# GLOSSARY (DRAFT — taxonomy v1; numeric definitions proposed, calibrated in Phase 6)

Each Brooks term: plain definition → **proposed** numeric/algorithmic definition
with named parameters (defaults live in `config/default.yaml` once calibrated).
Class: `rule-based` (deterministic from bars) · `semi-subjective` (needs judgment
thresholds) · `contextual` (depends on day structure).

## Day types

| Term (canonical id) | Plain definition | Proposed numeric definition | Class |
|---|---|---|---|
| Spike and Channel Bull (`spike_and_channel_bull`) | Violent up-move (spike), then a slower grinding bull channel | Spike: ≥ `spike_min_bars` (3) consecutive strong bull bars with closes near highs and range > `spike_range_mult` × ATR; channel: subsequent overlap, pullbacks ≤ `channel_pullback_max` bars | rule-based |
| Spike and Channel Bear (`spike_and_channel_bear`) | Mirror image down | Mirror of bull | rule-based |
| Bull Trend From The Open (`bull_trend_from_open`) | Opens strong and trends up all day | First bar bull + day closes in top `trend_close_zone` (25%) of range + pullbacks < `trend_pullback_max_pct` (25%) of trend leg | semi-subjective |
| Bear Trend From The Open (`bear_trend_from_open`) | Mirror image down | Mirror of bull | semi-subjective |
| Small Pullback Bull Trend (`small_pullback_bull_trend`) | Bull trend whose pullbacks are tiny/shallow | Bull trend + every pullback ≤ `small_pullback_max_bars` (2) bars and < `small_pullback_depth` (33%) of prior leg | rule-based |
| Small Pullback Bear Trend (`small_pullback_bear_trend`) | Mirror image down | Mirror of bull | rule-based |
| Trading Range (`trading_range`) | Sideways, two-sided trade, no trend | Bar overlap > `range_overlap_pct` (60%) over ≥ `range_min_bars` (12) bars + EMA slope < `ema_flat_slope` | rule-based |
| Trending Trading Range (`trending_trading_range`) | Range with a drift/slope | Range criteria + net drift > `drift_min_atr` (1.0 ATR) | semi-subjective |
| Broad Bull/Bear Channel (`broad_bull_channel` / `broad_bear_channel`) | Loose channel, deep pullbacks but trend intact | Channel lines hold + pullbacks up to `broad_pullback_depth` (50–61.8%) | semi-subjective |
| Reversal Day (`reversal_day`) | Trend one way, then the opposite takes over | First-half trend ≥ `reversal_leg_min_atr` (1.5 ATR), second half reverses > `reversal_retrace_pct` (61.8%) | rule-based |
| Trend Reversal To Bull/Bear (`trend_reversal_to_bull`/`_bear`) | Prior trend ends, new trend begins | Swing break + opposite spike or H2/L2 with follow-through ≥ `reversal_follow_bars` (3) | semi-subjective |

## Events / patterns

| Term (canonical id) | Plain definition | Proposed numeric definition | Class |
|---|---|---|---|
| Spike (`spike`) | Burst of strong same-direction bars | ≥ `spike_min_bars` bars, body/range > `strong_body_ratio` (0.6), same direction | rule-based |
| Channel (`channel`) | Orderly overlapping grind after a spike | ≥ `channel_min_bars` (5) with overlap and higher lows (bull) | rule-based |
| Buy/Sell The Close (`buy_the_close`/`sell_the_close`) | Late-day continuation entry expecting close strength | Signal in last `close_window_min` (30) min of session, with-trend, stop at signal extreme ± `stop_buffer_ticks` | semi-subjective |
| Breakout / Failed Breakout (`breakout`/`failed_breakout`) | Price exits a range/line; failure = quick return inside | Close beyond level + `breakout_follow_bars` (1–2) bars same direction; fail = close back inside within `fail_window_bars` (3) | rule-based |
| Bull/Bear Flag (`bull_flag`/`bear_flag`) | Brief countertrend pause (1–3 bars) then continuation | Countertrend ≤ `flag_max_bars` (3), then with-trend breakout | rule-based |
| Wedge / Truncated Wedge (`wedge`/`truncated_wedge`) | 3-push reversal/continuation with converging legs; truncated = 3rd push fails early | 3 pushes, each ≤ `wedge_push_retrace` (76.4%) of prior, slope converging; truncated: push 3 < `trunc_push_pct` (50%) of push 2 | semi-subjective |
| Double Top/Bottom (`double_top`/`double_bottom`) | Two tests of a level, second fails | Two highs/lows within `dt_tolerance_ticks`, second reverses ≥ `dt_reverse_min_atr` (0.5 ATR) | rule-based |
| LH DT / HL DB (`lower_high_double_top`/`higher_low_double_bottom`) | Second test slightly worse (lower high / higher low) | DT/DB + second extreme worse by ≥ `lhhl_min_ticks` (1 tick), better by < `dt_tolerance_ticks` | rule-based |
| Micro DT/DB (`micro_double_top`/`micro_double_bottom`) | 2–3 bar mini double | Same as DT/DB within `micro_max_span` (3) bars | rule-based |
| Measured Move (`measured_move`) | Leg 2 ≈ leg 1 in points | Project leg-1 size from leg-2 start; target zone ± `mm_tolerance_pct` (10%) | rule-based |
| 50% Pullback (`pullback_50pct`) | Pullback retraces about half the leg | Retrace within `pullback_band` (40–60%) of leg | rule-based |
| H1/H2, L1/L2 (`h1`/`h2`/`l1`/`l2`) | 1st/2nd pullback buy/sell in a trend | Pullback count after a swing + signal bar close in trend direction | rule-based |
| Major Bull/Bear Surprise (`major_bull_surprise`/`major_bear_surprise`) | Unexpected large with-trend bar after stall | Bar range > `surprise_range_mult` (2.0) × ATR(20) with trend-direction close | rule-based |
| Trend Line Break (`trend_line_break`) | Swing-based trend line violated | Close beyond line by ≥ `line_break_ticks` + next bar confirms | rule-based |
| Channel Line Overshoot (`channel_line_overshoot`) | Spike past the parallel then back inside | Wick beyond parallel ≥ `overshoot_min_ticks`, close back inside within `overshoot_window` (2) bars | rule-based |
| Gap / Body Gap (`gap`/`body_gap`) | Overnight/intraday gap; body gap = bodies don't overlap | High/low (or bodies) disjoint from prior bar by ≥ `gap_min_ticks` (1) | rule-based |
| EMA Gap Bar (`ema_gap_bar`) | Big bar gapping away from the EMA | Distance close→EMA(20) > `ema_gap_mult` (1.0) × ATR | rule-based |
| Climax / Exhaustive Climax (`climax`/`exhaustive_climax`) | Parabolic extreme; exhaustive = likely final push | Range > `climax_mult` (2.5) × ATR + reversal within `climax_window` (3) bars (exhaustive) | semi-subjective |
| Final Flag (`final_flag`) | Last pause before the trend ends | Flag after ≥ `late_flag_pushes` (2) pushes + subsequent reversal | contextual |
| Opening Reversal (`opening_reversal`) | First swing reverses the opening drive | Opening drive ≥ `open_drive_min_atr` (0.75 ATR), reversal within `open_window_bars` (6) bars | rule-based |
| Trading Range Begin/End (`trading_range_begin`/`_end`) | Range boundaries | First/last bar satisfying range criteria | rule-based |
| Signal/Entry Bar (`signal_bar`/`entry_bar`) | Setup bar / trigger bar | Signal: pattern completion bar; entry: first bar trading through signal extreme | rule-based |
| Failed Signal (`failed_signal`) | Entry triggers then immediately fails | Entry bar close back beyond signal extreme within `fail_window_bars` | rule-based |

> All thresholds are proposals. Phase 6 turns this draft into `docs/PATTERN_SPEC.md`
> with exact algorithms; parameters move into `config/default.yaml`.
