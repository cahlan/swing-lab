"""The chat copy of the video skill embeds the frame script. It must match scripts/swing_frames.py exactly."""
import os, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


class ChatSkillDrift(unittest.TestCase):
    def test_embedded_script_matches_the_repo_script(self):
        with open(os.path.join(ROOT, "skills-chat", "golf-swing-video-analysis", "SKILL.md")) as f:
            text = f.read()
        embedded = text.split("```python\n", 1)[1].split("\n```", 1)[0] + "\n"
        with open(os.path.join(ROOT, "scripts", "swing_frames.py")) as f:
            self.assertEqual(embedded, f.read(), "skills-chat copy has drifted from scripts/swing_frames.py")


if __name__ == "__main__":
    unittest.main()
