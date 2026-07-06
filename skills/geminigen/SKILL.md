---
name: geminigen
description: >
  Generate images and videos using snapgen.ai API (nano-banana/Grok/Meta AI/Sora/Veo/Seedance/Kling models).
  Use when user asks to create image/video, generate picture/animation, or invokes /geminigen.
  Supports image generation (4 models), video generation (5 families: Veo, Sora, Grok, Seedance, Kling),
  extend operations (Veo/Grok/Seedance), and Grok storyboard (multi-scene chained videos).
argument-hint: "<media-type> <prompt> [--model MODEL] [--out path] [--ref image.png]"
allowed-tools: Bash
---

Generate images or videos using bundled CLI:

```bash
# Image generation (nano-banana-pro/nano-banana-2, grok-image, meta-ai-image, gpt-image-2)
python "$HOME/.claude/skills/geminigen/scripts/geminigen.py" image \
  --prompt "A beautiful sunset over mountains" \
  --model nano-banana-pro \
  --out "output.jpg"

# Video generation (veo/sora/grok/seedance/kling families)
python "$HOME/.claude/skills/geminigen/scripts/geminigen.py" video \
  --prompt "A serene lake at sunset" \
  --model veo-3.1 \
  --duration 8 \
  --out "video.mp4"

# Extend video (veo/grok/seedance)
python "$HOME/.claude/skills/geminigen/scripts/geminigen.py" extend \
  --prompt "Continue with sunrise" \
  --model veo \
  --ref-history <uuid> \
  --out "extended.mp4"

# Storyboard (Grok multi-scene)
python "$HOME/.claude/skills/geminigen/scripts/geminigen.py" storyboard \
  --scenes '[{"prompt":"Scene 1","duration":6},{"prompt":"Scene 2","duration":10}]' \
  --out "storyboard.mp4"
```

## Defaults

- Output path: `output/geminigen/<media-type>_output.<ext>` unless user specifies one.
- Backend: `https://api.snapgen.ai/uapi/v1/`
- Image model: `nano-banana-pro` (Gemini 3 Pro Image Preview)
- Video model: `veo-3.1` (latest Veo)
- Polling: checks history API every 10s, timeout 600s (10 min)

## Options

### Image Generation

- `--model`: `nano-banana-pro` (Gemini 3 Pro), `nano-banana-2` (Gemini 3 Flash), `grok-image`, `meta-ai-image`, `gpt-image-2` (Premium)
- `--aspect-ratio`: `1:1` (default), `16:9`, `9:16`, `4:3`, `3:4`
- `--resolution`: `1K` (default), `2K`, `4K` (nano-banana models only)
- `--style`: `Photorealistic`, `3D Render`, `Anime General`, `Creative`, `Fashion`, `Portrait`, etc. (nano-banana only)
- `--orientation`: `landscape`, `portrait`, `square` (grok/meta-ai only)
- `--num-result`: number of images (1-8 for grok, 1-4 for meta-ai, default 1)
- `--mode`: `SPEED` or `QUALITY` (grok only, default SPEED; QUALITY max 4 images)
- `--ref`: reference image (local path or URL, repeatable)
- `--ref-history`: UUID of previous geminigen image for style reference

### Video Generation

**Veo family** (`veo-3.1`, `veo-3.1-fast`, `veo-2`, `veo-3.1-lite`, `omni-flash`):
- `--resolution`: `720p`, `1080p` (veo-2 only 720p)
- `--duration`: 4, 6, 8 (veo-2/veo-3.x); 10 (omni-flash)
- `--aspect-ratio`: `16:9`, `9:16`
- `--mode-image`: `frame` (1-2 images), `ingredient` (1-3 images)
- `--ref`: reference image (local/URL, repeatable; max 2 for frame, 3 for ingredient)
- `--ref-video`: reference video (local/URL, omni-flash only)

**Sora family** (`sora-2`, `sora-2-pro`, `sora-2-pro-hd`):
- `--resolution`: `small` (720p) or `large` (1080p); sora-2/sora-2-pro only small, sora-2-pro-hd only large
- `--duration`: 10 or 15 (sora-2); 25 (sora-2-pro); 15 (sora-2-pro-hd)
- `--aspect-ratio`: `landscape` (16:9), `portrait` (9:16)
- `--ref`: single reference image (local/URL)
- `--ref-history`: UUID of previous image

**Grok** (`grok-3`):
- `--resolution`: `480p`, `720p`
- `--duration`: 6, 10
- `--aspect-ratio`: `landscape` (16:9), `portrait` (9:16), `square` (1:1), `vertical` (2:3), `horizontal` (3:2)
- `--mode`: `custom`, `normal`, `extremely-crazy`, `extremely-spicy-or-crazy`
- `--ref`: reference image (local/URL, repeatable; priority: files > file_urls > ref_images)

**Seedance** (`seedance-2`, `seedance-2-omni`):
- `--mode`: `fast`, `pro` (seedance-2); `fast`, `pro`, `fast-2`, `pro-2`, `fast-vip`, `pro-vip` (seedance-2-omni)
- `--duration`: 4-15 seconds
- `--aspect-ratio`: `16:9`, `9:16`, `1:1`, `3:4`, `4:3`, `21:9`
- `--ref`: reference image (local/URL, repeatable; seedance-2: first/last frame, max 1 per frame, 15MB; seedance-2-omni: ingredient, max 4, 15MB)
- `--ref-video`: reference video (seedance-2-omni only, mp4/webm, max 15s, 60MB)
- `--ref-audio`: reference audio (seedance-2-omni only, mp3/wav, max 15s)

**Kling** (13 models: `kling-video-3-0`, `kling-video-2-6`, `kling-video-o1`, `kling-video-2-5`, `kling-video-lipsync`, `kling-video-motion-3`, `kling-video-motion`, `kling-video-3-0-edit`, `kling-video-o1-edit`, legacy 2.1/1.6 variants):
- `--mode`: `standard` (720p), `professional` (1080p), `professional_audio` (kling-video-2-6 only), `relax` (kling-video-2-5 only, fastest/cheapest)
- `--duration`: 3-15 seconds (depends on model)
- `--aspect-ratio`: `16:9`, `9:16`, `1:1`
- `--ref`: reference image (local/URL, repeatable; max 4, 10MB each)
- `--ref-video`: reference video (local/URL, **required** for motion/edit models; mp4/mov/webm, max 100MB, 120s)
- **Note**: Motion models (`kling-video-motion-3`, `kling-video-motion`) and edit models (`kling-video-3-0-edit`, `kling-video-o1-edit`) **require** `--ref-video`. Duration auto-extracted from reference video, user-provided duration ignored.

### Extend Operations

**Veo extend**:
- `--ref-history`: UUID of veo video (required)
- Settings (model/aspect-ratio/resolution) auto-inherited from original video

**Grok extend**:
- `--ref-history`: UUID of grok video (required)

**Seedance extend**:
- `--ref-history`: UUID of seedance video (required)
- Settings (model/mode/duration/aspect-ratio) auto-inherited from original video

### Storyboard (Grok only)

- `--scenes`: JSON array of scene objects `[{"prompt":"...", "duration":6|10, "mode":"custom"}]`
  - Min 2 scenes, max 10 scenes
  - Total duration max 45 seconds
  - Each scene: duration 6 or 10 seconds
- `--aspect-ratio`: `landscape` (16:9, default), `portrait` (9:16), `square` (1:1)
- `--resolution`: `480p` (default), `720p` (1080p auto-downgraded to 720p)
- `--model`: `grok-video` or `grok-3` (alias)
- **Requires Premium plan** (free users blocked)

## API Key

Requires snapgen.ai API key. Script reads key from first available source:

1. `SNAPGEN_API_KEY`
2. `GEMINIGEN_API_KEY`
3. `/tmp/snapgen_api_key`
4. `/tmp/geminigen_api_key`

Never print keys.

## Workflow

1. Use user-provided prompt/arguments.
2. If no output path specified, save to `output/geminigen/<media-type>_output.<ext>` (`.jpg` for image, `.mp4` for video).
3. For reference images/videos, pass each with `--ref` / `--ref-video` (repeatable).
4. Run bundled script.
5. Script submits request, polls history API every 10s until `status: 2` (completed) or `status: 3` (failed), timeout 600s.
6. On completion, downloads result to specified path.
7. Report saved path(s), file size, and generation UUID.

Use `--force` to overwrite existing output.
Use `--poll-interval N` / `--poll-timeout N` to customize polling (default 10s / 600s).

## Common Errors

- `API_KEY_NOT_FOUND` / `API_KEY_REQUIRED`: Set API key via env or `/tmp/snapgen_api_key`
- `NOT_ENOUGH_CREDIT`: Insufficient credits, check balance via `GET /uapi/v1/account`
- `PREMIUM_PLAN_REQUIRED`: Upgrade plan (Kling models, grok-storyboard require Premium)
- `GEMINI_RATE_LIMIT`: nano-banana-pro rate limit (5 req/min, 100/hour, 1000/day for free; paid no limit)
- `INVALID_VIDEO_FILE` (Kling): Motion/edit models require `--ref-video`
- `FILE_TOO_LARGE`: Image >10MB or video >100MB (Kling); reduce file size
- `VIDEO_DURATION_TOO_LONG`: Reference video >120s (Kling); trim video
- `TOO_FEW_SCENES` / `TOO_MANY_SCENES`: Storyboard requires 2-10 scenes
- `TOTAL_DURATION_EXCEEDED`: Storyboard max 45s total

## Async Pattern

All endpoints return immediately with `status: 1` (processing). Script polls `GET /uapi/v1/history/{uuid}` until `status: 2` or `3`. Alternatively, configure webhooks at https://snapgen.ai/profile/integration/webhook (events: `IMAGE_GENERATION_COMPLETED`, `VIDEO_GENERATION_COMPLETED`, `*_FAILED`).

## Premium Features

- `gpt-image-2` (image model): Premium only
- Kling models (all 13): Premium only
- Grok storyboard: Premium only

Check current plan/credits: `GET https://api.snapgen.ai/uapi/v1/account`
