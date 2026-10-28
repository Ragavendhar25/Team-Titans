# LabelGuard P3 PoC (Team Titans, P-2026-29-CD-003-AY26-27)

Question tested: can OCR + rules reach >=90% field accuracy on 30 labels vs a truth key, with 0 silent errors, in <=10 s per label?

## Component status
| Component | Status |
|---|---|
| Label images (60, script-generated, seeds 20261028 and 7777) | MOCKED |
| Tesseract OCR, `--psm 6`, no tuning | REUSED |
| `labelguard_poc.py` rule check, v0.1 and v0.2 | BUILT |
| Inspector UI (UNCERTAIN -> inspector reads) | PLANNED |
| Timed manual comparator | Not run |

Note: the script was rebuilt on 28 Oct 2026 to the P2 PoC plan; all numbers below come from running it. Real-photo test is still pending.

## Replay
Needs Python 3, Pillow, and the Tesseract CLI.
```
python labelguard_poc.py run1 v0.1        # seed 20261028
python labelguard_poc.py run2 v0.2        # same 30 labels
python labelguard_poc.py run3 v0.2 7777   # 30 fresh labels
```
Outputs go to `out/` (per-field CSV, summary JSON). Our recorded copies are in `results/`.

## Results (measured, synthetic labels only)
| Run | Version / data | T1 accuracy (>=189/210) | T2 silent-wrong labels (target 0/30) | T3 median time (<=10 s) |
|---|---|---|---|---|
| R1 | v0.1, seed 20261028 | 198/210 (94.3%) pass | 2/30 (L22, L25) FAIL | 0.31 s pass |
| R2 | v0.2, same 30 | 196/210 (93.3%) pass | 1/30 (L22) FAIL | 0.30 s pass |
| R3 | v0.2, seed 7777 (fresh) | 196/210 (93.3%) pass | 2/30 (L03, L23) FAIL | 0.30 s pass |

Manual-time comparator: Not tested. UNCERTAIN fields count as not correct in T1.

## Limits
- v0.2 reduces but does not remove silent errors; R3 L03 is an OCR digit misread (1800 read as 1300) that no rule catches.
- Synthetic labels only: no real photos, curved or regional packs, inspector use, hosting cost, or manual-time saving shown.
- No field or enforcement use. No personal data. Department permission pending.

## Files
- `labelguard_poc.py` : generator + OCR + rule check
- `results/` : run logs, per-field CSVs, summary JSON
- `SoI_P3_P-2026-29-CD-003-AY26-27_LabelGuard_v01.mp4` : demo video (<=120 s)
