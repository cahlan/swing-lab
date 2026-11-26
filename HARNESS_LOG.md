# Harness log

Each entry is a failure that actually happened and the part of the harness it changed. Newest first. Entries dated 2026-11-25 come from the design session before the first commit.

| Date | What went wrong | What changed |
| --- | --- | --- |
| 2026-11-26 | Re-run of 10: every check agreed, but readers chose the finish frame up to 23 frames apart. Face-on, the head's position at the finish is measured there | Finish is the frame 1.0 s after impact, or the last frame if the clip ends sooner; the script rejects any other |
| 2026-11-26 | Re-run of 10: `camera_line` differed in six of ten checks, so the roll-up's on-line and off-line split cannot be trusted | Added a measured stand-in from existing landmarks, `ball_beyond_hands_address_pct_height`. Experimental: it also varies with club and posture. `camera_line` stays in the record but should not carry conclusions |
| 2026-11-26 | First batch of 10: four of six checks agreed. Yes/no answers were the weak part: `early_extension` flipped in three of six, and one swing disagreed on answers alone with every measurement agreeing | Codes that follow from positions are now decided by the script from the measurements (`CUTS`); readers answer only what needs eyes. `rederive` recomputes records after a cutoff changes. Checks count flips only on reader-judged codes |
| 2026-11-26 | Takeaway disagreed again on a 30 fps video, with frames chosen two apart | Takeaway also records the adjacent frame across level (`takeaway_other`) and is interpolated; its off-level limit drops from 12% to 8% |
| 2026-11-26 | Two swings filmed the evening of July 7 local time were dated July 8 (UTC) and fell on the wrong side of the roll-up's date split | The roll-up dates swings by local day (`--tz`, default America/Denver) |
| 2026-11-26 | Nine of the first twelve videos are 30 fps, where delivery is poorly resolved | The roll-up splits down-the-line swings into 50+ fps and under 50 fps |
| 2026-11-26 | Swings re-measured after a reset were not checked again | A reset swing is always due for a check |
| 2026-11-26 | Skipped swings left their scratch folders behind | `mark` clears scratch for skipped and failed swings |
| 2026-11-25 | Re-run: the first reader's scratch folder, with its record, was still on disk when the checker started. The orchestrator moved old folders by hand | `file` and `check` delete the reader's scratch folder once the record is stored |
| 2026-11-25 | Re-run: readers said the camera was off the target line and might exaggerate an outside club, but only in free text | Required `camera_line` field for down-the-line swings; the roll-up splits camera on line from off line |
| 2026-11-25 | Re-run: subagents described their readings to the orchestrator, which put them in its report | `lab-measure` returns a path or a skip and nothing else; `lab-batch` reports only script output |
| 2026-11-25 | Pilot: readers split on "good" versus "usable" and on when to note a corrected strike time | Quality is a count of listed problems; `impact_corrected` only beyond 0.25 s |
| 2026-11-25 | Re-run: a check said AGREE without showing answers that moved to or from unreadable, or a changed club | `check` lists them as "also differ (not counted)" |
| 2026-11-25 | Pilot: two readers disagreed on clubhead-versus-hands at takeaway, and on which side of the hands the clubhead was. "Shaft parallel" was picked by eye from frames a tenth of a second apart | `lab-measure` step 3: takeaway and delivery are the frames where the clubhead is closest to level with the hands, chosen from five candidates one frame apart. The script computes how far off level each chosen frame is and rejects a miss. The limits (12% and 8% of height) are estimates. Regression: re-measure and re-check the three pilot swings |
| 2026-11-25 | Trying that rule on a real 60 fps swing showed clubhead-inside-hands at delivery reading 43%, 23% and -3% of height on three consecutive frames. The nearest frame alone leaves about 10 points of sampling error | The measurer also records `delivery_other`, the adjacent frame across level, and the script interpolates to the level moment. Slow-motion video is the real fix for down-the-line swings |
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
