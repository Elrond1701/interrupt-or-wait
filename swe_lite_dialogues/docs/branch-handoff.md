# Adding this folder to an existing repository branch

This handoff is a regular folder, not a separate Git repository. It contains no remote URL, Git history, account login, or author Git identity.

1. In your teammate's existing clone, check `git status` and select the agreed starting branch. Keep unrelated local work separate.
2. Create a new branch, for example `git switch -c benchmark/swe-lite-dialogues`.
3. Copy the entire `swe_lite_dialogues` folder into that repository. Keep it as a subfolder so it does not replace the team's root README, settings, or code.
4. Enter the copied folder and run `python3 verify_release.py` and the offline tests from its README.
5. From the repository root, stage only this folder and inspect the staged files:

```sh
git add -- swe_lite_dialogues
git diff --cached --stat
git diff --cached --name-only
```

The list should contain source code, prompts, documentation, checksums, and the selected data. It should not contain local environments, credentials, run outputs, or historical duplicate exports. The folder-level `.gitignore` applies inside this subfolder; it does not change the team's root ignore rules.

When your team is ready, commit using your normal Git identity. Pushing the branch and opening a pull request are separate later steps. No upload is needed to test this handoff locally.

The current bundle fits in ordinary Git; no LFS configuration is required. Do not copy the surrounding research workspace into the team's repository. Keep author data and future messages outside any solver workspace even if both are managed by the same team.

`CHECKSUMS.json` records the shipped files. If the team intentionally edits a file, the checksum check should fail until a new reviewed release is recorded. Keep `CHANGELOG.md` updated and generate new checksums for that new release; never change a checksum merely to hide an unexpected modification.
