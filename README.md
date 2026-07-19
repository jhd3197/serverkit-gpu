# serverkit-gpu

Live NVIDIA GPU metrics for [ServerKit](https://github.com/jhd3197/ServerKit) —
utilization, VRAM, temperature, power draw, fan speed, driver version, and the
running GPU compute processes (with best-effort container resolution). Adds a
**GPU Monitor** page (`/gpu`) to the panel; the sidebar entry only appears on
hosts where `nvidia-smi` is available.

Installs from the ServerKit Marketplace (registry:
[serverkit-extensions](https://github.com/jhd3197/serverkit-extensions)).

## Repository layout

```
plugin.json               # extension manifest (routes, nav, SDK + panel gates)
backend/                  # Flask blueprint + nvidia-smi parsing service
frontend/                 # runtime-ESM bundle source (vite lib build)
  runtime-entry.jsx       #   entry: injects inline CSS, exports GpuMonitorPage
  components/             #   GpuMonitor page + local EmptyState/Button stand-ins
  styles/gpu.css          #   page styles (host CSS custom properties)
scripts/build-zip.*       # release packaging (dist/serverkit-gpu-<version>.zip)
tests/                    # backend tests (run from a panel checkout — see tests/README.md)
```

## Development

The frontend is a **runtime-ESM extension**: it builds to a single
`frontend/dist/index.mjs` that the panel blob-imports at runtime — no panel
rebuild needed. React, react-router and `serverkit-sdk` are externalized and
resolved to the panel's own singletons via its import map; everything else
(lucide-react icons) is bundled.

```bash
cd frontend
npm install
npm run build        # writes frontend/dist/index.mjs
```

Load it into a dev panel with **Marketplace → Plugins → Upload Zip**, or:

```bash
./scripts/build-zip.sh    # or scripts/build-zip.ps1 on Windows
# → dist/serverkit-gpu-<version>.zip
```

For API details and the contribution model see
[docs/EXTENSIONS.md](https://github.com/jhd3197/ServerKit/blob/main/docs/EXTENSIONS.md)
in the main repo.

## Release

1. Bump `version` in `plugin.json` (and `frontend/package.json` to match).
2. `cd frontend && npm run build`
3. `./scripts/build-zip.sh`
4. Attach the zip to a GitHub release, then update `index.json` in
   [serverkit-extensions](https://github.com/jhd3197/serverkit-extensions)
   with the new version, download URL and sha256.

## License

MIT — see [LICENSE](LICENSE).
