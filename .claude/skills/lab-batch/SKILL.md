---
name: lab-batch
description: Run the swing archive loop in Claude Code. Finds new swing videos, hands each swing to a fresh measuring agent, files the records, runs independent checks, and stops cleanly so the job can resume later. Use when Cahlan says to process, continue, resume or check the swing archive, or to add new swing videos to it.
---

# Swing archive batch

You are the orchestrator. You never look at a swing yourself. You hand each swing to a fresh agent, file what comes back, and let the script decide what counts as done. Read `SPEC.md` if you need the reasons.

## Rules

1. **You do not measure.** Do not open frame images, records, checks, roll-ups or profiles. You pass paths and file results.
2. **One fresh agent per swing.** Each swing is measured by a new subagent that follows the `lab-measure` skill and is told nothing about any other swing.
3. **The script decides.** A swing is done when `file` accepts its record. Caps on retries and hand-outs are in the script; do not work around them.
4. **Stop when the batch is done.** Do the number of swings asked for (3 if no number is given), run the checks that are due, report, and stop.

## Setup, once per machine

1. `pip install -r requirements.txt`, and make sure `ffmpeg` and `ffprobe` are on PATH.
2. `python3 -m unittest discover tests` must pass.
3. Find the archive: Cahlan's Drive folder (id `1KX771eyyQtHGlbCssvt1lt9--TOmOqO2`) synced by Google Drive for desktop, on a Mac usually under `~/Library/CloudStorage/GoogleDrive-*/My Drive/`. Ask for the path if it isn't given. Each golfer has a subfolder.
4. Install the walls, then restart the session so they load:

```bash
python3 scripts/install_walls.py "ARCHIVE"
```

After that the archive path is in `.claude/archive_path.txt`.

## The loop

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" scan
python3 scripts/swing_archive.py --root "ARCHIVE" resume
python3 scripts/swing_archive.py --root "ARCHIVE" next -n 3
```

`resume` lists swings handed out in an earlier session and never finished. Do those first; they count toward the batch. `next` then hands out new swings. Both print one line per swing: unit id, video path, recording time, strike time, frame rate.

`next` hands each swing out exactly once. Call it once per batch for the number you still need, and call it again only to replace a swing that was skipped. Never call `next` while you are waiting on agents you already started.

Agents may run in parallel, one per swing.

For each line:

1. **Measure.** Spawn a new subagent with exactly this and nothing more: "Follow the lab-measure skill. VIDEO=`<path>` IMPACT=`<seconds>` UNIT=`<unit>` SCRATCH=`scratch/<unit>`."
2. **If it returns a skip:**

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" mark UNIT --status skipped --note "<reason>"
```

3. **If it returns a record, file it:**

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" file UNIT scratch/UNIT/record.json --evidence scratch/UNIT/keys.jpg
```

`file` prints one line and no readings. Do not pass `--show`; the readings are not for you.

4. **If `file` prints `RECORD REJECTED`,** send the rejection text back to the same subagent and file again. The script marks the swing `failed` after three rejections; when it says so, move on.

## Independent checks

After the batch, ask what is due:

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" checklist
```

The first three swings ever analyzed and about one in five after that are listed. For each one, spawn another new subagent with the same message as before, but `SCRATCH=scratch/<unit>_check`. Do not tell it this is a check and do not give it the first record. Then:

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" check UNIT scratch/UNIT_check/record.json
```

`AGREE` leaves the record in place. `DISAGREE` marks it `needs_review`, which removes it from every count until someone resolves it. On a disagreement the script names the measurements that differ and says whether the two readers chose different key frames or read the same frames differently. Copy those lines into your report as they are.

## Finish

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" rollup --golfer Cahlan --pivot 2026-07-08
python3 scripts/swing_archive.py --root "ARCHIVE" status
```

If `ARCHIVE/_analysis/profile/predictions_latest.json` exists, score it into a file without printing it, so the predictions stay out of your context:

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" score "ARCHIVE/_analysis/profile/predictions_latest.json" --golfer Cahlan \
  > "ARCHIVE/_analysis/profile/score_latest.txt"
```

Report, in a few lines:

- Analyzed, skipped, failed and needs-review this run, and how many are left.
- Each check result: agree or disagree, and on what.
- Anything odd about the videos (several swings in one file, slow motion, wrong golfer).
- Roughly how long each swing took.

Do not read or interpret the roll-up. Do not propose a diagnosis.

## First run: pilot

On the first run, do 3 swings, run the 3 checks, report and stop. Wait for Cahlan before continuing. If two or more of the three checks disagree, the measuring instructions are not repeatable enough; say so plainly.

## Re-measuring after a harness change

When Cahlan asks for swings to be measured again, for example after the measuring instructions change:

```bash
python3 scripts/swing_archive.py --root "ARCHIVE" reset UNIT --note "<why>"
```

The old record and check move to `_analysis/superseded/` and the swing is handed out again by `next`. Then run the loop and the checks as usual. Reset only the swings he names.

## When something keeps going wrong

Do not patch the record. Note what happened in your report so the fix can go into the harness: a clearer landmark definition in `lab-measure`, a new sanity check in the script, or a wall. Every such change is logged in `HARNESS_LOG.md` and rerun against the golden set (`swing_archive.py golden`) before it is kept.
