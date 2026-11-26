# swing-lab

Learns a golf swing from video: one blind measurement record per swing, independent checks on those records, and a roll-up that feeds a dated Swing Profile. The design is in [SPEC.md](SPEC.md).

## Quick start

```bash
pip install -r requirements.txt          # Pillow; also needs ffmpeg and ffprobe on PATH
python3 -m unittest discover tests       # 12 tests on a synthetic video
python3 scripts/install_walls.py "/path/to/swing archive"
```

Then open the repo in Claude Code and run `/lab-batch`. The first run is a pilot: three swings, three independent checks, then it stops.

## What is where

- `scripts/swing_frames.py`: turns a video into gridded frame sheets; finds the strike by sound; matches a swing to a FlightScope shot by time.
- `scripts/swing_archive.py`: resumable ledger, record validation, comparable measurements, independent checks, roll-up, golden set, prediction scoring.
- `.claude/skills/`: `lab-batch` (orchestrator) and `lab-measure` (one fresh agent per swing).
- `skills-chat/`: skills that run in the Claude app.
- `HARNESS_LOG.md`: what each failure changed.

Videos and swing records live in the Drive archive under `_analysis/`, not in this repo.
