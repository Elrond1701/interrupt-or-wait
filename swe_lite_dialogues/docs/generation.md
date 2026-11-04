# Generating more conversations

Reading or evaluating the shipped 152 conversations does not require generation. This workflow is for authors creating a separate new batch.

```text
Original issue
  → LLM extracts the complete final requirements
  → Author review checks the issue and original tests
  → LLM proposes a category and temporary/uncertain requirements
  → Author review checks meaningful updates and the locked final goal
  → Program enumerates legal plans; LLM selects one and writes English messages
  → Author review checks wording, replacements, and final equivalence
  → Program exports one conversation per original
```

The normal path has up to four construction calls: endpoint extraction, category design, plan selection, and wording. Docker is not used here. Reviewers may use an assistant, but approval is an explicit semantic decision, not a rule that all generated output passes.

## Modules and prompts

| Step | Main file / prompt | Role |
|---|---|---|
| Batch control | `source_batch.py` | Small resumable batches, call limits, review stops |
| Final requirements | `prompts/extract_endpoint_v1.txt` | Extract the full original goal without dialogue policy |
| Category design | `prompts/extract_category_v2.txt`, `v3.txt` | Prefer natural three-message plans and underrepresented classes |
| Plan selection | `prompts/select_stage_plan_v5.txt`, `v6.txt` | Choose from program-validated plans |
| English wording | `prompts/propose_trajectory_v10.txt` | Express fixed stage requirements naturally |
| Checks and export | `source_dataset.py` | Review bindings, final-state checks, original-test mapping, one-to-one export |

The `strong_v1` policy requests `gpt-6.1-sol` with `medium` reasoning through the Codex CLI. This describes the saved pipeline configuration, not a guarantee that every teammate account can access that model. The base `codex_config.json` retains the older profile for compatibility; `source_batch.py` writes the strong profile into each new batch. Earlier admitted records retain their own generation provenance.

## Preview a new batch without a model call

```sh
python3 split_pilot/source_batch.py --output split_pilot/source_runs/team_trial_01 --instances django__django-14017 --balance-categories --construction-policy strong_v1 --target-total 4 --max-new-calls 0
```

This writes a local batch plan and status. The target of four is a scheduling input, not a request to generate four variants of this issue. This example rebuilds one already-published original in a separate experiment; do not append it as another independent sample.

## Run generation only when ready

Install the [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) and authenticate with **your own account**, following the [official authentication guide](https://learn.chatgpt.com/docs/auth?surface=cli). The CLI must be on `PATH`. No account configuration or credentials are shipped here. The current provider requires ChatGPT authentication and does not silently fall back to API billing. Account/model availability and CLI flag compatibility must be checked in your environment.

```sh
python3 split_pilot/source_batch.py --output split_pilot/source_runs/team_trial_01 --live --max-new-calls 1
```

This can spend model allowance. It stops at a missing review rather than automatically accepting a draft. Read `status.json` and the generated files. Before proceeding:

- Review `contract/source.json` and `contract/contract.json`, then provide a hash-bound `contract_review.json`. Required checks and test mappings are defined by `CONTRACT_CHECKS` and `reviewed_contract()` in `source_dataset.py`.
- Review `category_contract/` similarly, including `PROGRESSIVE_CHECKS` and the endpoint/category policy hashes. Keep the approved final requirements unchanged.
- After both reviews pass, resume with `--max-new-calls 2` for selection and wording. Review `generation/` and supply `semantic_review.json`, binding the candidate, plan, and wording hashes and the checks in `planned_generation.REVIEW_CHECKS`.

An accepting review uses `verdict: "accept_for_development"`, a nonempty reviewer label, and explicit check results. A questionable draft should receive `verdict: "hold"` plus a reason. Do not fabricate approvals or copy review hashes from another task. There is no review UI or automatic semantic reviewer in this package. Re-running an unchanged completed/review-pending batch does not silently retry model calls; use a new directory for intentional retries.

Export a newly reviewed conversation separately:

```sh
python3 split_pilot/source_dataset.py export --runs split_pilot/source_runs/team_trial_01/django__django-14017/generation --output split_pilot/benchmark_output/team_trial_01
```

Inspect the output manifest and exclusions before using it. The `.gitignore` keeps fresh runs and new exports local until intentionally reviewed for sharing.

## Historical evidence is a separate archive

The compact handoff omits historical `source_runs`, `codex_runs`, and runtime evidence. They are not needed to load the shipped dataset or score new final patches.

**Do not use `--existing .../basic_v34` with generation/export in this compact copy.** Selection revalidates historical review files; without the separate archive, it can exclude those old records. Likewise, `check_pipeline.py` is a full construction-replay tool and requires that archive. `verify_release.py` is the supported offline handoff check. To extend the published set, restore its author evidence first, or keep new batches separate until an explicit merge is reviewed.
