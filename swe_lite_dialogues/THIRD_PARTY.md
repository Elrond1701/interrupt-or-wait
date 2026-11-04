# Sources and notices

- Original task data: [princeton-nlp/SWE-bench_Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite). The bundled snapshot contains its 300 test rows. The original download did not record an upstream commit; local content hashes pin the included snapshot. This is a limitation, not a claim of upstream revision pinning.
- Evaluation software: [SWE-bench v4.1.0](https://github.com/SWE-bench/SWE-bench/tree/v4.1.0), installed separately through `requirements-eval.txt`. Its [package metadata](https://github.com/SWE-bench/SWE-bench/blob/v4.1.0/pyproject.toml) specifies Python 3.10 or later.
- Vendored Django fragments: source URLs, revisions, and hashes are listed in `split_pilot/source_manifest.json`; the bundled license is [LICENSE-Django.txt](split_pilot/vendor/LICENSE-Django.txt).

Original issues, patches, tests, and upstream notices are retained. Public names, URLs, and example paths appearing inside original issue text are source content, not personal configuration from the dataset constructor. This handoff does not assign a new project-wide license or replace upstream licenses; coordinate project licensing with the receiving repository.
