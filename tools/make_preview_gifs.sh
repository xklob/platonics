#!/usr/bin/env bash
# Regenerate short GitHub-friendly GIF previews from original MP4s.
set -euo pipefail
cd "$(dirname "$0")/.."
for video in renders/videos/*/*.mp4; do
  group="$(basename "$(dirname "$video")")"
  name="$(basename "${video%.mp4}")"
  mkdir -p "renders/gifs/$group"
  ffmpeg -hide_banner -loglevel error -y -i "$video" -t 2.25 \
    -filter_complex '[0:v]fps=12,scale=320:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3' \
    "renders/gifs/$group/$name.gif"
done
