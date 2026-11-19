# Media collection: published

All assets have been uploaded to the `master` branch of [xklob/platonics](https://github.com/xklob/platonics).

- 67 original PNG stills under `renders/stills/{2d,3d,4d}/`
- 11 original MP4 renders under `renders/videos/{2d,3d,4d}/`
- 11 short GIF previews under `renders/gifs/{2d,3d,4d}/`
- 67 optimized WebP thumbnails under `renders/thumbnails/{2d,3d,4d}/`
- 8 original source ZIPs under `archives/original-generator-zips/`
- Extracted Python renderers and geometry specifications under `generators/`

## Verify a checkout

```bash
git clone https://github.com/xklob/platonics.git
cd platonics
python3 tools/verify_media.py
```

The 86 original PNG, MP4, and source-ZIP assets are tracked in `MANIFEST.csv` with SHA-256 checksums. A second `MEDIA_MANIFEST.csv` tracks 97 original and derived media assets, including GIFs. The uploaded media was checked against that 97-item manifest before commit.

## Future additions

Add new renders under the appropriate `renders/` subdirectory, update manifests, then commit and push. The two square 4K videos are about 92 MB and 54 MB, so GitHub may warn about their size. Files exceeding GitHub's 100 MiB regular-Git limit should use Git LFS or release assets.
