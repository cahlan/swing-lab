# Harness log

Each entry is a failure that actually happened and the part of the harness it changed. Newest first. Entries dated 2026-11-25 come from the design session before the first commit.

| Date | What went wrong | What changed |
| --- | --- | --- |
| 2026-11-25 | Pilot: a check disagreed and nothing said whether the readers chose different frames or read the same frames differently | `check` records and prints key frames chosen more than a frame apart |
| 2026-11-25 | Pilot: `next` gave out a swing that another agent was still measuring | `next` hands each swing out once; `resume` lists unfinished ones |
| 2026-11-25 | Pilot: `file` and `check` printed readings, which reached the orchestrator and its report | Both are quiet by default; `check` prints names, not values |
| 2026-11-25 | Pilot: no way to measure a swing again after the instructions change | `reset` sets a swing aside to be re-measured and keeps the old record in `superseded/` |
| 2026-11-25 | An audit against Cahlan's loop principles found the record validator could not tell a wrong record from a right one | Plausibility checks in `file`; independent second reading (`check`) for the pilot swings and one in five after; disputed records go to `needs_review` and are left out of counts |
| 2026-11-25 | The Profile was set to spot-check its own claims and score its own predictions | Predictions are data scored by `score`; the Profile reports check and golden-set agreement and grades nothing |
| 2026-11-25 | "Don't read the Model or other records" was only a sentence | One fresh agent per swing; read-deny rules from `install_walls.py`; the Model is kept out of the repo and archive |
| 2026-11-25 | Nothing tested whether a skill change made readings better | Golden set with a held-out split (`golden`); one change at a time |
| 2026-11-25 | Records did not say which analyzer produced them | Every record carries the git commit; the roll-up flags mixed versions |
| 2026-11-25 | "Two tries, then fail" depended on the agent remembering | Attempt counter in the ledger; three rejections mark the swing `failed` |
| 2026-11-25 | A video diagnosis prescribed a path fix before ball flight was known; the flight (push-slice) reversed the priority | Video skill: ball flight decides the fix; face before path; fixes are provisional without it |
| 2026-11-25 | Opus drew a reference line at one value and recorded a different value for the same landmark | Video skill: table landmarks must equal the reference lines; records store raw readings and the script computes |
| 2026-11-25 | A test run agreed with the author's read, but the skill's example command contained the author's numbers for that video | Example commands use placeholders only |
| 2026-11-25 | The grid was too coarse: the golfer filled three of ten units, so a key shift was barely above noise | Crop to the golfer, half-unit grid lines, horizontal lines; movement reported as a percentage of stance width or height |
| 2026-11-25 | A normal driver hip shift was at risk of being called a fault | Normal ranges stated; later, Cahlan's own baseline replaces generic thresholds |
