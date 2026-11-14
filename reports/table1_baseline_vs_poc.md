Baseline: `baseline` (git b0ce8bf, seed 42) · PoC: `poc` (git b0ce8bf, seed 42)

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Better | N |
|---|---|---|---|---|---|---|---|
| **Defect Recall@B** (GT defects in top-B / GT defects) | all | 0.8696 | 0.6522 | -0.2174 | -25.0% | higher | 40 |
| Precision@B (GT defects in top-B / B) | all | 1.0000 | 0.7500 | -0.2500 | -25.0% | higher | 40 |
| Defect-type accuracy (GT defects) (fraction) | all | n/a | 0.3913 | n/a | n/a | higher | 23 |
| False alarm in top-B (clean images in top-B / clean images) | light=day | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 20 |
| False alarm in top-B (clean images in top-B / clean images) | light=dusk | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 4 |
| False alarm in top-B (clean images in top-B / clean images) | light=night | 0.0000 | 0.8333 | 0.8333 | baseline=0 | lower | 16 |
| Runtime / 100 items (s) | all | 0.3026 | 0.3758 | | | lower | |
