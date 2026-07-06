#!/usr/bin/env python3
"""
geminigen - snapgen.ai image/video generation CLI
Supports: image (nano-banana/grok/meta-ai/gpt-image-2), video (veo/sora/grok/seedance/kling),
extend (veo/grok/seedance), storyboard (grok multi-scene)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)

# Base URLs
BASE_URL = "https://api.snapgen.ai/uapi/v1"
HISTORY_URL_TEMPLATE = f"{BASE_URL}/history/{{uuid}}"

# Defaults
DEFAULT_IMAGE_MODEL = "nano-banana-pro"
DEFAULT_VIDEO_MODEL = "veo-3.1"
DEFAULT_OUT_DIR = "output/geminigen"
DEFAULT_POLL_INTERVAL = 10  # seconds
DEFAULT_POLL_TIMEOUT = 600  # 10 minutes

# Status codes
STATUS_PROCESSING = 1
STATUS_COMPLETED = 2
STATUS_FAILED = 3


def die(message: str) -> None:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_api_key() -> Optional[str]:
    """Read API key from env vars or file in priority order."""
    for name in ("SNAPGEN_API_KEY", "GEMINIGEN_API_KEY"):
        value = os.getenv(name)
        if value:
            return value.strip()
    for raw in ("/tmp/snapgen_api_key", "/tmp/geminigen_api_key"):
        path = Path(raw)
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return None


def build_headers() -> Dict[str, str]:
    """Build request headers with API key."""
    key = read_api_key()
    if not key:
        die(
            "API key missing. Set SNAPGEN_API_KEY/GEMINIGEN_API_KEY or write /tmp/snapgen_api_key."
        )
    return {"x-api-key": key}


def submit_request(
    endpoint: str, data: Dict[str, Any], files: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Submit generation request and return initial response."""
    url = f"{BASE_URL}/{endpoint}"
    headers = build_headers()

    try:
        response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        try:
            body = exc.response.json()
            if "detail" in body:
                detail = body["detail"]
                if isinstance(detail, dict):
                    error_code = detail.get("error_code", "UNKNOWN")
                    error_message = detail.get("error_message", str(exc))
                    die(f"HTTP {exc.response.status_code}: {error_code} - {error_message}")
            die(f"HTTP {exc.response.status_code}: {exc.response.text[:500]}")
        except Exception:
            die(f"HTTP {exc.response.status_code}: {exc}")
    except requests.exceptions.RequestException as exc:
        die(f"Request failed: {exc}")


def poll_until_complete(
    uuid: str, poll_interval: int, poll_timeout: int
) -> Dict[str, Any]:
    """Poll history API until generation completes or fails."""
    url = HISTORY_URL_TEMPLATE.format(uuid=uuid)
    headers = build_headers()
    start_time = time.time()

    print(f"Polling {url} (interval={poll_interval}s, timeout={poll_timeout}s)...", file=sys.stderr)

    while True:
        elapsed = time.time() - start_time
        if elapsed > poll_timeout:
            die(f"Timeout after {elapsed:.1f}s. UUID: {uuid}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            print(f"Poll error: {exc}. Retrying...", file=sys.stderr)
            time.sleep(poll_interval)
            continue

        status = data.get("status")
        status_desc = data.get("status_desc", "")
        status_percentage = data.get("status_percentage", 0)

        if status == STATUS_COMPLETED:
            print(f"✓ Completed in {elapsed:.1f}s.", file=sys.stderr)
            return data
        elif status == STATUS_FAILED:
            error_code = data.get("error_code", "")
            error_message = data.get("error_message", "Unknown error")
            die(f"Generation failed: {error_code} - {error_message}")
        elif status == STATUS_PROCESSING:
            print(f"  [{status_percentage}%] {status_desc}", file=sys.stderr)
        else:
            print(f"  Status {status}: {status_desc}", file=sys.stderr)

        time.sleep(poll_interval)


def download_media(url: str, output_path: Path, force: bool) -> None:
    """Download media from URL to local path."""
    if output_path.exists() and not force:
        die(f"Output exists: {output_path} (use --force to overwrite)")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(url, timeout=300, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size = output_path.stat().st_size
        print(f"Downloaded {output_path} ({size:,} bytes)")
    except requests.exceptions.RequestException as exc:
        die(f"Download failed: {exc}")


def extract_result_url(data: Dict[str, Any], media_type: str) -> str:
    """Extract result URL from completed history data."""
    # Try generate_result first (common field)
    if data.get("generate_result"):
        return data["generate_result"]

    # Try nested generated_video/generated_image arrays
    if media_type == "video":
        videos = data.get("generated_video", [])
        if videos and isinstance(videos, list) and len(videos) > 0:
            video_url = videos[0].get("video_url")
            if video_url:
                return video_url
    elif media_type == "image":
        images = data.get("generated_image", [])
        if images and isinstance(images, list) and len(images) > 0:
            image_url = images[0].get("image_url") or images[0].get("image_uri")
            if image_url:
                return image_url

    # Fallback: check media_files array (Kling)
    media_files = data.get("media_files", [])
    if media_files and isinstance(media_files, list) and len(media_files) > 0:
        file_url = media_files[0].get("url") or media_files[0].get("video_url")
        if file_url:
            return file_url

    die(f"No result URL found in response. Keys: {list(data.keys())}")


def prepare_files_for_upload(
    ref_paths: List[str], ref_videos: List[str], ref_audios: List[str]
) -> Dict[str, Any]:
    """Prepare multipart files dict for requests."""
    files = {}

    # Reference images
    for idx, ref_path in enumerate(ref_paths):
        path = Path(ref_path)
        if not path.exists():
            die(f"Reference image not found: {path}")
        files[f"ref_images_{idx}"] = (path.name, open(path, "rb"), guess_mime_type(path))

    # Reference videos
    for idx, video_path in enumerate(ref_videos):
        path = Path(video_path)
        if not path.exists():
            die(f"Reference video not found: {path}")
        files[f"ref_videos_{idx}"] = (path.name, open(path, "rb"), guess_mime_type(path))

    # Reference audios
    for idx, audio_path in enumerate(ref_audios):
        path = Path(audio_path)
        if not path.exists():
            die(f"Reference audio not found: {path}")
        files[f"ref_audios_{idx}"] = (path.name, open(path, "rb"), guess_mime_type(path))

    return files


def guess_mime_type(path: Path) -> str:
    """Guess MIME type from file extension."""
    ext = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
    }
    return mime_map.get(ext, "application/octet-stream")


def close_files(files: Dict[str, Any]) -> None:
    """Close all open file handles in multipart files dict."""
    for key, value in files.items():
        if isinstance(value, tuple) and len(value) >= 2:
            file_obj = value[1]
            if hasattr(file_obj, "close"):
                file_obj.close()


# ============================================================================
# Command: image
# ============================================================================

def cmd_image(args: argparse.Namespace) -> int:
    """Generate image using nano-banana/grok/meta-ai/gpt-image-2."""
    model = args.model or DEFAULT_IMAGE_MODEL

    # Map model to endpoint
    if model.startswith("nano-banana"):
        endpoint = "generate_image"
    elif model == "grok-image":
        endpoint = "imagen/grok"
    elif model == "meta-ai-image":
        endpoint = "meta_ai/generate"
    elif model == "gpt-image-2":
        endpoint = "gpt_image/generate"
    else:
        die(f"Unknown image model: {model}")

    # Build request data
    data = {"prompt": args.prompt, "model": model}

    # Model-specific parameters
    if model.startswith("nano-banana"):
        if args.aspect_ratio:
            data["aspect_ratio"] = args.aspect_ratio
        if args.resolution:
            data["resolution"] = args.resolution
        if args.style:
            data["style"] = args.style
        if args.ref_history:
            data["ref_history"] = args.ref_history
    elif model in ("grok-image", "meta-ai-image"):
        if args.orientation:
            data["orientation"] = args.orientation
        if args.num_result:
            data["num_result"] = args.num_result
        if model == "grok-image" and args.mode:
            data["mode"] = args.mode
        if args.ref_history:
            data["ref_history"] = args.ref_history

    # Handle reference images
    files = {}
    if args.ref:
        for ref in args.ref:
            if ref.startswith("http://") or ref.startswith("https://"):
                # URL reference
                if "file_urls" not in data:
                    data["file_urls"] = []
                data["file_urls"].append(ref)
            else:
                # Local file
                path = Path(ref)
                if not path.exists():
                    die(f"Reference image not found: {path}")
                # For requests multipart, append to files list with same key
                if "files" not in files:
                    files["files"] = []
                files["files"].append((path.name, open(path, "rb"), guess_mime_type(path)))

    # Convert file list to proper format for requests
    files_for_request = None
    if files:
        files_for_request = []
        for name, fp, mime in files["files"]:
            files_for_request.append(("files", (name, fp, mime)))

    try:
        # Submit
        response = submit_request(endpoint, data, files_for_request)
        uuid = response.get("uuid")
        if not uuid:
            die(f"No UUID in response. Keys: {list(response.keys())}")

        print(f"Submitted. UUID: {uuid}", file=sys.stderr)

        # Poll
        result = poll_until_complete(uuid, args.poll_interval, args.poll_timeout)

        # Extract URL
        result_url = extract_result_url(result, "image")

        # Download
        output_path = Path(args.out) if args.out else Path(DEFAULT_OUT_DIR) / "image_output.jpg"
        download_media(result_url, output_path, args.force)

        print(f"UUID: {uuid}")
        return 0
    finally:
        # Close file handles
        if files_for_request:
            for _, (name, fp, mime) in files_for_request:
                if hasattr(fp, "close"):
                    fp.close()


# ============================================================================
# Command: video
# ============================================================================

def cmd_video(args: argparse.Namespace) -> int:
    """Generate video using veo/sora/grok/seedance/kling."""
    model = args.model or DEFAULT_VIDEO_MODEL

    # Map model to endpoint
    if model.startswith("veo"):
        endpoint = "video-gen/veo"
    elif model.startswith("sora"):
        endpoint = "video-gen/sora"
    elif model.startswith("grok"):
        endpoint = "video-gen/grok"
    elif model.startswith("seedance"):
        endpoint = "video-gen/seedance"
    elif model.startswith("kling"):
        endpoint = "video-gen/kling"
    else:
        die(f"Unknown video model: {model}")

    # Build request data
    data = {"prompt": args.prompt, "model": model}

    # Common parameters
    if args.duration:
        data["duration"] = args.duration
    if args.aspect_ratio:
        data["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        data["resolution"] = args.resolution
    if args.mode:
        data["mode"] = args.mode

    # Model-specific parameters
    if model.startswith("veo"):
        if args.mode_image:
            data["mode_image"] = args.mode_image
    elif model.startswith("seedance"):
        pass  # mode already set above

    # Handle reference files
    files_list = []

    # Reference images
    if args.ref:
        for ref in args.ref:
            if ref.startswith("http://") or ref.startswith("https://"):
                # URL reference
                if "file_urls" not in data:
                    data["file_urls"] = []
                data["file_urls"].append(ref)
            else:
                # Local file
                path = Path(ref)
                if not path.exists():
                    die(f"Reference image not found: {path}")
                files_list.append(("ref_images", (path.name, open(path, "rb"), guess_mime_type(path))))

    # Reference videos
    if args.ref_video:
        for ref in args.ref_video:
            if ref.startswith("http://") or ref.startswith("https://"):
                if "ref_video_urls" not in data:
                    data["ref_video_urls"] = []
                data["ref_video_urls"].append(ref)
            else:
                path = Path(ref)
                if not path.exists():
                    die(f"Reference video not found: {path}")
                files_list.append(("ref_videos", (path.name, open(path, "rb"), guess_mime_type(path))))

    # Reference audios (seedance-2-omni)
    if args.ref_audio:
        for ref in args.ref_audio:
            path = Path(ref)
            if not path.exists():
                die(f"Reference audio not found: {path}")
            files_list.append(("ref_audios", (path.name, open(path, "rb"), guess_mime_type(path))))

    # Reference history
    if args.ref_history:
        data["ref_history"] = args.ref_history

    try:
        # Submit
        response = submit_request(endpoint, data, files_list if files_list else None)
        uuid = response.get("uuid")
        if not uuid:
            die(f"No UUID in response. Keys: {list(response.keys())}")

        print(f"Submitted. UUID: {uuid}", file=sys.stderr)

        # Poll
        result = poll_until_complete(uuid, args.poll_interval, args.poll_timeout)

        # Extract URL
        result_url = extract_result_url(result, "video")

        # Download
        output_path = Path(args.out) if args.out else Path(DEFAULT_OUT_DIR) / "video_output.mp4"
        download_media(result_url, output_path, args.force)

        print(f"UUID: {uuid}")
        return 0
    finally:
        # Close file handles
        for key, (name, fp, mime) in files_list:
            if hasattr(fp, "close"):
                fp.close()


# ============================================================================
# Command: extend
# ============================================================================

def cmd_extend(args: argparse.Namespace) -> int:
    """Extend video using veo/grok/seedance."""
    if not args.model:
        die("--model required for extend (veo/grok/seedance)")
    if not args.ref_history:
        die("--ref-history required for extend")

    model_family = args.model.lower()

    # Map to endpoint
    if model_family == "veo":
        endpoint = "video-extend/veo"
    elif model_family == "grok":
        endpoint = "video-extend/grok"
    elif model_family == "seedance":
        endpoint = "video-extend/seedance"
    else:
        die(f"Unknown extend model: {model_family}")

    # Build request
    data = {
        "prompt": args.prompt,
        "ref_history": args.ref_history,
    }

    # Submit
    response = submit_request(endpoint, data)
    uuid = response.get("uuid")
    if not uuid:
        die(f"No UUID in response. Keys: {list(response.keys())}")

    print(f"Submitted extend. UUID: {uuid}", file=sys.stderr)

    # Poll
    result = poll_until_complete(uuid, args.poll_interval, args.poll_timeout)

    # Extract URL
    result_url = extract_result_url(result, "video")

    # Download
    output_path = Path(args.out) if args.out else Path(DEFAULT_OUT_DIR) / "extend_output.mp4"
    download_media(result_url, output_path, args.force)

    print(f"UUID: {uuid}")
    return 0


# ============================================================================
# Command: storyboard
# ============================================================================

def cmd_storyboard(args: argparse.Namespace) -> int:
    """Generate multi-scene video using Grok storyboard."""
    if not args.scenes:
        die("--scenes required (JSON array of scene objects)")

    # Parse scenes JSON
    try:
        scenes = json.loads(args.scenes)
    except json.JSONDecodeError as exc:
        die(f"Invalid JSON in --scenes: {exc}")

    if not isinstance(scenes, list):
        die("--scenes must be a JSON array")

    # Build request
    data = {
        "scenes": json.dumps(scenes),  # API expects JSON string
        "aspect_ratio": args.aspect_ratio or "landscape",
        "resolution": args.resolution or "720p",
        "model": args.model or "grok-video",
    }

    # Submit
    endpoint = "video-storyboard/grok"
    response = submit_request(endpoint, data)
    uuid = response.get("uuid")
    if not uuid:
        die(f"No UUID in response. Keys: {list(response.keys())}")

    print(f"Submitted storyboard ({len(scenes)} scenes). UUID: {uuid}", file=sys.stderr)

    # Poll
    result = poll_until_complete(uuid, args.poll_interval, args.poll_timeout)

    # Extract URL
    result_url = extract_result_url(result, "video")

    # Download
    output_path = Path(args.out) if args.out else Path(DEFAULT_OUT_DIR) / "storyboard_output.mp4"
    download_media(result_url, output_path, args.force)

    print(f"UUID: {uuid}")
    return 0


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="geminigen - snapgen.ai image/video generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # ---- image ----
    image_parser = subparsers.add_parser("image", help="Generate image")
    image_parser.add_argument("--prompt", required=True, help="Text prompt")
    image_parser.add_argument("--model", help=f"Model (default: {DEFAULT_IMAGE_MODEL})")
    image_parser.add_argument("--out", help="Output path")
    image_parser.add_argument("--aspect-ratio", help="Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)")
    image_parser.add_argument("--resolution", help="Resolution (1K, 2K, 4K)")
    image_parser.add_argument("--style", help="Style (Photorealistic, 3D Render, etc.)")
    image_parser.add_argument("--orientation", help="Orientation (landscape, portrait, square)")
    image_parser.add_argument("--num-result", type=int, help="Number of images (1-8)")
    image_parser.add_argument("--mode", help="Mode (SPEED, QUALITY)")
    image_parser.add_argument("--ref", action="append", default=[], help="Reference image (repeatable)")
    image_parser.add_argument("--ref-history", help="Reference history UUID")
    image_parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    image_parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="Poll interval (seconds)")
    image_parser.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT, help="Poll timeout (seconds)")

    # ---- video ----
    video_parser = subparsers.add_parser("video", help="Generate video")
    video_parser.add_argument("--prompt", required=True, help="Text prompt")
    video_parser.add_argument("--model", help=f"Model (default: {DEFAULT_VIDEO_MODEL})")
    video_parser.add_argument("--out", help="Output path")
    video_parser.add_argument("--duration", type=int, help="Duration (seconds)")
    video_parser.add_argument("--aspect-ratio", help="Aspect ratio (16:9, 9:16, 1:1, etc.)")
    video_parser.add_argument("--resolution", help="Resolution (720p, 1080p, small, large, 480p)")
    video_parser.add_argument("--mode", help="Mode (standard, professional, fast, pro, etc.)")
    video_parser.add_argument("--mode-image", help="Mode image (frame, ingredient)")
    video_parser.add_argument("--ref", action="append", default=[], help="Reference image (repeatable)")
    video_parser.add_argument("--ref-video", action="append", default=[], help="Reference video (repeatable)")
    video_parser.add_argument("--ref-audio", action="append", default=[], help="Reference audio (repeatable)")
    video_parser.add_argument("--ref-history", help="Reference history UUID")
    video_parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    video_parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="Poll interval (seconds)")
    video_parser.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT, help="Poll timeout (seconds)")

    # ---- extend ----
    extend_parser = subparsers.add_parser("extend", help="Extend video")
    extend_parser.add_argument("--prompt", required=True, help="Text prompt")
    extend_parser.add_argument("--model", required=True, help="Model family (veo, grok, seedance)")
    extend_parser.add_argument("--ref-history", required=True, help="Original video UUID")
    extend_parser.add_argument("--out", help="Output path")
    extend_parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    extend_parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="Poll interval (seconds)")
    extend_parser.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT, help="Poll timeout (seconds)")

    # ---- storyboard ----
    storyboard_parser = subparsers.add_parser("storyboard", help="Generate Grok storyboard (multi-scene)")
    storyboard_parser.add_argument("--scenes", required=True, help='JSON array: [{"prompt":"...","duration":6}]')
    storyboard_parser.add_argument("--out", help="Output path")
    storyboard_parser.add_argument("--aspect-ratio", help="Aspect ratio (landscape, portrait, square)")
    storyboard_parser.add_argument("--resolution", help="Resolution (480p, 720p)")
    storyboard_parser.add_argument("--model", help="Model (grok-video, grok-3)")
    storyboard_parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    storyboard_parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="Poll interval (seconds)")
    storyboard_parser.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT, help="Poll timeout (seconds)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "image":
        return cmd_image(args)
    elif args.command == "video":
        return cmd_video(args)
    elif args.command == "extend":
        return cmd_extend(args)
    elif args.command == "storyboard":
        return cmd_storyboard(args)
    else:
        die(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
