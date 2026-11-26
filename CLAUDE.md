# swing-lab

Measures golf swings from video, one record per swing, and checks its own readings. Read `SPEC.md` before changing how anything works.

## Map

| Need | Go to |
| --- | --- |
| Why it is built this way, roles, gates | `SPEC.md` |
| Run or resume the archive | `.claude/skills/lab-batch/SKILL.md` |
| Measure one swing (subagents only) | `.claude/skills/lab-measure/SKILL.md` |
| Ledger, records, checks, roll-up, golden set, predictions | `scripts/swing_archive.py` (`--help` text at the top) |
| Frame extraction and FlightScope time matching | `scripts/swing_frames.py` |
| What each past failure changed | `HARNESS_LOG.md` |
| Skills that run in the Claude app, not here | `skills-chat/README.md` |

## Rules for this repo

- Run `python3 -m unittest discover tests` before and after any change to `scripts/`.
- Change one thing at a time, rerun the golden set (`swing_archive.py golden`), and add an entry to `HARNESS_LOG.md`.
- `scripts/swing_frames.py` is embedded in `skills-chat/golf-swing-video-analysis/SKILL.md`. Change both together; a test fails otherwise.
- Never put Cahlan's Model, Constitution or Living Log in this repo or the archive. The measuring agents must not be able to read them.
- Videos, records and everything under the archive's `_analysis/` stay in Drive, not in git.
- Do not read the archive's records, checks, roll-ups, profiles or golden set from a session that measures swings. Permissions deny it.
