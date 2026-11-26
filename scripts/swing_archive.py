#!/usr/bin/env python3
"""Resumable ledger, swing records, checks and roll-up for a folder of swing videos.

  swing_archive.py --root DIR scan                 find new videos and their strikes (no model needed)
  swing_archive.py --root DIR status               counts by status
  swing_archive.py --root DIR next [-n 3]          hand out the next swings, spread across the date range
  swing_archive.py --root DIR resume               swings handed out earlier and never finished
  swing_archive.py --root DIR reset UNIT --note "why"   set a swing aside to be measured again
  swing_archive.py --root DIR mark UNIT --status skipped --note "practice swing"
  swing_archive.py --root DIR file UNIT record.json [--evidence keys.jpg] [--show]
  swing_archive.py --root DIR checklist            analyzed swings that still need an independent check
  swing_archive.py --root DIR check UNIT second.json   compare an independent second reading
  swing_archive.py --root DIR rollup [--golfer NAME] [--pivot YYYY-MM-DD] [--tz America/Denver]
  swing_archive.py --root DIR rederive             recompute measurements and script-decided codes from stored readings
  swing_archive.py --root DIR golden               score records against trusted labels in golden.csv
  swing_archive.py --root DIR score predictions.json   score a Profile's predictions

Everything it writes goes in DIR/_analysis. See SPEC.md.
"""
import argparse, csv, json, os, shutil, statistics, subprocess, sys, zlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swing_frames as sf

VIDEO_EXT = (".mov", ".mp4", ".m4v")
COLS = ["unit_id", "file", "recorded_utc", "fps", "duration_s", "width", "height", "impact_s", "strike_level",
        "status", "view", "club", "attempts", "checked", "harness", "note", "updated_utc"]
STATUSES = ("extracted", "in_progress", "analyzed", "needs_review", "skipped", "failed")
VIEWS = ("face-on", "dtl", "angled")
CLUBS = ("driver", "wood", "hybrid", "iron", "wedge", "unknown")
ANSWERS = ("yes", "no", "unreadable")
CAMERA_LINES = ("on_line", "inside", "outside", "unknown")   # down the line: where the camera stood
FRAMES = {"face-on": ["address", "top", "impact", "finish"],
          "dtl": ["address", "takeaway", "top", "halfway", "delivery", "impact", "finish"]}
CODES = {
    "face-on": ["hip_slide", "hang_back_finish", "sway_back", "reverse_pivot", "early_release",
                "trail_heel_up_before_impact", "ball_too_far_back", "ball_too_far_forward",
                "weak_grip", "strong_grip"],
    "dtl": ["over_the_top", "stuck_inside", "early_extension", "inside_takeaway", "steep_at_halfway",
            "open_face_at_top", "closed_face_at_top", "weight_on_heels_at_address",
            "aimed_right", "aimed_left", "ball_starts_right", "ball_starts_left"],
}
# Codes a model answers by looking. Every other code is decided by the script from the measurements (see CUTS),
# so its cutoff can change later without anyone re-reading a video.
JUDGED = {
    "face-on": ["early_release", "trail_heel_up_before_impact", "ball_too_far_back", "ball_too_far_forward",
                "weak_grip", "strong_grip"],
    "dtl": ["steep_at_halfway", "open_face_at_top", "closed_face_at_top", "weight_on_heels_at_address",
            "aimed_right", "aimed_left", "ball_starts_right", "ball_starts_left"],
}
CUTS = {   # cutoffs for script-decided codes, in the measurements' own units. All are estimates until the golden set tests them.
    "hip_slide_pelvis": 20.0, "hip_slide_past_foot": 0.0, "hang_back_finish": 33.0, "sway_back": -10.0, "reverse_pivot": 5.0,
    "over_the_top": -5.0, "stuck_inside": 20.0, "stuck_hands_out": 3.0, "early_extension_hips": 4.0,
    "early_extension_hands": 5.0, "inside_takeaway": 15.0,
}
MAX_ATTEMPTS = 3      # rejected records per swing before it is marked failed
MAX_HANDOUT = 5       # swings handed out at once
CHECK_EVERY = 5       # one swing in this many gets an independent second reading
PILOT = 3             # the first swings analyzed are always checked
TOLERANCE = 6.0       # points two readings of one measurement may differ
LEVEL_LIMIT = {"takeaway": 8.0, "delivery": 8.0}     # how far off level a frame may be, % of height (estimates)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def harness_version():
    """Git commit of this code, so every record says which analyzer produced it."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        rev = subprocess.run(["git", "-C", here, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", here, "status", "--porcelain", "--", "."], capture_output=True, text=True).stdout.strip()
        return (rev + ("+dirty" if dirty else "")) if rev else "unversioned"
    except OSError:
        return "unversioned"


class Archive:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.dir = os.path.join(self.root, "_analysis")
        self.ledger = os.path.join(self.dir, "ledger.csv")
        for d in ("records", "evidence", "checks", "profile"):
            os.makedirs(os.path.join(self.dir, d), exist_ok=True)
        self.rows = list(csv.DictReader(open(self.ledger, newline=""))) if os.path.exists(self.ledger) else []
        for r in self.rows:
            for c in COLS:
                r.setdefault(c, "")

    def save(self):
        tmp = self.ledger + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, COLS, extrasaction="ignore"); w.writeheader(); w.writerows(self.rows)
        os.replace(tmp, self.ledger)          # atomic: a crash never leaves half a ledger

    def row(self, unit):
        for r in self.rows:
            if r["unit_id"] == unit:
                return r
        sys.exit("no such unit in the ledger: %s" % unit)

    def record_path(self, unit):
        return os.path.join(self.dir, "records", unit + ".json")

    def records(self, golfer=""):
        out = []
        for r in self.rows:
            if r["status"] == "analyzed" and os.path.exists(self.record_path(r["unit_id"])):
                rec = json.load(open(self.record_path(r["unit_id"])))
                if not golfer or rec.get("golfer", "").lower() == golfer.lower():
                    out.append(rec)
        return out

    def videos(self):
        out = []
        for base, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d != "_analysis" and not d.startswith(".")]
            out += [os.path.relpath(os.path.join(base, f), self.root)
                    for f in files if f.lower().endswith(VIDEO_EXT) and not f.startswith(".")]
        return sorted(out)


# ---------------------------------------------------------------- scan / status / next / mark

def cmd_scan(A, a):
    known = {r["file"] for r in A.rows}
    todo = [v for v in A.videos() if v not in known]
    print("%d videos, %d already in the ledger, %d new" % (len(known) + len(todo), len(known), len(todo)))
    for rel in todo:
        path = os.path.join(A.root, rel); stem = os.path.splitext(os.path.basename(rel))[0]
        blank = dict.fromkeys(COLS, "")
        try:
            info = sf.probe(path)
            w, h = sf.grab(path, 0).size                       # displayed size, rotation applied
            peaks = sf.audio_peaks(path, k=12, gap=4) if info["audio"] else []
            top = peaks[0][1] if peaks else 0
            strikes = sorted(p for p in peaks if p[1] >= 0.5 * top) or [("", "")]
            start = sf.utc(info["recorded"])
            for i, (t, level) in enumerate(strikes, 1):
                A.rows.append(blank | {
                    "unit_id": "%s__s%d" % (stem, i), "file": rel,
                    "recorded_utc": start.strftime("%Y-%m-%d %H:%M:%S") if start else "",
                    "fps": "%.0f" % info["fps"], "duration_s": "%.1f" % info["duration"],
                    "width": w, "height": h, "impact_s": t, "strike_level": level,
                    "status": "extracted", "attempts": "0", "updated_utc": now()})
            print("  %s: %d candidate strike(s)" % (rel, len(strikes)))
        except SystemExit as e:
            A.rows.append(blank | {"unit_id": stem + "__s1", "file": rel, "status": "failed",
                                   "note": str(e)[:200], "updated_utc": now()})
            print("  %s: FAILED" % rel)
        A.save()                                               # after every video, so a stop loses nothing
    cmd_status(A, a)


def cmd_status(A, a):
    counts = {}
    for r in A.rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("ledger: %d units | %s" % (len(A.rows), ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "empty"))


def spread_order(rows):
    """Order that covers the whole date range early: first, last, middle, quarters, ..."""
    rows = sorted(rows, key=lambda r: (r["recorded_utc"], r["unit_id"]))
    n = len(rows); bits = max(1, (n - 1).bit_length())
    return [rows[i] for i in sorted(range(n), key=lambda i: int(format(i, "0%db" % bits)[::-1], 2))]


def cmd_next(A, a):
    order = spread_order(A.rows)                               # fixed order, whatever has been done so far
    todo = [r for r in order if r["status"] == "extracted"][:min(a.n, MAX_HANDOUT)]
    for r in todo:                                             # a swing is handed out once; see `resume`
        r.update(status="in_progress", updated_utc=now())
        print(handout_line(A, r))
    A.save()
    if not todo:
        waiting = sum(r["status"] == "in_progress" for r in A.rows)
        print("nothing new to hand out" + (" (%d still in progress; see `resume`)" % waiting if waiting else ""))


def handout_line(A, r):
    return "%s | %s | recorded %s | impact %ss | %s fps" % (
        r["unit_id"], os.path.join(A.root, r["file"]), r["recorded_utc"] or "?", r["impact_s"] or "?", r["fps"])


def cmd_resume(A, a):
    """Swings handed out in an earlier session that were never filed, skipped or failed."""
    todo = [r for r in spread_order(A.rows) if r["status"] == "in_progress"]
    for r in todo:
        print(handout_line(A, r))
    if not todo:
        print("nothing in progress")


def cmd_reset(A, a):
    """Set a swing aside to be measured again. The old record and check are kept, never edited or deleted."""
    r = A.row(a.unit)
    if not a.note:
        sys.exit("reset needs --note saying why")
    stamp = now().replace(" ", "T").replace(":", "")
    kept = os.path.join(A.dir, "superseded"); os.makedirs(kept, exist_ok=True)
    for sub in ("records", "checks"):
        src = os.path.join(A.dir, sub, a.unit + ".json")
        if os.path.exists(src):
            shutil.move(src, os.path.join(kept, "%s_%s_%s.json" % (a.unit, sub, stamp)))
    r.update(status="extracted", attempts="0", checked="due", note=("reset: " + a.note)[:200], updated_utc=now())
    A.save()
    print("reset %s: it will be handed out again; the old record is in _analysis/superseded/" % a.unit)


def cmd_mark(A, a):
    r = A.row(a.unit)
    if a.status and a.status not in STATUSES:
        sys.exit("status must be one of %s" % (STATUSES,))
    for k in ("status", "view", "club", "note"):
        if getattr(a, k):
            r[k] = getattr(a, k)
    r["updated_utc"] = now(); A.save()
    if r["status"] in ("skipped", "failed"):                   # nothing more will be read from this swing's scratch
        for name in (a.unit, a.unit + "_check"):
            shutil.rmtree(os.path.join(os.getcwd(), "scratch", name), ignore_errors=True)
    print("marked %s: status=%s note=%s" % (a.unit, r["status"], r["note"]))


# ---------------------------------------------------------------- records

def derive(rec, row):
    """Turn raw grid readings into numbers that compare across videos. Returns {name: value or None}."""
    fr, crop = rec["frames"], rec["crop"]
    px_x = float(row["width"]) / 10 * (crop[1] - crop[0]) / 10       # source pixels per cropped grid unit
    px_y = float(row["height"]) / 10 * (crop[3] - crop[2]) / 10

    def at(frame, mark, axis):
        v = (fr.get(frame) or {}).get(mark)
        return None if v is None else float(v[axis])

    def move(mark, frame, axis, scale, sign=1.0, origin=("address", None)):
        a0 = at(origin[0], origin[1] or mark, axis); a1 = at(frame, mark, axis)
        if a0 is None or a1 is None or not scale:
            return None
        return round(sign * (a1 - a0) * (px_x if axis == 0 else px_y) / scale * 100, 1)

    top, ground = at("address", "cap_top", 1), at("address", "ground", 1)
    height = (ground - top) * px_y if None not in (top, ground) else None
    out = {}
    if rec["view"] == "face-on":
        lead, trail = at("address", "lead_foot_outer", 0), at("address", "trail_foot_outer", 0)
        if None in (lead, trail):
            return out
        stance, toward = abs(lead - trail) * px_x, (1.0 if lead > trail else -1.0)   # + = toward the target
        out["stance_pct_height"] = round(stance / height * 100, 1) if height else None
        out["head_shift_top_pct_stance"] = move("head", "top", 0, stance, toward)
        out["head_shift_impact_pct_stance"] = move("head", "impact", 0, stance, toward)
        out["pelvis_shift_top_pct_stance"] = move("pelvis_center", "top", 0, stance, toward)
        out["pelvis_shift_impact_pct_stance"] = move("pelvis_center", "impact", 0, stance, toward)
        out["lead_hip_past_lead_foot_impact_pct_stance"] = move(
            "lead_hip_outer", "impact", 0, stance, toward, ("address", "lead_foot_outer"))
        out["head_short_of_lead_foot_finish_pct_stance"] = move(
            "head", "finish", 0, stance, -toward, ("address", "lead_foot_outer"))
        out["ball_position_pct_stance"] = move("ball", "address", 0, stance, toward, ("address", "trail_foot_outer"))
        out["head_drop_impact_pct_height"] = move("head", "impact", 1, height)
    elif rec["view"] == "dtl":
        ball, hips = at("address", "ball", 0), at("address", "hips_back", 0)
        if None in (ball, hips) or not height:
            return out
        toward = 1.0 if ball > hips else -1.0                                        # + = toward the ball
        out["hips_toward_ball_impact_pct_height"] = move("hips_back", "impact", 0, height, toward)
        out["head_toward_ball_impact_pct_height"] = move("head", "impact", 0, height, toward)
        out["head_drop_impact_pct_height"] = move("head", "impact", 1, height)
        out["hands_out_impact_pct_height"] = move("hands", "impact", 0, height, toward)
        out["hands_higher_impact_pct_height"] = move("hands", "impact", 1, height, -1.0)
        for f in ("takeaway", "delivery"):                                           # + = clubhead inside the hands
            inside = move("clubhead", f, 0, height, -toward, (f, "hands"))
            off = move("clubhead", f, 1, height, 1.0, (f, "hands"))                  # 0 = clubhead level with the hands
            o = f + "_other"                                                         # adjacent frame, other side of level
            inside2 = move("clubhead", o, 0, height, -toward, (o, "hands"))
            off2 = move("clubhead", o, 1, height, 1.0, (o, "hands"))
            if None not in (inside, off, inside2, off2) and off * off2 < 0:          # the two frames bracket level:
                w = abs(off) / (abs(off) + abs(off2))                                # read off the instant it was level
                inside, off = round(inside + w * (inside2 - inside), 1), 0.0
            out["clubhead_inside_hands_%s_pct_height" % f] = inside
            out["%s_level_error_pct_height" % f] = None if off is None else abs(off)
    return out


def validate(rec):
    """Is the record complete? Returns a list of problems."""
    errs = []
    if rec.get("view") not in VIEWS: errs.append("view must be one of %s" % (VIEWS,))
    if rec.get("club") not in CLUBS: errs.append("club must be one of %s" % (CLUBS,))
    if not rec.get("model"): errs.append("model is missing (which model read the frames)")
    if not (isinstance(rec.get("crop"), list) and len(rec["crop"]) == 4): errs.append("crop must be [X0,X1,Y0,Y1]")
    if not rec.get("summary"): errs.append("summary is missing")
    view = rec.get("view")
    if view == "dtl" and rec.get("camera_line") not in CAMERA_LINES:
        errs.append("camera_line must be one of %s for a down-the-line swing" % (CAMERA_LINES,))
    if view in FRAMES:
        for f in FRAMES[view]:
            if f not in rec.get("frames", {}): errs.append("frames is missing '%s'" % f)
            elif (rec["frames"][f] or {}).get("t") is None: errs.append("frames.%s has no time 't'" % f)
        got = {o.get("code"): o for o in rec.get("observations", [])}
        for c in JUDGED[view]:
            o = got.get(c)
            if not o: errs.append("observations is missing '%s'" % c)
            elif o.get("present") not in ANSWERS: errs.append("%s.present must be one of %s" % (c, ANSWERS))
            elif o["present"] == "yes" and not o.get("evidence"): errs.append("%s is 'yes' but has no evidence" % c)
    return errs


def sanity(rec, row, derived):
    """Could these readings be a real golfer? Checks that can say no. Returns a list of problems."""
    bad, fr, view = [], rec.get("frames", {}), rec["view"]
    if view not in FRAMES:
        return bad
    for f, marks in fr.items():
        for m, v in (marks or {}).items():
            if m != "t" and v is not None and not (isinstance(v, list) and len(v) == 2 and all(0 <= float(c) <= 10 for c in v)):
                bad.append("%s.%s = %s is not an [x, y] inside the 0-10 grid" % (f, m, v))
    if bad:
        return bad
    times = [fr[f]["t"] for f in FRAMES[view]]
    if times != sorted(times):
        bad.append("key-frame times are out of order: %s" % dict(zip(FRAMES[view], times)))
    if row["impact_s"] and abs(float(fr["impact"]["t"]) - float(row["impact_s"])) > 0.25 and not rec.get("impact_corrected"):
        bad.append("impact frame t=%s is far from the ledger strike at %ss (set impact_corrected with the reason if the ledger was wrong)"
                   % (fr["impact"]["t"], row["impact_s"]))
    A0 = fr["address"]
    def y(m): return None if A0.get(m) is None else float(A0[m][1])
    if None not in (y("cap_top"), y("head"), y("ground")) and not (y("cap_top") <= y("head") < y("ground")):
        bad.append("address: expected cap_top above head above ground, got y = %s, %s, %s" % (y("cap_top"), y("head"), y("ground")))
    if view == "face-on":
        s = derived.get("stance_pct_height")
        if s is not None and not 12 <= s <= 70:
            bad.append("stance width is %s%% of height; a real stance is roughly 20-50%%" % s)
        feet = [A0.get("trail_foot_outer"), A0.get("lead_foot_outer")]
        if None not in feet and A0.get("pelvis_center") is not None:
            lo, hi = sorted(float(f[0]) for f in feet)
            if not lo <= float(A0["pelvis_center"][0]) <= hi:
                bad.append("address: pelvis_center is not between the feet")
    else:
        if None not in (A0.get("hips_back"), A0.get("head"), A0.get("ball")):
            hb, hd, bl = (float(A0[m][0]) for m in ("hips_back", "head", "ball"))
            if not (hb < hd < bl or hb > hd > bl):
                bad.append("address: expected hips_back, then head, then ball across the frame")
    for f, limit in LEVEL_LIMIT.items():                       # these frames are defined by the clubhead being level
        off = derived.get("%s_level_error_pct_height" % f)
        if off is not None and off > limit:
            bad.append("%s frame is not where the clubhead is level with the hands (off by %s%% of height, limit %s%%). "
                       "Pick the frame where their heights are closest and give the adjacent frame on the other side of "
                       "level as %s_other so the script can interpolate. If the clubhead cannot be read there, record "
                       "the %s clubhead as null" % (f, off, limit, f, f))
    for k, v in derived.items():
        if v is not None and k != "stance_pct_height" and k != "ball_position_pct_stance" and abs(v) > 70:
            bad.append("%s = %s is outside anything a swing produces" % (k, v))
    return bad


def clear_scratch(unit, record_path):
    """Remove a reader's scratch folder once its record is safely stored, so a later reader cannot find it."""
    folder = os.path.dirname(os.path.abspath(record_path))
    parts = folder.replace("\\", "/").split("/")
    if os.path.basename(folder) in (unit, unit + "_check") and "scratch" in parts[:-1]:
        shutil.rmtree(folder, ignore_errors=True)
    elif os.path.exists(record_path):
        os.remove(record_path)


def derive_codes(view, d):
    """Codes the script decides from measurements. Returns {code: yes / no / unreadable}."""
    def any_of(*tests):                                        # yes if any holds; unreadable only if nothing was measured
        seen = [t for t in tests if t is not None]
        return "unreadable" if not seen else ("yes" if any(seen) else "no")

    def all_of(*tests):                                        # needs every measurement
        return "unreadable" if any(t is None for t in tests) else ("yes" if all(tests) else "no")

    def over(name, cut): return None if d.get(name) is None else d[name] > CUTS[cut]
    def under(name, cut): return None if d.get(name) is None else d[name] < CUTS[cut]

    if view == "face-on":
        return {"hip_slide": any_of(over("pelvis_shift_impact_pct_stance", "hip_slide_pelvis"),
                                    over("lead_hip_past_lead_foot_impact_pct_stance", "hip_slide_past_foot")),
                "hang_back_finish": any_of(over("head_short_of_lead_foot_finish_pct_stance", "hang_back_finish")),
                "sway_back": any_of(under("head_shift_top_pct_stance", "sway_back")),
                "reverse_pivot": any_of(over("head_shift_top_pct_stance", "reverse_pivot"))}
    if view == "dtl":
        return {"over_the_top": any_of(under("clubhead_inside_hands_delivery_pct_height", "over_the_top")),
                "stuck_inside": all_of(over("clubhead_inside_hands_delivery_pct_height", "stuck_inside"),
                                       over("hands_out_impact_pct_height", "stuck_hands_out")),
                "early_extension": any_of(over("hips_toward_ball_impact_pct_height", "early_extension_hips"),
                                          over("hands_higher_impact_pct_height", "early_extension_hands")),
                "inside_takeaway": any_of(over("clubhead_inside_hands_takeaway_pct_height", "inside_takeaway"))}
    return {}


def prepare(A, unit, path):
    row = A.row(unit); rec = json.load(open(path))
    errs = validate(rec)
    derived = derive(rec, row) if not errs and rec["view"] in FRAMES else {}
    doubts = [] if errs else sanity(rec, row, derived)
    return row, rec, errs, derived, doubts


def cmd_file(A, a):
    row, rec, errs, derived, doubts = prepare(A, a.unit, a.record)
    if doubts and not rec.get("sanity_override"):
        errs += doubts + ["if the readings are right and the swing really is unusual, add \"sanity_override\": \"<why>\"; "
                          "the record is then filed as needs_review"]
    if errs:
        row["attempts"] = str(int(row["attempts"] or 0) + 1)
        if int(row["attempts"]) >= MAX_ATTEMPTS:
            row.update(status="failed", note="record rejected %d times: %s" % (MAX_ATTEMPTS, errs[0][:120]))
        row["updated_utc"] = now(); A.save()
        sys.exit("RECORD REJECTED (attempt %s of %d)%s:\n  %s" % (
            row["attempts"], MAX_ATTEMPTS, "; unit marked failed, move on" if row["status"] == "failed" else "", "\n  ".join(errs)))
    f = row["file"].replace("\\", "/")
    rec.update(unit_id=a.unit, file=row["file"], recorded_utc=row["recorded_utc"], fps=row["fps"],
               golfer=f.split("/")[0] if "/" in f else "", derived=derived,
               derived_codes=derive_codes(view_of(rec), derived), harness=harness_version(), filed_utc=now())
    if row["recorded_utc"] and rec.get("impact_s") is not None:
        rec["impact_utc"] = (sf.utc(row["recorded_utc"]) + timedelta(seconds=float(rec["impact_s"]))).strftime("%Y-%m-%d %H:%M:%S")
    if a.evidence:
        dest = os.path.join(A.dir, "evidence", a.unit + "_keys.jpg")
        shutil.copyfile(a.evidence, dest); rec["evidence"] = os.path.relpath(dest, A.dir)
    out = A.record_path(a.unit)
    with open(out + ".tmp", "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(out + ".tmp", out)                              # record first ...
    status = "needs_review" if doubts else "analyzed"
    row.update(status=status, view=rec["view"], club=rec["club"], harness=rec["harness"], updated_utc=now(),
               note=("sanity override: " + rec["sanity_override"])[:200] if doubts else row["note"])
    A.save()                                                   # ... ledger last
    clear_scratch(a.unit, a.record)
    print("filed %s as %s" % (a.unit, status))                 # quiet: the orchestrator stays blind to readings
    if a.show:
        for k, v in derived.items():
            print("  %-46s %s" % (k, "unreadable" if v is None else v))


def view_of(rec):
    return rec.get("view")


def due_for_check(A):
    done = sorted((r for r in A.rows if r["status"] == "analyzed"), key=lambda r: r["updated_utc"])
    pilot = {r["unit_id"] for r in done[:PILOT]}
    return [r for r in done if r["checked"] in ("", "due") and                 # "due": re-measured after a reset
            (r["checked"] == "due" or r["unit_id"] in pilot or zlib.crc32(r["unit_id"].encode()) % CHECK_EVERY == 0)]


def cmd_checklist(A, a):
    due = due_for_check(A)
    for r in due:
        print("%s | %s | impact %ss | %s fps" % (r["unit_id"], os.path.join(A.root, r["file"]), r["impact_s"] or "?", r["fps"]))
    if not due:
        print("no independent checks are due")


def cmd_check(A, a):
    row, second, errs, derived, doubts = prepare(A, a.unit, a.record)
    if errs:
        sys.exit("SECOND READING REJECTED:\n  " + "\n  ".join(errs))
    first = json.load(open(A.record_path(a.unit)))
    diffs, flips = {}, []
    for k, v in derived.items():
        w = first.get("derived", {}).get(k)
        if None not in (v, w) and abs(v - w) > TOLERANCE:
            diffs[k] = [w, v]
    judged = JUDGED.get(second["view"], [])
    was = {o["code"]: o["present"] for o in first.get("observations", [])}
    soft = []                                                  # reported, not counted
    for o in second.get("observations", []):
        if o["code"] not in judged:
            continue
        if {was.get(o["code"]), o["present"]} == {"yes", "no"}:
            flips.append(o["code"])
        elif was.get(o["code"]) != o["present"]:
            soft.append(o["code"])                             # one reader could not tell
    then = first.get("derived_codes") or derive_codes(first["view"], first.get("derived", {}))
    for code, ans in derive_codes(second["view"], derived).items():
        if then.get(code) != ans:
            soft.append(code)                                  # follows a measurement; the measurement is what is compared
    for field in ("club", "quality", "camera_line"):
        if first.get(field) != second.get(field):
            soft.append(field)
    if first["view"] != second["view"]:
        flips.append("view")
    frame = 1.0 / float(row["fps"] or 30)
    times = {}                                                 # key frames the two readers put more than a frame apart
    for f, marks in (first.get("frames") or {}).items():
        t1, t2 = (marks or {}).get("t"), ((second.get("frames") or {}).get(f) or {}).get("t")
        if None not in (t1, t2) and abs(float(t1) - float(t2)) > 1.5 * frame:
            times[f] = [t1, t2, round(abs(float(t1) - float(t2)) / frame)]
    agree = not diffs and len(flips) < 2
    json.dump({"unit_id": a.unit, "checked_utc": now(), "agree": agree, "measurement_diffs": diffs, "flipped": flips,
               "frame_time_diffs": times, "soft_changes": soft,
               "first_model": first.get("model"), "second_model": second.get("model"), "second": second, "second_derived": derived},
              open(os.path.join(A.dir, "checks", a.unit + ".json"), "w"), indent=1)
    row.update(checked="agree" if agree else "disagree", updated_utc=now())
    if not agree:
        row.update(status="needs_review", note=("independent check disagreed: %s" % ", ".join(list(diffs) + flips))[:200])
    A.save()
    print("%s: %s" % (a.unit, "AGREE" if agree else "DISAGREE -> needs_review"))
    if diffs:                                                  # names only; the readings stay in the check file
        print("  measurements that differ: %s" % ", ".join(diffs))
    if flips:
        print("  answers that flipped between yes and no: %s" % ", ".join(flips))
    if soft:
        print("  also differ (not counted): %s" % ", ".join(soft))
    for f, (t1, t2, n) in times.items():
        print("  key frame '%s' chosen %d frames apart (%ss vs %ss)" % (f, n, t1, t2))
    if diffs and not times:
        print("  the readers chose the same frames, so they read the landmarks differently")
    clear_scratch(a.unit, a.record)


# ---------------------------------------------------------------- roll-up, golden set, predictions

def local_date(rec, tz):
    """The calendar day the swing was filmed where the golfer lives. File timestamps are UTC."""
    t = sf.utc(rec.get("recorded_utc"))
    return t.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d") if t else ""


def cmd_rollup(A, a):
    recs = A.records(a.golfer)
    for r in recs:
        r["day"] = local_date(r, a.tz)
    L = ["# Swing roll-up%s" % (": " + a.golfer if a.golfer else ""), "",
         "Generated %s UTC from %d swing records. Counts only; no interpretation." % (now(), len(recs)), ""]
    st = {}
    for r in A.rows:
        st[r["status"]] = st.get(r["status"], 0) + 1
    L += ["Ledger: " + ", ".join("%s %d" % kv for kv in sorted(st.items())),
          "Records marked needs_review are left out of every count below.", ""]
    checked = [r["checked"] for r in A.rows if r["checked"]]
    L += ["Independent checks: %d agree, %d disagree." % (checked.count("agree"), checked.count("disagree")), ""]
    versions = sorted({r.get("harness", "?") for r in recs})
    L += ["Analyzer versions: %s%s" % (", ".join(versions) or "none",
                                       "  **Mixed versions: compare across them with care.**" if len(versions) > 1 else ""), ""]

    def groups(rs):
        g = [("all", rs), ("driver", [r for r in rs if r["club"] == "driver"]),
             ("not driver", [r for r in rs if r["club"] != "driver"])]
        if a.pivot:
            g += [("before " + a.pivot, [r for r in rs if r["day"] and r["day"] < a.pivot]),
                  ("from " + a.pivot, [r for r in rs if r["day"] and r["day"] >= a.pivot])]
        if rs and rs[0]["view"] == "dtl":                      # an off-line camera distorts inside/outside readings
            g += [("camera on line", [r for r in rs if r.get("camera_line") == "on_line"]),
                  ("camera off line", [r for r in rs if r.get("camera_line") in ("inside", "outside")]),
                  ("50+ fps", [r for r in rs if float(r.get("fps") or 0) >= 50]),      # the club's position coming
                  ("under 50 fps", [r for r in rs if float(r.get("fps") or 0) < 50])]   # down is far less exact here
        return [x for x in g if x[1]]

    for view in FRAMES:
        rs = [r for r in recs if r["view"] == view]
        if not rs:
            continue
        L += ["## %s (%d swings)" % (view, len(rs)), "", "### Observations: yes / no / unreadable", "",
              "Codes in *italics* are decided by the script from the measurements below; the rest are a reader's call.", "",
              "| code | " + " | ".join(n for n, _ in groups(rs)) + " |", "|---|" + "---|" * len(groups(rs))]
        for c in CODES[view]:
            cells = []
            for _, g in groups(rs):
                ans = [lookup(r, c) or "unreadable" for r in g]
                cells.append("%d / %d / %d" % tuple(ans.count(x) for x in ANSWERS))
            L.append("| %s | %s |" % (c if c in JUDGED[view] else "*%s*" % c, " | ".join(cells)))
        L += ["", "### Measurements: median (25th to 75th percentile), n", "",
              "| measurement | " + " | ".join(n for n, _ in groups(rs)) + " |", "|---|" + "---|" * len(groups(rs))]
        for m in sorted({k for r in rs for k in r.get("derived", {})}):
            cells = []
            for _, g in groups(rs):
                v = sorted(r["derived"][m] for r in g if r.get("derived", {}).get(m) is not None)
                if not v: cells.append("n=0")
                elif len(v) < 4: cells.append("%s, n=%d" % (" ".join("%g" % x for x in v), len(v)))
                else:
                    q = statistics.quantiles(v, n=4)
                    cells.append("%g (%g to %g), n=%d" % (round(statistics.median(v), 1), round(q[0], 1), round(q[2], 1), len(v)))
            L.append("| %s | %s |" % (m, " | ".join(cells)))
        L.append("")
    L += ["## Every swing", "", "| recorded | unit | view | club | quality | checked | summary |", "|---|---|---|---|---|---|---|"]
    chk = {r["unit_id"]: r["checked"] for r in A.rows}
    for r in sorted(recs, key=lambda r: r["recorded_utc"]):
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (r["day"], r["unit_id"], r["view"], r["club"],
                                                         r.get("quality", ""), chk.get(r["unit_id"], ""), r["summary"].replace("|", "/")))
    out = os.path.join(A.dir, "rollup%s.md" % ("_" + a.golfer if a.golfer else ""))
    open(out, "w").write("\n".join(L) + "\n")
    print("wrote %s (%d records)" % (out, len(recs)))


def lookup(rec, field):
    """A record's value for a golden or prediction field: view, club, an observation code, or a measurement."""
    if field in ("view", "club", "camera_line", "quality"):
        return rec.get(field)
    if field in rec.get("derived_codes", {}):
        return rec["derived_codes"][field]
    if field in JUDGED.get(rec.get("view"), []):
        for o in rec.get("observations", []):
            if o["code"] == field:
                return o["present"]
    return rec.get("derived", {}).get(field)


def cmd_rederive(A, a):
    """Recompute measurements and script-decided codes for every record from its stored readings.
    The readings themselves are never touched. Use after changing a formula or a cutoff."""
    n = 0
    for row in A.rows:
        path = A.record_path(row["unit_id"])
        if not os.path.exists(path):
            continue
        rec = json.load(open(path))
        if rec.get("view") not in FRAMES:
            continue
        rec["derived"] = derive(rec, row); rec["derived_codes"] = derive_codes(rec["view"], rec["derived"])
        rec["rederived"] = {"utc": now(), "harness": harness_version()}
        with open(path + ".tmp", "w") as fh:
            json.dump(rec, fh, indent=1)
        os.replace(path + ".tmp", path); n += 1
    print("rederived %d records with harness %s" % (n, harness_version()))


def cmd_golden(A, a):
    """golden.csv columns: unit_id, field, expected, tolerance, split (tune or holdout), source."""
    path = os.path.join(A.dir, "golden.csv")
    if not os.path.exists(path):
        sys.exit("no golden set yet: create %s" % path)
    tally, lines = {}, []
    for g in csv.DictReader(open(path, newline="")):
        split = g.get("split") or "tune"
        if not os.path.exists(A.record_path(g["unit_id"])):
            verdict, got = "no record", ""
        else:
            got = lookup(json.load(open(A.record_path(g["unit_id"]))), g["field"])
            if got is None or got == "unreadable":
                verdict = "unreadable"
            elif isinstance(got, (int, float)):
                verdict = "agree" if abs(got - float(g["expected"])) <= float(g.get("tolerance") or TOLERANCE) else "DISAGREE"
            else:
                verdict = "agree" if str(got) == g["expected"] else "DISAGREE"
        tally.setdefault(split, {}).setdefault(verdict, 0); tally[split][verdict] += 1
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (g["unit_id"], g["field"], g["expected"], got, verdict, split, g.get("source", "")))
    L = ["# Golden set report", "", "Generated %s UTC. Analyzer version %s." % (now(), harness_version()), ""]
    for split, t in sorted(tally.items()):
        scored = t.get("agree", 0) + t.get("DISAGREE", 0)
        L.append("- **%s:** %d of %d scored labels agree (%s). Not scored: %d unreadable, %d with no record." % (
            split, t.get("agree", 0), scored, "%.0f%%" % (100 * t.get("agree", 0) / scored) if scored else "n/a",
            t.get("unreadable", 0), t.get("no record", 0)))
    L += ["", "| unit | field | expected | got | verdict | split | source |", "|---|---|---|---|---|---|---|"] + lines
    open(os.path.join(A.dir, "golden_report.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:4 + len(tally)]))


def cmd_score(A, a):
    """Predictions file: {"after": "YYYY-MM-DD HH:MM:SS", "min_n": 5, "predictions": [
         {"id": "p1", "view": "dtl", "club": "driver", "field": "stuck_inside", "op": ">=", "value": 0.7},
         {"id": "p2", "view": "face-on", "field": "pelvis_shift_impact_pct_stance", "op": "<=", "value": 20}]}
    For an observation code, value is the share of readable swings answering yes. For a measurement, it is the median."""
    spec = json.load(open(a.predictions)); min_n = int(spec.get("min_n", 5))
    recs = [r for r in A.records(a.golfer) if r.get("filed_utc", "") > spec["after"]]
    print("scoring against %d records filed after %s" % (len(recs), spec["after"]))
    for p in spec["predictions"]:
        rs = [r for r in recs if r["view"] == p["view"] and (not p.get("club") or r["club"] == p["club"])]
        vals = [v for v in (lookup(r, p["field"]) for r in rs) if v is not None and v != "unreadable"]
        if len(vals) < min_n:
            print("  %-6s NOT ENOUGH SWINGS (%d of %d needed)" % (p["id"], len(vals), min_n)); continue
        got = (sum(v == "yes" for v in vals) / len(vals)) if isinstance(vals[0], str) else statistics.median(vals)
        hit = got >= p["value"] if p["op"] == ">=" else got <= p["value"]
        print("  %-6s %s   %s %s %s, got %.2f over %d swings" % (p["id"], "HIT " if hit else "MISS", p["field"], p["op"], p["value"], got, len(vals)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "status", "checklist", "golden", "resume", "rederive"):
        sub.add_parser(name)
    p = sub.add_parser("next"); p.add_argument("-n", type=int, default=3)
    p = sub.add_parser("mark"); p.add_argument("unit")
    for k in ("status", "view", "club", "note"): p.add_argument("--" + k, default="")
    p = sub.add_parser("file"); p.add_argument("unit"); p.add_argument("record"); p.add_argument("--evidence", default="")
    p.add_argument("--show", action="store_true", help="also print the computed measurements")
    p = sub.add_parser("reset"); p.add_argument("unit"); p.add_argument("--note", default="")
    p = sub.add_parser("check"); p.add_argument("unit"); p.add_argument("record")
    p = sub.add_parser("rollup"); p.add_argument("--pivot", default=""); p.add_argument("--golfer", default="")
    p.add_argument("--tz", default="America/Denver", help="time zone the swings were filmed in; dates are local")
    p = sub.add_parser("score"); p.add_argument("predictions"); p.add_argument("--golfer", default="")
    a = ap.parse_args(); A = Archive(a.root)
    {"scan": cmd_scan, "status": cmd_status, "next": cmd_next, "resume": cmd_resume, "reset": cmd_reset,
     "mark": cmd_mark, "file": cmd_file, "rederive": cmd_rederive,
     "checklist": cmd_checklist, "check": cmd_check, "rollup": cmd_rollup, "golden": cmd_golden, "score": cmd_score}[a.cmd](A, a)


if __name__ == "__main__":
    main()
