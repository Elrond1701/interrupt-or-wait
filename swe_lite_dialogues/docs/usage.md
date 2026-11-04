# Using the data and scoring final patches

All commands below run from the folder containing `README.md`.

## One record is one conversation

Read `split_pilot/benchmark_output/basic_v34/candidates.jsonl`: one JSON object per line.

| Field | Meaning |
|---|---|
| `group_id`, `source.instance_id` | The original task ID; unique in this release |
| `source.repo`, `source.base_commit` | Repository and starting code revision |
| `messages` | Ordered U0/U1, or U0/U1/U2, with English `content` |
| `trajectory_type` | One label for the whole conversation |
| `stage_annotations` | Requirements added, removed, unresolved, or active at each stage |
| `final_requirement_ids` | Requirements that remain in force at the end |
| `full_prompt` | Complete final task, used by the full-upfront comparison |
| `evaluation` | Original scoring linkage; some flags describe construction-time status |
| `provenance` | Historical generation/review references and hashes, not solver input |

The four labels are **Cumulative** (add requirements while keeping earlier ones), **Clarification** (resolve uncertainty or refine a compatible goal), **Revision** (replace an earlier requirement), and **Mixed** (combine update types). Labels describe actual annotations, rather than a required quota.

The final goal is the union of requirements still in force, not necessarily the last message alone. Temporary requirements must be explicitly withdrawn when replaced. The construction review checks equivalence to the original task; mechanical checks cannot prove semantic equivalence by themselves.

`evaluation_sources.jsonl` preserves the original rows, including `patch`, `test_patch`, `FAIL_TO_PASS`, and `PASS_TO_PASS`. It is evaluator-only. A correct solver patch need not match the reference patch text.

## Deliver the messages

1. Prepare a separate clean repository checkout at `source.base_commit`.
2. In the controller process, load one record and create `Delivery(record, "wait")`.
3. Send only `visible_history()` to your agent. Keep the same code workspace and conversation across rounds.
4. After a completed shell action, call `accept(action, observation=tool_result)`. After the agent ends a round, call `accept({"action": "submit", "command": "", "text": "Done"})`. A submission releases the next user message or ends the final round.
5. Save the final code diff relative to the original base revision; score it externally.

See `demo.py` for the minimal delivery loop. `run_episode()` in `delivery.py` also accepts model and workspace adapters, but those adapters must be supplied by the experiment runner. A free-form question is held for answer review; the controller does not invent a response.

The optional `full` condition supplies the complete final task upfront. `interrupt` releases updates after a configured number of completed tool actions, with an earlier submission also releasing an update. It does not implement random wall-clock interruptions.

## Install the optional evaluator

Docker must be running **only for the actual test-execution step**. Install its official distribution for your operating system. Then:

```sh
python3 -m venv split_pilot/.venv-eval
split_pilot/.venv-eval/bin/python -m pip install -r requirements-eval.txt
docker info
```

The pinned harness is `swebench==4.1.0`, matching the existing scoring interface. This pins the grader, not every transitive dependency. Installations and task images can require network access; clean installs on all operating systems have not been verified.

On Apple Silicon, historical runs needed explicit `linux/amd64` pulls for official x86_64 images. For the validated Django example:

```sh
docker pull --platform linux/amd64 swebench/sweb.eval.x86_64.django_1776_django-14017:latest
```

Other tasks have different image names; follow their official TestSpec. Loading the dataset does not require downloading all images.

## Prepare and run a small evaluation

Create `outputs/predictions.jsonl` outside the solver workspace. Each line has exactly three fields:

```json
{"instance_id":"django__django-14017","model_name_or_path":"team-model","model_patch":""}
```

Replace the empty string with the agent's actual git diff. Empty patches count as failures. Use one model and condition per file. The following commands explicitly select this one task; all-task evaluation requires one prediction per selected task.

```sh
python3 split_pilot/evaluate_benchmark.py prepare --dataset split_pilot/benchmark_output/basic_v34 --predictions outputs/predictions.jsonl --instance-ids django__django-14017 --condition wait --output outputs/first_wait
python3 split_pilot/evaluate_benchmark.py run --job outputs/first_wait
python3 split_pilot/evaluate_benchmark.py summarize --job outputs/first_wait
```

`prepare` validates and freezes inputs without starting Docker. `run` invokes the official harness; `summarize` reads results without rerunning tests. Results include overall, category, and message-count groups. Missing/incomplete reports remain `unscored`; only `complete=true` represents a completed requested evaluation. Inspect raw test logs for formal results, including environment and patch-application errors.

Prepare a **new output directory** for each run. Evaluation jobs contain local paths and must be prepared again after moving to another machine. Do not copy old job folders as runnable jobs.
