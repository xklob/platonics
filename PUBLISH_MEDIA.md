# Completing the media upload

The Python renderers and metadata can be committed directly through the connected GitHub integration. The **binary images, videos, ZIPs and GIF previews** require a regular Git push from a machine with access to the original bytes.

The downloadable `platonics-complete-repository.zip` package contains all of them, plus their verified SHA-256 checksums. Extract that archive and run:

```bash
cd platonics-repository
bash tools/publish_to_github.sh
```

The script clones `xklob/platonics`, copies the complete archive contents, commits the additions, and pushes to `master` using your locally configured GitHub credentials. It does not change unrelated files in the target repository. You can pass a destination checkout path as the script's first argument.

GitHub warns about files above 50 MiB but accepts files up to 100 MiB in ordinary Git. The two square 4K videos (92.1 MB and 53.6 MB) are below that limit; Git LFS is optional if larger videos are added later.

Verify the package before pushing with `python3 tools/verify_media.py` (no dependencies required). All 86 recovered originals are included in the manifest: **67 PNG + 11 MP4 + 8 original source ZIP**.
