# MT5 Market-Data Export (S3, Phase 5b)

Purpose: export read-only M5 history from the Alpari MT5 terminal into
`data/market/raw/` so the S3 experiments (broker-time alignment, coverage
probe, similarity gate) can run. Nothing in this workflow trades, changes
terminal settings, or writes anything except two scripts' output files in
`MQL5\Files`.

**Source of truth:** `docs/PLAN_V2.md` §S3. Raw CSVs are git-ignored and must
never be committed (public repo). Only `artifacts/market_manifest.json` (the
validation report) is committed.

## Files delivered

| File | Runs in | Output (in `MQL5\Files`) |
|---|---|---|
| `mql5/Scripts/ExportSymbols.mq5` | MT5 terminal | `symbols_sp500.csv` — all symbols matching `SP500`, `US500`, `SPX`, `ES`, `S&P` (case-insensitive) with description, path, expiration, first M5 bar date, digits, point |
| `mql5/Scripts/ExportRatesM5.mq5` | MT5 terminal | `rates_<SYMBOL>_M5.csv` + `<SYMBOL>_export_info.txt` for one symbol (inputs: `InpSymbol`, `InpFrom`, `InpTo`) |
| `scripts/market_validate.py` | Python venv | `artifacts/market_manifest.json` — hashes, row counts, errors, anomalies, missing weekdays, gaps |

## CSV contract

```
time_server,open,high,low,close,tick_volume,real_volume,spread
```

- `time_server`: broker **server time**, ISO `YYYY-MM-DD HH:MM:SS` (TZ rule is
  derived empirically later; documentation alone is not trusted).
- `.` decimals; one M5 bar per row; monotonic time.
- `<SYMBOL>_export_info.txt`: `key: value` lines including `bar_count`,
  `first_bar`, `last_bar`, digits, point, tick value/size, contract size,
  expiration — used to cross-check the CSV.

## Terminal procedure (one symbol at a time)

1. Docker-copied or manually copied scripts go to
   `<MT5 data folder>\MQL5\Scripts\` (see data-folder path in
   `config/local.yaml`; open it via *File → Open Data Folder*).
2. In MT5: *View → Navigator → Scripts* (right-click → **Refresh** if the
   scripts are not visible).
3. *Tools → Options → Charts → Max bars in chart*: set to the largest value.
4. Open an M5 chart of the symbol and scroll back to the earliest bars (or
   press `F2` for the History Center and load the symbol's history) so the
   terminal actually has all stored bars on disk.
5. Drag `ExportSymbols.mq5` onto any chart once — this writes
   `symbols_sp500.csv` (needs to be run once, before step 6).
6. Drag `ExportRatesM5.mq5` onto a chart of the target symbol; in the Inputs
   dialog set `InpSymbol`, `InpFrom`, `InpTo` (dates in server time!). Run it
   for **`US500`, `SP500Z6` and every sibling contract found by
   `ExportSymbols`**. `SP500Z6` expires around December 2026 — export it
   **now** and archive the raw CSV.
7. Copy the output files into `data/market/raw/` in the repo:
   ```
   data/market/raw/rates_US500_M5.csv
   data/market/raw/US500_export_info.txt
   data/market/raw/rates_SP500Z6_M5.csv
   data/market/raw/SP500Z6_export_info.txt
   data/market/raw/symbols_sp500.csv
   ```

## Validation (agent side, no MT5 needed)

```powershell
$env:PATH = ".\.venv\Scripts;$env:PATH"
python scripts\market_validate.py
```

Exit code 0 = all files conform; 2 = anomalies (reported in
`artifacts/market_manifest.json`). The manifest records for each file:
SHA-256, row count, first/last bar, header/parse errors, OHLC anomalies,
duplicates, non-monotonic timestamps, suspicious ranges, missing weekdays,
gaps over 3 calendar days, and whether `bar_count` matches the declared
`export_info` value.

## Safety rules

- MT5 stays **read-only**: no trading, no terminal settings changed, only the
  two output files in `MQL5\Files` are written.
- Raw market CSVs never enter git (`data/market/` is git-ignored);
  `scripts/public_safety_scan.py` must stay clean.
- Broker-server time rules are **not** assumed; they are derived empirically
  in the later S3 steps and recorded in `config/broker_time.yaml` with tests.

---

## خلاصه فارسی برای کاربر (CHECKPOINT B)

1. دو اسکریپت زیر را در فولدر دیتای متاتریدر (از داخل ترمینال، *File → Open Data Folder*) زیر `MQL5\Scripts` کپی کن:
   - `mql5/Scripts/ExportSymbols.mq5`
   - `mql5/Scripts/ExportRatesM5.mq5`
2. در متاتریدر: `View → Navigator → Scripts` را باز کن (اگر نبود، راست‌کلیک → Refresh). سپس در `Tools → Options → Charts → Max bars in chart` بزرگ‌ترین مقدار را بگذار.
3. یک بار `ExportSymbols` را روی هر چارتی بینداز تا فایل `symbols_sp500.csv` ساخته شود؛ این لیست همه‌ی سمبل‌های مرتبط با S&P 500 را با تاریخِ اولین کندل M5 می‌دهد.
4. برای هر سمبل (حتماً **US500** و **SP500Z6** — زد6 حدود دسامبر منقضی می‌شود، همین حالا اکسپورت و آرشیو کن) و هر قرارداد دیگری که در لیست ظاهر شد:
   - یک چارت M5 از آن سمبل باز کن و به عقب اسکرول کن تا ترمینال کل تاریخچه را بارگذاری کند (یا `F2` → History Center).
   - `ExportRatesM5` را روی چارت بینداز؛ در پنجره Inputs مقدارهای `InpSymbol`، `InpFrom`، `InpTo` را (به **سِروِر تایم** ترمینال، نه GMT) تنظیم کن و OK کن.
5. فایل‌های ساخته‌شده در `MQL5\Files` هستند؛ همه را در پوشه `data/market/raw/` داخل ریپو کپی کن: فایل‌های `rates_<NAME>_M5.csv`، فایل‌های `<NAME>_export_info.txt` و `symbols_sp500.csv`.
6. بعد به من خبر بده (این همان **CHECKPOINT B** است). من اعتبارسنجی و گزارش پوشش را اجرا می‌کنم و اعداد واقعی (اولین/آخرین روز کامل RTH، تعداد روزها، روزهای غایب) را برمی‌گردانم.
7. محدودیت‌ها: هیچ معامله‌ای انجام نمی‌شود و هیچ تنظیمی در ترمینال تغییر نمی‌کند؛ فایل‌های CSV دیتای بازار هرگز در گیتهاب قرار نمی‌گیرند.
