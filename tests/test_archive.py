"""End-to-end tests for scripts/swing_archive.py on a synthetic video. Run: python3 -m unittest discover tests"""
import copy, csv, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "swing_archive.py")

FACE_ON = {
    "schema": 1, "view": "face-on", "club": "driver", "quality": "good", "model": "test", "impact_s": 1.5,
    "crop": [1.5, 8, 1.8, 9], "camera_moved": False,
    "frames": {
        "address": {"t": 0.5, "head": [4.3, 1.8], "cap_top": [4.3, 1.2], "ground": [5, 7.4],
                    "lead_foot_outer": [7.0, 7.3], "trail_foot_outer": [2.85, 7.3], "pelvis_center": [5.1, 4.4],
                    "lead_hip_outer": [6.5, 4.4], "ball": [6.4, 9.0], "hands": [5.9, 4.4]},
        "top": {"t": 1.2, "head": [4.3, 1.8], "pelvis_center": [4.9, 4.4]},
        "impact": {"t": 1.5, "head": [4.2, 2.4], "pelvis_center": [5.6, 4.5], "lead_hip_outer": [7.0, 4.5]},
        "finish": {"t": 2.4, "head": [4.6, 1.8]}},
    "observations": [{"code": c, "present": "no", "confidence": "high", "evidence": ""} for c in (
        "hip_slide", "sway_back", "reverse_pivot", "early_release", "trail_heel_up_before_impact",
        "ball_too_far_back", "ball_too_far_forward", "weak_grip", "strong_grip")] + [
        {"code": "hang_back_finish", "present": "yes", "confidence": "medium", "evidence": "finish t=2.4: head 4.6, lead foot 7.0"}],
    "summary": "Stable head, modest hip shift, hangs back at the finish."}


def make_video(path):
    """3 s of test pattern with one loud click at 1.5 s and a recording timestamp."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=30:duration=3",
                    "-f", "lavfi", "-i", "aevalsrc='if(between(t,1.5,1.52),0.9*sin(2*PI*1000*t),0)':d=3",
                    "-metadata", "creation_time=2026-06-04T18:59:22Z", "-pix_fmt", "yuv420p", "-shortest", path], check=True)


class ArchiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = os.path.join(tempfile.mkdtemp(), "clip.mov"); make_video(cls.src)

    def setUp(self):
        self.root = tempfile.mkdtemp(); os.makedirs(os.path.join(self.root, "Cahlan"))
        for name in ("A.mov", "B.mov", "C.mov"):
            shutil.copy(self.src, os.path.join(self.root, "Cahlan", name))
        self.run_ok("scan")

    def run_cmd(self, *args):
        return subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True, text=True)

    def run_ok(self, *args):
        r = self.run_cmd(*args); self.assertEqual(r.returncode, 0, r.stdout + r.stderr); return r.stdout

    def read(self, *parts):
        with open(os.path.join(self.root, "_analysis", *parts)) as f:
            return f.read()

    def ledger(self):
        return {r["unit_id"]: r for r in csv.DictReader(self.read("ledger.csv").splitlines())}

    def record(self, **changes):
        rec = copy.deepcopy(FACE_ON)
        for path, value in changes.items():
            node = rec; keys = path.split("__")
            for k in keys[:-1]: node = node[k]
            node[keys[-1]] = value
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(rec, f); f.close(); return f.name

    def test_scan_finds_the_strike_and_is_idempotent(self):
        row = self.ledger()["A__s1"]
        self.assertAlmostEqual(float(row["impact_s"]), 1.5, delta=0.06)
        self.assertEqual((row["width"], row["height"], row["status"]), ("320", "568", "extracted"))
        self.assertEqual(row["recorded_utc"], "2026-06-04 18:59:22")
        self.run_ok("scan"); self.assertEqual(len(self.ledger()), 3)

    def test_next_hands_out_and_resumes_the_same_units(self):
        first = self.run_ok("next", "-n", "2"); again = self.run_ok("next", "-n", "2")
        self.assertEqual(first, again)
        self.assertEqual(sum(r["status"] == "in_progress" for r in self.ledger().values()), 2)

    def test_file_computes_comparable_measurements(self):
        out = self.run_ok("file", "A__s1", self.record())
        rec = json.loads(self.read("records", "A__s1.json"))
        self.assertEqual(rec["derived"]["pelvis_shift_impact_pct_stance"], 12.0)
        self.assertEqual(rec["derived"]["head_drop_impact_pct_height"], 9.7)
        self.assertEqual(rec["golfer"], "Cahlan"); self.assertTrue(rec["harness"]); self.assertIn("analyzed", out)
        self.assertEqual(rec["impact_utc"], "2026-06-04 18:59:23")

    def test_incomplete_record_is_rejected_and_capped(self):
        bad = self.record(club="big stick")
        for attempt in (1, 2, 3):
            r = self.run_cmd("file", "A__s1", bad); self.assertNotEqual(r.returncode, 0)
            self.assertIn("RECORD REJECTED (attempt %d of 3)" % attempt, r.stderr)
        self.assertEqual(self.ledger()["A__s1"]["status"], "failed")

    def test_impossible_readings_are_rejected_unless_overridden(self):
        bad = self.record(frames__address__trail_foot_outer=[6.8, 7.3])
        r = self.run_cmd("file", "A__s1", bad); self.assertIn("stance width", r.stderr)
        self.run_ok("file", "A__s1", self.record(frames__address__trail_foot_outer=[6.8, 7.3], sanity_override="filmed from far away"))
        self.assertEqual(self.ledger()["A__s1"]["status"], "needs_review")

    def test_out_of_order_frames_are_rejected(self):
        r = self.run_cmd("file", "A__s1", self.record(frames__top__t=2.0)); self.assertIn("out of order", r.stderr)

    def test_independent_check_agrees_or_flags(self):
        self.run_ok("file", "A__s1", self.record()); self.run_ok("file", "B__s1", self.record())
        self.assertIn("AGREE", self.run_ok("check", "A__s1", self.record(frames__impact__pelvis_center=[5.7, 4.5])))
        self.assertIn("DISAGREE", self.run_ok("check", "B__s1", self.record(frames__impact__pelvis_center=[6.6, 4.5])))
        led = self.ledger()
        self.assertEqual((led["A__s1"]["checked"], led["A__s1"]["status"]), ("agree", "analyzed"))
        self.assertEqual((led["B__s1"]["checked"], led["B__s1"]["status"]), ("disagree", "needs_review"))

    def test_pilot_swings_are_due_for_a_check(self):
        self.run_ok("file", "A__s1", self.record())
        self.assertIn("A__s1", self.run_ok("checklist"))
        self.run_ok("check", "A__s1", self.record()); self.assertIn("no independent checks", self.run_ok("checklist"))

    def test_rollup_leaves_out_needs_review(self):
        self.run_ok("file", "A__s1", self.record()); self.run_ok("file", "B__s1", self.record())
        self.run_ok("check", "B__s1", self.record(frames__impact__pelvis_center=[6.6, 4.5]))
        self.run_ok("rollup", "--golfer", "Cahlan", "--pivot", "2026-07-08")
        text = self.read("rollup_Cahlan.md")
        self.assertIn("face-on (1 swings)", text); self.assertIn("| hang_back_finish | 1 / 0 / 0 |", text)
        self.assertIn("before 2026-07-08", text); self.assertIn("0 agree, 1 disagree", text)

    def test_golden_set_scores_labels(self):
        self.run_ok("file", "A__s1", self.record())
        with open(os.path.join(self.root, "_analysis", "golden.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["unit_id", "field", "expected", "tolerance", "split", "source"])
            w.writerows([["A__s1", "view", "face-on", "", "tune", "Cahlan"], ["A__s1", "hang_back_finish", "no", "", "tune", "Cahlan"],
                         ["A__s1", "pelvis_shift_impact_pct_stance", "14", "5", "holdout", "FlightScope"]])
        out = self.run_ok("golden")
        self.assertIn("**tune:** 1 of 2", out); self.assertIn("**holdout:** 1 of 1", out)

    def test_predictions_are_scored_by_the_script(self):
        for u in ("A__s1", "B__s1", "C__s1"):
            self.run_ok("file", u, self.record())
        spec = {"after": "2000-01-01 00:00:00", "min_n": 3, "predictions": [
            {"id": "p1", "view": "face-on", "field": "hang_back_finish", "op": ">=", "value": 0.7},
            {"id": "p2", "view": "face-on", "field": "pelvis_shift_impact_pct_stance", "op": ">=", "value": 20},
            {"id": "p3", "view": "dtl", "field": "stuck_inside", "op": ">=", "value": 0.5}]}
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(spec, f); f.close()
        out = self.run_ok("score", f.name)
        self.assertRegex(out, r"p1\s+HIT"); self.assertRegex(out, r"p2\s+MISS"); self.assertRegex(out, r"p3\s+NOT ENOUGH")


if __name__ == "__main__":
    unittest.main()
