"""harness.swebench: dataset conversion, scripted end-to-end runs, and scorer-compatible predictions.

No Docker or API key: the environment is a local git repo and the model is scripted.
"""

import json
import sys

import pytest

from minisweagent.environments.local import LocalEnvironment

from harness import swebench, toy

RECORDS = swebench.load_records()
THREE = "django__django-12983"  # slugify: U0 -> U1 -> U2
SUBMIT = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt"  # as in interactive_swebench.yaml


def edit(n: int) -> str:
    return f"echo 'x = {n}' >> calc.py && git diff -- calc.py > patch.txt"


def run(tmp_path, condition, script, **kwargs):
    repo = toy.make_repo(tmp_path / "repo")
    config = swebench.load_config(cost_limit=0)  # the scripted model bills $1/call; 0 = no limit, as in test_harness
    return swebench.run_one(
        RECORDS[THREE],
        condition,
        config,
        tmp_path / "out",
        make_env=lambda record, cfg: LocalEnvironment(cwd=str(repo)),
        make_model=lambda: toy.scripted_model(script),
        **kwargs,
    )


def trajectory(tmp_path) -> dict:
    return json.loads((tmp_path / "out" / f"{THREE}.traj.json").read_text())


# Conversion


def test_dataset_has_152_conversations():
    assert len(RECORDS) == 152


@pytest.mark.parametrize("condition", ["upfront", "interrupt", "wait"])
def test_every_conversation_converts(condition):
    for record in RECORDS.values():
        pieces = swebench.to_pieces(record, condition).pieces
        if condition == "upfront":
            assert [p.text for p in pieces] == [record["full_prompt"]]
        else:
            assert [p.text for p in pieces] == [m["content"] for m in record["messages"]]


def test_interrupt_releases_are_staggered():
    pieces = swebench.to_pieces(RECORDS[THREE], "interrupt", interrupt_gap=4).pieces
    assert [p.release.label if p.release else None for p in pieces] == [
        None,
        "after_first_edit+0",
        "after_first_edit+4",
    ]
    with pytest.raises(ValueError):
        swebench.to_pieces(RECORDS[THREE], "interrupt", interrupt_gap=0)


# Scripted runs


def test_upfront_sends_only_the_reconciled_final_task(tmp_path):
    result = run(tmp_path, "upfront", [("Work.", edit(1)), ("Submit.", SUBMIT)])
    assert result["exit_status"] == "Submitted"
    assert result["delivered"] == ["full"] and result["rounds"] == 1
    opening = trajectory(tmp_path)["messages"][1]["content"]
    assert RECORDS[THREE]["full_prompt"] in opening
    assert RECORDS[THREE]["messages"][0]["content"] not in opening  # no withdrawn U0/U1 requirements


def test_wait_delivers_each_message_after_a_submit(tmp_path):
    script = [("U0", edit(1)), ("Submit.", SUBMIT), ("U1", edit(2)), ("Submit.", SUBMIT), ("U2", edit(3)),
              ("Submit.", SUBMIT)]
    result = run(tmp_path, "wait", script)
    assert result["exit_status"] == "Submitted"
    assert result["delivered"] == ["U0", "U1", "U2"] and result["rounds"] == 3
    assert "+x = 1" in result["model_patch"] and "+x = 3" in result["model_patch"]  # the final round's patch
    assert [d["trigger"] for d in trajectory(tmp_path)["harness"]["deliveries"]] == ["opening", "on_submit",
                                                                                      "on_submit"]


def test_interrupt_releases_after_first_edit_then_gap(tmp_path):
    script = [("Look.", "cat calc.py"), ("Edit.", edit(1)), ("Edit.", edit(2)), ("Edit.", edit(3)),
              ("Submit.", SUBMIT)]
    result = run(tmp_path, "interrupt", script, interrupt_gap=2)
    assert result["exit_status"] == "Submitted" and result["rounds"] == 1
    deliveries = trajectory(tmp_path)["harness"]["deliveries"]
    assert [(d["piece_id"], d["step"]) for d in deliveries] == [("U0", 0), ("U1", 2), ("U2", 4)]


def test_errors_are_recorded_and_left_out_of_predictions(tmp_path):
    def no_docker(record, config):
        raise RuntimeError("Cannot connect to the Docker daemon")

    result = swebench.run_one(RECORDS[THREE], "wait", swebench.load_config(), tmp_path, make_env=no_docker)
    assert result["exit_status"] == "RuntimeError" and "Docker daemon" in result["error"]
    assert not swebench.finished(tmp_path, THREE)
    assert swebench.write_predictions(tmp_path, "m")[1] == []


def test_predictions_are_accepted_by_the_scorer(tmp_path, monkeypatch):
    run(tmp_path, "wait", [("U0", edit(1)), ("Submit.", SUBMIT), ("U1", edit(2)), ("Submit.", SUBMIT),
                           ("U2", edit(3)), ("Submit.", SUBMIT)])
    predictions, ids = swebench.write_predictions(tmp_path / "out", "anthropic/claude-sonnet-4-5-20250929")
    assert ids == [THREE]
    monkeypatch.setattr(sys, "dont_write_bytecode", True)  # leave Sihong's checksummed folder untouched
    monkeypatch.syspath_prepend(str(swebench.SCORER.parent))
    import evaluate_benchmark

    job = evaluate_benchmark.prepare(swebench.DATASET_DIR, predictions, "wait", tmp_path / "job", [THREE])
    assert [t["instance_id"] for t in job["tasks"]] == [THREE] and job["condition"] == "wait"
