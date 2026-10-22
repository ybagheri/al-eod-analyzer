# data/ — user-provided chart images (NOT committed)

Put Brooks EOD review screenshots here (S&P 500 Emini, M5, one full day each).

- Expected filename pattern: `S&P500_Emini_M5_YYYY_MM_DD.jpg`
  (e.g. `S&P500_Emini_M5_2022_07_29.jpg`). Phase 1 parses the date from the
  filename and falls back to OCR of the axis when the pattern does not match.
- Images are third-party copyrighted material for **personal research use**.
  They are git-ignored (`data/*.jpg` etc.); only this README is tracked and
  committed (documentation only, enforced by `scripts/public_safety_scan.py`).
- The repo is public; image files and market data must never be committed
  (`AGENTS.md` rule 11, `docs/PUBLIC_SAFETY.md`).
- Derived labels (JSON in `artifacts/labels/`) may be committed.

Current pilot set: 5 images (2022-07-29 … 2022-08-09). The full collection is
expected to grow to ~100–200 images.
