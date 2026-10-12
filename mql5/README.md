# mql5/ — MQL5 port (Phase 9+). Stubs only in Phase 0.

- `Include/BrooksLab/` — engine classes (`CBar`, `CSwingDetector`, …), ported
  exactly from `docs/PATTERN_SPEC.md` (Phase 6). Any deviation requires a spec
  update first.
- `Indicators/BrooksLab.mq5` — the live indicator.
- `Experts/BrooksLabEA.mq5` — the EA (Phase 10).
- `Scripts/ParityExport.mq5` — parity export (Phase 9).

Install (once real code lands): copy this folder's contents into the MT5
data-folder `MQL5/` tree and compile in MetaEditor.
