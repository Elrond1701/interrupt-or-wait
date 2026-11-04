# Validation scope and limitations

This is the first team handoff of `basic_v34`, not an all-task runtime certification.

| Layer | Evidence / status |
|---|---|
| Construction | All 300 originals attempted; 152 selected and 148 not selected. Historical author checks rebuilt the selected export and retained original scoring rows. |
| Handoff checks | File hashes, record identities, final annotation sets, scripted delivery, and scoring-input preparation are checked offline by `verify_release.py`. |
| Program tests | Fixed fixtures exercise generation review stops, category handling, delivery isolation, and scoring denominators. No model or Docker calls. |
| Author runtime | Historical base/gold runs exist for three tasks listed below; the other 149 are not environment-validated. Raw evidence remains in the separate author archive. |
| Real agent experiments | No general solver adapter or new model scores are included. Scripted delivery and gold-patch tests are not agent success rates. |
| Intermediate stages | No dataset-wide intermediate score or per-stage gold requirement. Final scoring uses the original task tests. |

Historical author checks:

| Original | Base target tests | Gold target tests | Named regression tests |
|---|---:|---:|---:|
| django__django-12983 (slugify) | 0/1 | 1/1 | 15/15 for both |
| django__django-14017 | 0/2 | 2/2 | 147/147 for both |
| sympy__sympy-20322 | 0/1 | 1/1 | 89/89 for both |

Base failures are expected. The latter two runs also checked the original issue examples and reconciled raw logs. These are summaries of earlier runs, not Docker runs performed while packaging. The original manifest and per-record environment flags reflect construction-time evidence (one task); `statistics.json` and `preview.json` separately report the three later-known author checks.

Known limits are retained:

- Categories are uneven; Mixed accounts for 86/152 and many examples use a similar clarify-then-revise pattern.
- Some early messages ask for investigation or describe behavior already satisfied by the base. Not every round requires an independent code edit.
- The original tests sometimes cover a shared component rather than every detail of the issue text. Passing them is not proof of complete semantic equivalence.
- Semantic review was assistant-assisted, not independent certification. A six-task historical spot check found no new blocking issue; it was not a random estimate of error rate.
- Admitted records come from multiple frozen model/prompt versions. Dataset proportions are not a controlled comparison of model quality.
- The 148 non-selected tasks include source/test conflicts, weak splits, and execution failures. They may be reconsidered; no full exclusion ledger is included in this compact package.
- `swebench==4.1.0` is a compatibility baseline. Formal experiments should retain raw logs and separately investigate upstream grader limitations.

Packaging preserves `candidates.jsonl`, `evaluation_sources.jsonl`, the source snapshot, and the other unchanged dataset files byte-for-byte. Only sharing metadata, documentation, test fixtures/paths, and evaluation-status wording were adapted. Production pipeline code is unchanged. `PACKAGING.json` records those changes. No task was regenerated or relabeled for this handoff.
