# Chat skills

These two skills run in the Claude app, not in this repo's Claude Code session. The copies here are the source of truth; the copies saved to Cahlan's Claude account are updated from them through a skill proposal in chat.

- `golf-swing-video-analysis`: coach-style read of one swing video in chat. Its last section embeds `scripts/swing_frames.py`; `tests/test_chat_skill.py` fails if the two drift apart.
- `swing-profile`: builds the Swing Profile and the diff against the Model. It holds no Model content; the map from Model to evidence is written fresh each time, in chat.
