---
name: swing-profile
description: Build or update Cahlan's Swing Profile from the swing archive's roll-up, then diff it against his golf Model. Use when he asks to roll up the swing analyses, what his common swing faults are, to update the profile, to compare the video evidence with his Model or coaching instructions, or after a batch of new swings is filed.
---

# Swing Profile

Turn the swing records into a dated, evidence-only picture of Cahlan's swing, then compare that picture with his own Model. This is his Fresh-Eyes protocol applied to video: blind diagnosis first, diff second. The design is in `SPEC.md` in the `cahlan/swing-lab` repo.

This skill runs in chat, never in the repo's Claude Code session. The agents that measure swings must not see what it writes.

## Three layers, never mixed

1. **Swing records** (`_analysis/records/`). One per swing, written by the lab. Never edit them.
2. **Swing Profile** (`_analysis/profile/`). What this skill writes. Each version is re-derived from all records and saved as a new dated file. Never patch an old version.
3. **Cahlan's Model.** His. It lives in his Golf Coach project instructions, with the Living Log in Notion (page `371a3f47-8469-812f-b0a6-f8325c148753`). This skill proposes changes to it and never makes them.

Authority follows his Constitution: fresh evidence beats the Living Log, which beats the Model.

## Inputs

The archive is Drive folder `1KX771eyyQtHGlbCssvt1lt9--TOmOqO2`. Read with the Drive connector.

- `_analysis/rollup_Cahlan.md`: counts and measurement ranges. Start here. Records marked `needs_review` are already left out.
- `_analysis/ledger.csv`: what has been analyzed, checked, skipped, failed or flagged.
- `_analysis/golden_report.md`: how the analyzer scores against labels Cahlan trusts.
- `_analysis/profile/score_latest.txt`: the script's scoring of the previous predictions.
- `_analysis/records/<unit>.json` and `_analysis/evidence/<unit>_keys.jpg`: open these to look at a specific swing.
- `_analysis/profile/`: earlier Profile versions.

If the roll-up is older than the newest record, it has to be regenerated in Claude Code first (the `lab-batch` skill does it). Chat cannot run it. Say so and stop.

## Step 0: is the evidence good enough to read?

Before any synthesis, report three numbers from the roll-up and the golden report:

- **Check agreement.** Independent checks that agreed versus disagreed. Below about 70% agreement, the readings are not repeatable: say so, write no Profile, and recommend fixing the measuring instructions first.
- **Golden-set agreement,** on the held-out labels if there are any.
- **Analyzer versions.** If records come from more than one version, compare across them with care and say so.

Do not grade the records yourself. The lab's independent checks and the golden set are the graders.

## Step 1: blind synthesis

Do this before reading the Model, the Constitution or the Living Log. If they are already in the conversation, do not use them in this step.

- **Coverage.** Count swings by view, club and period. Any group with fewer than 5 swings is "too few to call": list what it shows, classify nothing.
- **Recurring patterns.** For each observation code, in groups of 5 or more readable swings: yes in at least half is **recurring**, a quarter to a half is **intermittent**, less is **rare**. Unreadable swings are left out of the denominator and reported beside it.
- **Baseline.** For each measurement with 8 or more values, his normal range is the 25th to 75th percentile. This replaces generic thresholds for judging his future swings.
- **Change over time.** Compare periods (the roll-up's pivot date, or halves of the year). Call a change only when both sides have at least 4 swings and the medians differ by more than 6 points, the tolerance the independent check uses.
- **Mind the camera.** An off-line camera shifts every inside/outside reading. The roll-up's "camera on line" and "camera off line" columns come from a reader's call that two readers disagreed on in six of ten checks, so do not rest a claim on that split. Use `ball_beyond_hands_address_pct_height` among swings with the same club as a rough measured guide to where the camera stood, and say plainly that camera position is an uncontrolled source of error in every claim about the club's position.
- **Mind the frame rate.** The roll-up also splits down-the-line swings into 50+ and under 50 frames per second. Below 50, the club's position coming into the ball is poorly resolved; say what the faster swings show and treat the slower ones as weak evidence.
- **Lean on measurements.** Codes in italics in the roll-up are decided by the script from measurements, using cutoffs that are estimates. Report the measurement's median and range beside any such code, and where the two tell different stories, trust the measurement.
- **Rank by frequency.** Video cannot rank by cost, because it has no ball flight. Say that.

## Step 2: predictions

Read `score_latest.txt` for the previous version's predictions: hit, miss or not enough swings. If half or more of the scored ones missed, the earlier Profile was stale; say so plainly.

Then write 3 to 5 new predictions about the next 10 swings as data, and save them to `_analysis/profile/predictions_latest.json` (and a dated copy). The script scores them; this skill does not.

```json
{"after": "2026-12-01 00:00:00", "min_n": 5, "predictions": [
  {"id": "p1", "view": "dtl", "club": "driver", "field": "stuck_inside", "op": ">=", "value": 0.7},
  {"id": "p2", "view": "face-on", "field": "pelvis_shift_impact_pct_stance", "op": "<=", "value": 20}
]}
```

`after` is the time this Profile was written, in UTC. For an observation code, `value` is the share of readable swings answering yes. For a measurement, it is the median.

## Step 3: write the Profile

Save as `_analysis/profile/profile_vN_YYYY-MM-DD.md` (next N). Sections, in order:

1. Evidence quality: check agreement, golden-set agreement, analyzer versions.
2. Coverage table, with the groups that are too few to call.
3. Recurring and intermittent patterns, each with its count (for example "6 of 9 readable").
4. Baseline ranges.
5. Changes over time.
6. What video cannot tell: clubface, path, strike location, cost of each miss.
7. Scorecard of the previous version's predictions, from the script.
8. New predictions, in words.
9. Sample bias: he may film mostly when something feels off, so the archive can overstate faults.

## Step 4: diff against the Model

Now read the current Model. If its text is not in the conversation, ask Cahlan for it. The Model is never stored in the repo or the archive, and no mapping to it is kept in this skill, because the Model changes.

1. **Write the map first, before looking at any count.** For each Model element, list which observation codes and which measurements would support it and which would contradict it. An element with nothing on either list is untestable from video. Show Cahlan the map.
2. **Then fill in the counts** from the roll-up and give each element one verdict: **supported**, **contradicted**, **mixed**, **untestable from video**, or **too few swings** (fewer than 5 relevant).

Also report:

- **Open questions in the Model.** Where the Model asks something that dates can answer, such as whether a fix installed on a known date went too far, compare the periods on either side of that date.
- **Missing from the Model.** Recurring patterns the Model doesn't mention.
- **Claims that need ball flight.** Anything about start line, curve or two-way misses can't be tested from video alone. Say so unless FlightScope-matched swings exist.

## Step 5: report to Cahlan

Short and direct. He wants ground truth and can smell false praise.

- Evidence quality in one line.
- The top three recurring patterns, with counts.
- The verdict table.
- Proposed conflict-tally increments, one per contradicted element. Under his Constitution, an element contradicted three times triggers a Model review; say when a tally would reach three. Do not edit the Living Log or the Model unless he says to.
- What to film next to fill the thinnest group, for example "5 down-the-line iron swings".
- Any swings sitting in `needs_review`, since he is the one who resolves them.

## How it learns

- **Re-derive, don't patch.** Rebuild the Profile every 10 new records or when asked.
- **Predictions keep it honest.** They are scored by the script against swings filed later. A Profile that keeps missing is stale, whatever it says.
- **The golden set grades the analyzer.** Labels Cahlan trusts, including FlightScope-matched ball starts, go in `_analysis/golden.csv` (columns: `unit_id, field, expected, tolerance, split, source`; `split` is `tune` or `holdout`). Help him add labels when he gives a verdict on a swing. Never copy a label from the record it is meant to grade.
- **New swings.** Videos added to the Drive folder are picked up by the lab's `scan`. A video analyzed only in chat is not filed and does not count.
