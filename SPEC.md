# swing-lab spec

The canonical design for the swing-learning loop. If something here disagrees with a skill or a script, this file is right and the other is a bug. Changes to this file go through a pull request and an entry in `HARNESS_LOG.md`.

## Purpose

Learn Cahlan's golf swing from video as well as video allows, keep learning as new swings arrive, and keep checking that what it has learned is true.

The lab is the evidence layer. It measures swings and reports patterns. It does not coach. Coaching belongs to Cahlan's Golf Coach project, which owns his Model of his swing. The lab's job is to tell that Model, with counts, where the video agrees with it and where it doesn't.

## Principles

1. **Blind first, diff second.** Swings are measured by agents that know nothing about the golfer, his Model, or any other swing. Comparison with the Model happens afterwards, somewhere else.
2. **Never self-grade.** The agent that produces a reading is never the one that judges it. Checks are done by a different agent with fresh context, by a script, or by Cahlan.
3. **Evidence must be able to say no.** A check that could not have come back red is decoration. Every gate in the loop is something a script computes or a second reader disputes.
4. **Facts over prose.** A rule that matters is enforced by a script, a permission or a file, not by a sentence in a prompt.
5. **State lives in files.** A fresh session resumes from the ledger and the records alone. Nothing depends on a conversation.
6. **Measure, then count, then interpret.** Models read positions. Scripts do arithmetic and counting. Interpretation comes last and cites counts.
7. **Unreadable is an answer.** A missing value is recorded as missing. Nothing is guessed to fill a field.
8. **Fix the harness, not the run.** When a result is wrong, the fix is a clearer definition, a new check or a wall, logged and tested, so the same failure cannot recur.
9. **The Model stays Cahlan's.** The lab proposes. He decides.

## Layers

| Layer | Where | Written by | Changed how |
| --- | --- | --- | --- |
| Videos | Drive archive, one subfolder per golfer | Cahlan | Added, never edited |
| Ledger | `_analysis/ledger.csv` | `swing_archive.py` | By script only |
| Swing records | `_analysis/records/` | Measuring agent, filed by script | Written once; never edited. A re-measure moves the old record to `_analysis/superseded/` |
| Checks | `_analysis/checks/` | Second measuring agent, compared by script | Written once |
| Roll-up | `_analysis/rollup_<golfer>.md` | Script | Regenerated |
| Golden set | `_analysis/golden.csv` | Cahlan | Labels added by him |
| Swing Profile | `_analysis/profile/` | Profile skill, in chat | New dated version each time; never patched |
| Model | Cahlan's Golf Coach project and Living Log | Cahlan | By him, through his own review protocol |

Authority, most to least: fresh evidence, then the Living Log, then the Model.

## Roles and what each may see

| Role | Runs in | Does | May not see |
| --- | --- | --- | --- |
| Orchestrator (`lab-batch`) | Claude Code, this repo | Hands out swings, files results, runs checks | Frames, records, checks, roll-ups, profiles, golden set |
| Measurer (`lab-measure`) | Fresh subagent per swing | Reads one swing's frames, writes one record | Anything about any other swing, the golfer or the Model |
| Checker (`lab-measure` again) | Another fresh subagent | Reads the same swing independently | The first record, or that it is a check |
| Scripts | Python | Validate, compute, count, compare, score | Not applicable |
| Synthesizer (`swing-profile`) | Chat, with Drive access | Writes the Profile, then diffs it against the Model | Nothing, but it grades nothing |
| Cahlan | | Labels the golden set, resolves `needs_review`, owns the Model | |

The walls are Claude Code read-deny rules written by `scripts/install_walls.py`, plus the fact that the Model is not stored anywhere in the repo or the archive.

## The two loops

### Loop 1: learn the swing

1. **Discover.** `scan` finds new videos and locates candidate strikes by sound. No model is involved.
2. **Hand out.** `next` returns swings in a fixed order that spans the date range early (first, last, middle, quarters), unfinished ones first.
3. **Measure.** A fresh agent reads landmark positions off gridded frames and answers a fixed list of observations.
4. **File.** The script checks the record is complete and physically plausible, computes comparable measurements, saves the record, then marks the ledger.
5. **Check.** The first three swings and about one in five after that are measured again by a second fresh agent. The script compares. Disagreement marks the swing `needs_review`.
6. **Roll up.** The script counts observations and summarizes measurements by view, club and period, leaving out `needs_review`.
7. **Synthesize.** In chat, the Profile is rebuilt from the roll-up: recurring patterns, Cahlan's own normal ranges, changes over time, and falsifiable predictions.
8. **Diff.** The Profile is compared with the Model. Each Model element gets a verdict with counts.
9. **Decide.** Cahlan decides what changes in the Model.

### Loop 2: improve the analyzer

1. **Golden set.** Swings with labels Cahlan trusts: his own calls and FlightScope-matched ball starts. Part is held out.
2. **One change at a time.** A change to a skill, a definition, a threshold or a script is made alone.
3. **Rerun.** `golden` scores the analyzer against the labels. Check agreement is the second score.
4. **Keep or revert.** The change is kept only if the tuning labels improve and the held-out labels do not get worse.
5. **Log.** `HARNESS_LOG.md` records the failure that prompted the change and what changed.

Records carry the git commit of the code that produced them. Records from different versions are compared with care, and the roll-up says when versions are mixed.

## Data contract

**Unit.** One swing: `<video name>__s<n>`. A video with several strikes yields several units.

**Ledger statuses.**

| Status | Meaning | Set by |
| --- | --- | --- |
| `extracted` | Found by `scan`, waiting | `scan`, `reset` |
| `in_progress` | Handed out once, not yet filed; listed by `resume` | `next` |
| `analyzed` | Record filed and counted | `file` |
| `needs_review` | Record filed but disputed or implausible; not counted | `file`, `check` |
| `skipped` | Not a usable swing | `mark` |
| `failed` | Could not be processed | `scan`, `file` after three rejections |

**Record.** Raw readings only: view, club, quality, crop, key-frame times, landmark positions on a 0 to 10 grid, and a yes / no / unreadable answer for every observation code, with evidence for each yes. The script adds the comparable measurements, the golfer, the analyzer version and timestamps. The exact fields are in `.claude/skills/lab-measure/SKILL.md`.

**Comparable measurements.** Sideways movement face-on is a percentage of stance width. Vertical movement, and all movement down the line, is a percentage of the golfer's height at address. These hold at any camera distance.

## Gates

| Gate | What it catches | Can it say no? |
| --- | --- | --- |
| Completeness check in `file` | Missing fields, unanswered observations, a yes with no evidence | Yes, by script |
| Plausibility check in `file` | Landmarks off the grid, frames out of order, a stance no human has, a strike time far from the sound | Yes, by script |
| Independent check | Readings a second agent does not reproduce | Yes, by comparison |
| Golden set | An analyzer that disagrees with trusted labels | Yes, by script |
| Prediction scoring | A Profile that does not predict later swings | Yes, by script |
| Chat-skill drift test | The chat copy of the frame script falling behind the repo | Yes, by test |

## Exits

- A record rejected three times marks the swing `failed`. The loop moves on.
- `next` hands out at most five swings at once, and each swing only once.
- A batch does the number of swings asked for, then stops and reports.
- The first run is a pilot of three swings and three checks. It stops for Cahlan.
- A check agreement rate below about 70% stops synthesis. No Profile is written from unrepeatable readings.

## Human gates

These never become automatic:

- Any change to the Model or the Living Log.
- Resolving a `needs_review` swing.
- Adding a label to the golden set.
- Accepting a change to this spec.

## What video cannot know

- The clubface and the swing path at impact. At 60 frames per second the club moves several feet between frames.
- Strike location on the face.
- The club's position coming into the ball, precisely. At 60 frames per second the clubhead travels up to a third of the golfer's height between frames, so the delivery reading is interpolated from two frames and still carries error. At 30 it is worse. Down-the-line swings filmed in slow motion remove most of it.
- What each miss costs. That needs ball flight.
- Anything about a swing that was not filmed. Cahlan may film mostly when something feels off, so the archive can overstate faults.

FlightScope shots matched to a video by timestamp supply measured ball start and curve for that swing. They are the best labels the golden set can have.

## Triggers

- New videos in the archive: run `lab-batch`.
- Ten new records since the last Profile: rebuild the Profile.
- Half or more of a Profile's scored predictions missed: the Profile is stale; rebuild it and look for what changed.
- Any change to a skill or script: rerun the golden set before keeping it.

Nothing runs on a timer more often than the archive changes.

## Unproven as of the first commit

- Nothing has run end to end in Claude Code on the real archive.
- Finding several strikes in one long video by sound is untested on real footage.
- The observation thresholds are estimates. Until the golden set tests them, measurements are trusted over observation codes.
- The plausibility ranges are estimates and may reject a real but unusual setup. `sanity_override` exists for that and routes the record to review.
- The golden set is empty.

## Sources for the design

- Cahlan's Golf Coaching Constitution: Fresh-Eyes protocol, authority order, conflict tally.
- Cahlan's loop principles: generator and evaluator separation, the five moves (discovery, handoff, verification, persistence, scheduling), hard caps, a permanent human checkpoint.
- Anthropic, "Effective harnesses for long-running agents" and "Harness design for long-running application development": progress in files, a separate evaluator.
- Anthropic, "Loop engineering: Getting started with loops": deterministic stop criteria, scripts for deterministic steps, pilots, fixing the system and not the single result.
- Anthropic, "Automating eval design and hillclimbing with Claude": one change at a time against an eval with a held-out set.
- Trackmind, "Harness Engineering": contract, map, tools, state, sensors, exits, walls, traces.
