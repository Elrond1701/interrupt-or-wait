"""Offline author-side checks, using stdlib only.

Run: python3 split_pilot/verify_split.py
This does NOT run an agent, Docker, or the complete SWE-bench harness.
slugify is extracted by AST with its lazy decorator removed: plain strings only.
ValidationError uses unchanged upstream modules and the dataset's test patch in
an isolated minimal package. Partial implementations are handwritten witnesses,
not model outputs or recommended patches.
"""

import ast
import hashlib
import importlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parent


def apply_patch(directory, patch):
    result = subprocess.run(
        ["patch", "-p1", "--batch", "--fuzz=0"],
        input=patch, text=True, cwd=directory,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def load_slugify(source):
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "slugify")
    fn.decorator_list = []
    module = ast.Module(body=[fn], type_ignores=[])
    namespace = {"re": re, "unicodedata": unicodedata}
    exec(compile(ast.fix_missing_locations(module), "<upstream-slugify>", "exec"), namespace)
    return namespace["slugify"]


def check_groups(groups):
    output = {}
    for name, checks in groups.items():
        results = []
        for label, check in checks:
            try:
                passed = bool(check())
                results.append({"check": label, "passed": passed})
            except Exception as e:
                results.append({"check": label, "passed": False, "error": type(e).__name__ + ": " + str(e)})
        output[name] = {"passed": sum(x["passed"] for x in results), "total": len(results), "checks": results}
    return output


def slugify_checks(fn):
    cases = {
        "U0_dashes": [
            ("--strip-dash-value---", "strip-dash-value", False),
            ("---This is a test---", "this-is-a-test", False),
        ],
        "U1_underscores_and_mixed": [
            ("__strip__underscore-value___", "strip__underscore-value", False),
            ("__strip-mixed-value---", "strip-mixed-value", False),
            ("_ -strip-mixed-value _-", "strip-mixed-value", False),
        ],
        "unchanged_behavior": [
            ("Hello, World!", "hello-world", False),
            (" multiple---dash and  space ", "multiple-dash-and-space", False),
            ("underscore_in-value", "underscore_in-value", False),
            ("spam & ıçüş", "spam-ıçüş", True),
        ],
    }
    return check_groups({
        group: [(s, lambda s=s, expected=expected, unicode=unicode: fn(s, allow_unicode=unicode) == expected)
                for s, expected, unicode in rows]
        for group, rows in cases.items()
    })


def validation_checks(V):
    def scalar(**kwargs):
        return V("bad %(x)s", code="invalid", params={"x": 1}, **kwargs)

    def hashable_equal(a, b):
        return a == b and hash(a) == hash(b) and len({a, b}) == 1

    return check_groups({
        "U0_scalar_equality": [
            ("equal scalar instances", lambda: V("bad") == V("bad")),
            ("different messages", lambda: V("bad") != V("other")),
            ("different codes", lambda: V("bad", code="a") != V("bad", code="b")),
            ("same params in different key order", lambda: V("%(a)s %(b)s", params={"a": 1, "b": 2}) == V("%(a)s %(b)s", params={"b": 2, "a": 1})),
            ("different params", lambda: V("%(a)s", params={"a": 1}) != V("%(a)s", params={"a": 2})),
        ],
        "U1_list_equality": [
            ("reordered messages", lambda: V(["alpha", "beta"]) == V(["beta", "alpha"])),
            ("same message retains code", lambda: V([V("bad", code="a")]) != V([V("bad", code="b")])),
            ("multiplicity preserved", lambda: V(["a", "a"]) != V(["a"])),
            ("different structures", lambda: V("a") != V(["a"])),
        ],
        "U2_field_and_nested_equality": [
            ("reordered fields and errors", lambda: V({"left": ["a", "b"], "right": "c"}) == V({"right": "c", "left": ["b", "a"]})),
            ("field identity matters", lambda: V({"left": "a"}) != V({"right": "a"})),
            ("nested scalar metadata", lambda: V({"left": scalar()}) == V({"left": scalar()})),
            ("scalar vs field dictionary", lambda: V("a") != V({"left": "a"})),
        ],
        "U3_hash_consistency": [
            ("scalar hash", lambda: hashable_equal(V("a"), V("a"))),
            ("list hash", lambda: hashable_equal(V(["a", "b"]), V(["b", "a"]))),
            ("field hash", lambda: hashable_equal(V({"x": "a", "y": "b"}), V({"y": "b", "x": "a"}))),
            ("nested hash", lambda: hashable_equal(V({"x": scalar()}), V({"x": scalar()}))),
        ],
    })


def partial_validation(V, level):
    """Witness implementation supporting only the revealed structures."""
    def freeze(value):
        if isinstance(value, dict):
            return tuple(sorted((k, freeze(v)) for k, v in value.items()))
        if isinstance(value, (list, tuple)):
            return tuple(freeze(v) for v in value)
        return value

    def key(value):
        if hasattr(value, "message"):
            return ("scalar", value.message, value.code, freeze(value.params))
        if hasattr(value, "error_dict"):
            if level < 2:
                raise NotImplementedError
            return ("dict", tuple(sorted((k, tuple(sorted((key(v) for v in vals), key=repr))) for k, vals in value.error_dict.items())))
        if level < 1:
            raise NotImplementedError
        return ("list", tuple(sorted((key(v) for v in value.error_list), key=repr)))

    def eq(self, other):
        if not isinstance(other, V):
            return NotImplemented
        try:
            return key(self) == key(other)
        except NotImplementedError:
            return self is other

    V.__eq__ = eq
    V.__hash__ = None


def worker(directory, mode):
    sys.path.insert(0, str(directory))
    V = importlib.import_module("django.core.exceptions").ValidationError
    official = None
    if mode in ("base", "gold"):
        suite = unittest.defaultTestLoader.discover(
            str(directory / "tests/test_exceptions"),
            pattern="test_validation_error.py",
        )
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
        official = {
            "tests_run": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "skipped": len(result.skipped),
            "successful": result.wasSuccessful(), "log": stream.getvalue(),
        }
    else:
        partial_validation(V, int(mode))
    return {"official_selected_test_file": official, "probe_groups": validation_checks(V)}


def main():
    references = {
        r["instance_id"]: r
        for r in json.loads((ROOT / "author_reference.json").read_text())["instances"]
    }
    report = {
        "scope": "Offline semantic feasibility checks only; no LLM, interruption runner, Docker, or full SWE-bench evaluation.",
        "python_version": sys.version,
        "input_hashes": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                Path(__file__).resolve(), ROOT / "author_reference.json",
                ROOT / "task_cards.json", ROOT / "requirements.json",
                *(p for p in (ROOT / "vendor").rglob("*") if p.is_file()),
            ]
            if path.is_file()
        },
        "limitations": [
            "Finite passing tests are evidence, not proof of full semantic equivalence.",
            "slugify checks omit lazy wrappers and all unrelated Django regressions.",
            "ValidationError runs one original test file plus constructed probes in a minimal package, not the full Django test runner.",
            "Witness implementations are manually constructed; this does not predict agent behavior or prove every update is necessary for every solver.",
            "All author_reference, vendor, task cards, reports and future messages must remain outside solver workspaces.",
        ],
    }
    with tempfile.TemporaryDirectory(prefix="swe-split-") as tmp:
        tmp = Path(tmp)
        slug = tmp / "slug"
        shutil.copytree(ROOT / "vendor/slugify", slug)
        slug_file = slug / "django/utils/text.py"
        base = slug_file.read_text()
        partial = base.replace("return re.sub(r'[-\\s]+', '-', value)", "return re.sub(r'[-\\s]+', '-', value).strip('-')")
        if partial == base:
            raise RuntimeError("Could not construct dash-only witness.")
        apply_patch(slug, references["django__django-12983"]["patch"])
        gold_source = slug_file.read_text()
        report["django__django-12983"] = {
            "base": slugify_checks(load_slugify(base)),
            "U0_witness": slugify_checks(load_slugify(partial)),
            "gold": slugify_checks(load_slugify(gold_source)),
        }
        initial_revision_source = gold_source.replace(
            ".strip('-_')", ".replace('_', '').strip('-')"
        )
        if initial_revision_source == gold_source:
            raise RuntimeError("Could not construct revision witness.")
        initial_revision = load_slugify(initial_revision_source)
        final_revision = load_slugify(gold_source)
        report["slugify_constructed_revision"] = {
            "description": "Synthetic U0 deletes underscores everywhere; U1 changes this to boundary-only deletion. Final target returns to the original issue.",
            "initial_witness_U0": check_groups({
                "U0": [
                    ("remove all underscores", lambda: initial_revision("__a_b__") == "ab"),
                    ("trim boundary dashes", lambda: initial_revision("---abc---") == "abc"),
                    ("preserve normal slug behavior", lambda: initial_revision("Hello World") == "hello-world"),
                ]
            }),
            "initial_witness_final": slugify_checks(initial_revision),
            "gold_final": slugify_checks(final_revision),
        }

        val_base = tmp / "val_base"
        shutil.copytree(ROOT / "vendor/validation_error", val_base)
        for path in ["django", "django/core", "django/utils"]:
            (val_base / path / "__init__.py").write_text("")
        apply_patch(val_base, references["django__django-13220"]["test_patch"])
        val_gold = tmp / "val_gold"
        shutil.copytree(val_base, val_gold)
        apply_patch(val_gold, references["django__django-13220"]["patch"])
        report["django__django-13220"] = {}
        for mode in ["base", "0", "1", "2", "gold"]:
            path = val_gold if mode == "gold" else val_base
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker", str(path), mode],
                check=True, capture_output=True, text=True,
            )
            report["django__django-13220"][mode] = json.loads(result.stdout)

    def all_pass(groups):
        return all(g["passed"] == g["total"] for g in groups.values())
    slug_result = report["django__django-12983"]
    val_result = report["django__django-13220"]
    assertions = {
        "slug_base_fails_new_goal": not all_pass(slug_result["base"]),
        "slug_initial_witness_satisfies_U0": all_pass({"U0": slug_result["U0_witness"]["U0_dashes"], "unchanged": slug_result["U0_witness"]["unchanged_behavior"]}),
        "slug_initial_witness_fails_U1": not all_pass({"U1": slug_result["U0_witness"]["U1_underscores_and_mixed"]}),
        "slug_gold_passes_all_probes": all_pass(slug_result["gold"]),
        "validation_base_fails_original_test_file": not val_result["base"]["official_selected_test_file"]["successful"],
        "validation_gold_passes_original_test_file": val_result["gold"]["official_selected_test_file"]["successful"],
        "validation_gold_passes_all_probes": all_pass(val_result["gold"]["probe_groups"]),
    }
    revision = report["slugify_constructed_revision"]
    assertions.update({
        "revision_initial_witness_satisfies_U0": all_pass(revision["initial_witness_U0"]),
        "revision_initial_witness_fails_final": not all_pass(revision["initial_witness_final"]),
        "revision_gold_satisfies_final": all_pass(revision["gold_final"]),
    })
    names = list(val_result["gold"]["probe_groups"])
    for level in range(3):
        groups = val_result[str(level)]["probe_groups"]
        assertions[f"validation_witness_{level}_passes_revealed"] = all_pass({k: groups[k] for k in names[:level+1]})
        assertions[f"validation_witness_{level}_fails_next"] = not all_pass({names[level+1]: groups[names[level+1]]})
    report["checks"] = assertions
    report["candidate_decisions"] = {
        "slugify_addition": "PASS isolated feasibility checks; full SWE-bench validation and agent trials still required.",
        "slugify_constructed_revision": "PASS isolated feasibility checks; synthetic initial requirement, same original final endpoint.",
        "validation_error_U0_U1_U2_U3": "HOLD: gold fails reordered errors inside a field; original tests do not cover this combination. Do not silently delete the failing probe.",
    }
    (ROOT / "verification_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checks": assertions, "all_checks_passed": all(assertions.values()), "report": str(ROOT / "verification_report.json")}, ensure_ascii=False, indent=2))
    if not all(assertions.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        print(json.dumps(worker(Path(sys.argv[2]), sys.argv[3])))
    else:
        main()
