# Public-Safety Scan — policy and procedure (S0)

The repo is **public** by the user's decision (`AGENTS.md` rule 11). This
document defines what "safe to be public" means for this repository and how
`scripts/public_safety_scan.py` enforces it.

## What must never be committed

- Chart images or any video (jpg, png, gif, mp4, ...) and archives
  (zip, 7z, ...) — third-party copyrighted material, personal research use only.
- Anything under `data/` (images or market data).
- Market data: `*.csv` larger than 200 KB; MT5 history files (`.hcc`, `.dat`, ...).
- `config/local.yaml`, `.env`, local machine paths (terminal path, MT5 data
  folder id, home-directory paths such as `C:\Users\<name>\` or `/home/<name>/`).
- Secrets: API keys, tokens, passwords, private-key blocks (`-----BEGIN ...`).
- Any blob larger than 1 MB; any single JSON string value (or text line)
  longer than 2000 chars that is a verbatim transcription of on-chart text.

Queue `*.request.json` files must never embed image bytes (base64).

## Allowed, documented exceptions (content inspected by hand)

| Path | Reason |
| --- | --- |
| `artifacts/manifest_batch1.json` | Metadata-only manifest (sha256/phash, dimensions, filenames per ingested image). No images, no market data. Slightly over the 1 MB blob limit (~1.05 MB) solely due to hash arrays. |
| `data/README.md` | Documentation only; the only tracked file under `data/` (images themselves are git-ignored). |

The `"prompt"` field inside `artifacts/extraction_queue/*.request.json` is the
committed extraction-prompt template (our own text); the long-string rule
exempts it.

## How to run

```powershell
python scripts/public_safety_scan.py            # tracked working tree
python scripts/public_safety_scan.py --json     # machine-readable
python scripts/public_safety_scan.py --history  # entire git history (all refs)
```

Exit code 0 = clean, 1 = violations. `--history` must be run before each
`S<k>-done` tag and its result recorded in `docs/evidence/<step>.md`.
The gate (`python -m tasks check`) runs the working-tree scan; CI runs both.

## Scan status (2026-10-19)

- Working tree: **clean**.
- Full history: **1 finding** — an old version of `docs/MASTER_PROMPT.md`
  (blob `07f0f9c4…`) contains two absolute local MT5 paths (terminal path and
  MT5 data-folder id). The current version is redacted.
- **User decision (2026-10-19, Persian): ACCEPTED.** The user reviewed the
  finding (username + terminal-folder id, no key/secret) and chose to accept
  the historical exposure instead of rewriting history. No filter-repo /
  force-push. This decision is final for S0 and recorded in `docs/evidence/S0.md`.
