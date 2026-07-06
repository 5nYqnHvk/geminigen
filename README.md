# geminigen

Claude Code skill for generating images and videos via the [snapgen.ai](https://snapgen.ai) API.

Supports **Gemini, Grok, Meta AI, GPT Image, Veo, Sora, Seedance, Kling** — all from a single `/geminigen` command.

## Installation

**Step 1** — Add this repo as a marketplace source:

```bash
claude plugin marketplace add https://github.com/5nYqnHvk/geminigen
```

**Step 2** — Install the plugin inside Claude Code:

```
/plugin install geminigen
```

Then set your API key (get one at [snapgen.ai](https://snapgen.ai)):

```bash
export SNAPGEN_API_KEY=your_key_here
```

Or write it to a temp file (persists across shell sessions without modifying your profile):

```bash
echo "your_key_here" > /tmp/snapgen_api_key
```

## Usage

Once installed, use the `/geminigen` command in Claude Code:

```
/geminigen image a golden retriever surfing at sunset
/geminigen video a timelapse of cherry blossoms falling --model veo-3.1
/geminigen image portrait of a samurai --model grok-image --orientation portrait
```

Output is saved to `output/geminigen/` by default, or specify `--out path/to/file`.

## Supported Models

### Image

| Model | ID | Notes |
|---|---|---|
| Gemini 3 Pro Image | `nano-banana-pro` | Default. Supports aspect ratio, resolution, style |
| Gemini 3 Flash Image | `nano-banana-2` | Faster, lighter |
| Grok Image | `grok-image` | Supports multi-image output (up to 8) |
| Meta AI Image | `meta-ai-image` | |
| GPT Image 2 | `gpt-image-2` | Premium plan required |

### Video

| Family | Models | Max Duration |
|---|---|---|
| Veo | `veo-3.1`, `veo-3.1-fast`, `veo-3.1-lite`, `veo-2`, `omni-flash` | 10s |
| Sora | `sora-2`, `sora-2-pro`, `sora-2-pro-hd` | 25s |
| Grok | `grok-3` | 10s |
| Seedance | `seedance-2`, `seedance-2-omni` | 15s |
| Kling | `kling-video-3-0`, `kling-video-2-6`, `kling-video-o1`, + 10 more | 15s |

## Examples

### Image generation

```
# Default model (nano-banana-pro)
/geminigen image a futuristic city at night in cyberpunk style

# 4K landscape with specific style
/geminigen image aerial view of the Amazon rainforest --model nano-banana-pro --aspect-ratio 16:9 --resolution 4K --style Photorealistic

# Multiple images with Grok
/geminigen image a cat wearing a wizard hat --model grok-image --num-result 4

# Image with reference photo
/geminigen image the same person but smiling --ref photo.jpg --model grok-image
```

### Video generation

```
# Veo 3.1 (default)
/geminigen video a whale breaching at sunrise --model veo-3.1 --duration 8

# Sora cinematic
/geminigen video slow motion rain on a window --model sora-2-pro --duration 25 --aspect-ratio landscape

# Image-to-video with Veo
/geminigen video the dog runs across the field --model veo-3.1 --ref dog.jpg --mode-image frame

# Kling with reference video
/geminigen video --model kling-video-motion-3 --ref-video original.mp4 --prompt add snow falling
```

### Extend a video

```
/geminigen extend --model veo --ref-history <uuid> --prompt continue with the camera pulling back
```

### Grok storyboard (multi-scene)

```
/geminigen storyboard --scenes '[{"prompt":"A lone astronaut on Mars","duration":6},{"prompt":"She removes her helmet, breathes fresh air","duration":10}]'
```

## Options Reference

### Common
- `--out` — output file path
- `--force` — overwrite existing file
- `--poll-interval N` — polling interval in seconds (default 10)
- `--poll-timeout N` — max wait time in seconds (default 600)

### Image
- `--aspect-ratio` — `1:1`, `16:9`, `9:16`, `4:3`, `3:4`
- `--resolution` — `1K`, `2K`, `4K` (nano-banana only)
- `--style` — `Photorealistic`, `3D Render`, `Anime General`, `Creative`, `Fashion`, `Portrait`, ...
- `--num-result` — number of images (grok: 1–8, meta-ai: 1–4)
- `--ref` — reference image, local path or URL (repeatable)

### Video
- `--duration` — seconds (model-dependent)
- `--aspect-ratio` — `16:9`, `9:16`, `1:1`, etc.
- `--resolution` — `720p`, `1080p`, `small`, `large`, `480p`
- `--mode` — model-specific quality/speed mode
- `--ref` — reference image for image-to-video
- `--ref-video` — reference video (required for motion/edit models)
- `--ref-audio` — reference audio (seedance-2-omni only)

## API Key Priority

The script reads your key from the first available source:

1. `SNAPGEN_API_KEY` env var
2. `GEMINIGEN_API_KEY` env var
3. `/tmp/snapgen_api_key` file
4. `/tmp/geminigen_api_key` file

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `API_KEY_NOT_FOUND` | Key not set | Set `SNAPGEN_API_KEY` or write to `/tmp/snapgen_api_key` |
| `NOT_ENOUGH_CREDIT` | Out of credits | Top up at snapgen.ai |
| `PREMIUM_PLAN_REQUIRED` | Kling / storyboard / gpt-image-2 | Upgrade plan |
| `GEMINI_RATE_LIMIT` | Free tier: 5 req/min, 100/hr | Wait or upgrade |
| `INVALID_VIDEO_FILE` | Motion/edit model without `--ref-video` | Add `--ref-video` |

## Requirements

- Python 3.8+
- `pip install requests`
- [snapgen.ai](https://snapgen.ai) account and API key
