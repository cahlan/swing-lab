---
name: "golf-swing-video-analysis"
description: "Freeze-frame and analyze a golf swing video (face-on/caddy view or down-the-line) to diagnose a miss, pairing it with the matching FlightScope shot when one exists. Use when Cahlan shares a swing video (.mov/.mp4) of himself or his son and asks why shots go right/left, what's wrong, or to look at a swing."
---

# Golf swing video analysis

Turn a phone swing video into labeled, gridded still frames, measure positions against the grid, and return a short diagnosis with external cues and an objective way to confirm it.

Three rules govern everything below:

1. **Look before you answer.** Never diagnose from the question, the file name, or what a miss "usually" means. Run the script and read the images first.
2. **Measure before you claim.** Every observation in the answer must come from a grid reading on a named frame. If a frame doesn't show it clearly, say it can't be read from this video.
3. **Ball flight decides the fix.** Video shows body and club positions; it cannot show the clubface at impact. Do not prescribe a fix until the ball flight is known (start direction and curve). A matched FlightScope shot (section 5a) supplies it. Without either, give the read, label any fix provisional, and ask.

## 1. Set up the script

Save the script in the last section of this file as `swing_frames.py` (any scratch directory). It needs `ffmpeg`/`ffprobe` on PATH and Pillow (`pip install pillow`).

Every image the script writes carries a grid: x runs 0 (left) to 10 (right) in yellow, y runs 0 (top) to 10 (bottom) in cyan, with faint half-unit lines. Read positions to the nearest 0.1.

## 2. Pass 1: find the swing

```bash
python3 swing_frames.py VIDEO --out swing_out
```

It prints the frame rate, the loudest sounds in the clip, and its impact estimate (the loudest sound, which is normally the strike). Read `overview.jpg` (24 frames across the whole clip, full frame) and `impact.jpg`, then settle:

- **Impact time.** On `impact.jpg` the club should reach the ball within a frame or two of the estimate. If it doesn't (wind, talking, no audio, a practice swing), find the strike on `overview.jpg` and pass `--impact T`.
- **Several swings in one clip.** Each strike is a separate audio peak. Run once per swing with its own `--impact` and `--out`.
- **View.** Face-on (caddy view: camera facing the chest, target to one side) or down-the-line (camera behind the golfer, looking toward the target). If it is in between, say so; angled views distort both checklists.
- **Handedness.** The tables below are for a right-hander. Mirror every left/right for a left-hander.
- **Club**, and whether the clip is high-speed (the script says so above 100 fps). For slow motion widen the window, for example `--pre 8 --post 3`.
- **Crop box.** From the overview grid, read a box around the golfer: X0,X1,Y0,Y1. Face-on: feet to cap with about one unit of margin each side. Down-the-line: include the ball and the clubhead at the top of the backswing.

## 3. Pass 2: zoom in

```bash
python3 swing_frames.py VIDEO --out swing_out --impact T --crop X0,X1,Y0,Y1
```

`swing.jpg` (24 frames of the swing) and `impact.jpg` (15 consecutive frames) are now cropped, with a fresh 0 to 10 grid on the crop. `after.jpg` (8 full-frame frames from impact) shows the ball leaving. Read all three and pick key times off the labels:

- **Face-on:** address (last still frame before takeaway), top, impact, finish.
- **Down-the-line:** address, takeaway (shaft parallel to the ground going back), top, halfway (lead arm parallel to the ground coming down), delivery (shaft parallel to the ground coming down), impact, finish.

## 4. Pass 3: key stills with reference lines

On the cropped address frame, read the landmarks for this view, then rerun with them as red lines. `--lines` are vertical (x values), `--hlines` horizontal (y values), both on the cropped grid.

```bash
python3 swing_frames.py VIDEO --out swing_out --impact T --crop X0,X1,Y0,Y1 \
  --keys address=T,top=T,impact=T,finish=T --lines X,X,X --hlines Y
```

This writes `key_<name>.jpg` for each key time and `keys.jpg`, a side-by-side strip. Lines to set from the address frame:

- **Face-on:** `--lines` head center, lead hip outer edge, lead foot outer edge. `--hlines` head center.
- **Down-the-line:** `--lines` back of the hips (tush line), hands. `--hlines` head center, hands.

**Camera check.** The feet should sit at the same grid position in address, top and impact. If they don't, the camera moved or zoomed: measure each landmark relative to the feet in its own frame, and say so.

## 5. Grip and clubface check

The face causes most of a ball's start direction, so check what the video can show about it. Run the script once more into a separate folder with a tight crop on the hands, and keys at address and top:

```bash
python3 swing_frames.py VIDEO --out hands_out --impact T --crop X0,X1,Y0,Y1 --keys address=T,top=T
```

- **Grip at address (face-on):** how many lead-hand knuckles are visible (two to three is neutral, fewer is weak, more is strong), and whether the trail hand sits on top of the grip or under it.
- **Lead wrist at the top (down-the-line):** cupped, flat or bowed.
- **Clubface at takeaway (down-the-line):** with the shaft parallel to the ground, toe up is neutral, face tilted to the sky is open, face tilted to the ground is closed.

Sleeves, gloves, distance and blur often hide these. If the grip can't be read, say so and ask for a close-up photo of the grip from the front. Do not guess.

## 5a. Match the swing to a FlightScope shot

Do this whenever the swing may have been filmed during a FlightScope session. A matched shot replaces asking Cahlan for ball flight.

1. **Impact clock time.** Every run prints `recording started ... UTC; impact at ... UTC`, taken from the video's own timestamp plus the impact time.
2. **Find the session.** Drive folder `FlightScope/sessions` (folder id `1e2Ie5p3LxKtil5TLvp3bc4gNsT8rCsDH`), files named `YYYY-MM-DD_PocketAppLesson_<id>.{md,csv,json}`. Search with the Drive connector (`parentId = '<folder id>'`) for the impact date, and the day either side, since shot times are UTC and an evening session in Utah lands on the next UTC day.
3. **Get the shot times to disk.** Read the session's `.md` with the Drive connector and save its text as `session.md`; its table has `ShotDateTime` for every shot. The decoded `.csv` from the flightscope-analysis skill works too.
4. **Match.**

```bash
python3 swing_frames.py VIDEO --out swing_out --impact T --shots session.md
```

The script lists the three nearest shots with the gap in seconds and prints `MATCH`, `AMBIGUOUS` or `NO MATCH` (15 second limit). Shots are usually 30 seconds or more apart.

- **Clock offset.** FlightScope's time and the phone's can differ by a few seconds, and that offset is not yet measured. When several videos from one session all show the same gap (within 3 seconds), that gap is the offset: rerun with `--clock-offset SECONDS`. State the offset you used in the answer so Cahlan can confirm it.
- **Lost timestamp.** If the recording date is the day the file was sent, not the day of the session, the video was trimmed or re-saved. Ask for the original, or for the time it was shot and pass `--recorded-at "YYYY-MM-DD HH:MM:SS"` in UTC.
- **Never pair on `NO MATCH` or `AMBIGUOUS`**, and never pair by shot order alone. Say there was no match and carry on from video only.

5. **Use the matched shot.** Run the flightscope-analysis skill on that session and take the matched shot's row: start direction, spin axis, curve, offline, carry, smash and attack angle. That is the ball flight for section 8. These exports usually carry ball data only (`session_clubDataAvailable: 0`), so club path and face are still inferred from start direction and curve. Say which numbers are measured and which are inferred.
6. **Many swings.** When a session has several videos, analyze the three worst-offline matched shots and one good one for contrast, not every swing.

## 6. Measure

Build a table of readings for every key frame before interpreting anything. The landmarks in the table must be the same ones the red lines were set on; if a reading at address disagrees with its own red line, fix the line and rerun.

Report movement so it holds at any camera distance:

- **Face-on, sideways moves:** percent of stance width (trail foot outer edge to lead foot outer edge at address).
- **Either view, vertical moves:** percent of address height (top of cap to the ground under the feet).
- **Down-the-line, sideways moves:** grid units relative to the tush line and the hands line.

A move under 0.2 grid units is noise. Report it as "no clear change."

**Face-on landmarks:** head center (x and y), pelvis center, lead hip outer edge, both feet outer edges, hands, ball. Note trail heel (down or up) at impact and where the head is relative to the lead foot at the finish.

**Down-the-line landmarks:** back of hips versus the tush line; head center (x and y); hands at impact versus the hands lines; clubhead relative to the hands at takeaway and at delivery (inside means toward the golfer's back, outside means toward the ball); where the shaft crosses the body at halfway (trail forearm, elbow, upper arm, shoulder); where the club reappears after impact relative to the lead shoulder.

**Ball start line (either view, best down-the-line).** On `after.jpg` read the ball's x,y in each frame it is visible. A straight track that drifts right as it climbs means the ball started right of where the camera points. That only equals "right of target" if the camera was aimed at the target, so ask what the target was. Never estimate degrees.

## 7. What the video cannot show

- **Clubface and path at impact.** At 60 fps the club moves several feet between frames. Infer them from delivery position, body motion and ball flight, and label that as inference.
- **Rolling shutter.** Near impact the shaft looks bent and the ball can appear to move before the club arrives. Never read shaft bend, shaft lean or strike quality from the impact frame.
- **Face-on** shows weight shift, sway, slide, tilt and release timing. Not plane or path.
- **Down-the-line** shows plane, posture, delivery and ball start. Not weight shift. A camera set off the hand line shifts every inside/outside reading, so say where the camera appears to be.
- **One swing is one sample.** Two clips from different days are two samples, not one swing seen twice.

## 8. Ball flight, and what to fix first

Ball flight is the ground truth; the video explains it.

- The ball **starts** roughly where the face points at impact.
- It **curves** away from the path: face open to the path curves right, closed to the path curves left.

| Flight (right-hander) | Face and path |
| --- | --- |
| Starts right, stays right (push) | Path in-to-out, face square to that path |
| Starts right, curves further right (push-slice) | Face open to target and to path |
| Starts left or straight, curves right (slice) | Path out-to-in, face open to path |
| Starts left, stays left (pull) | Path out-to-in, face square to that path |
| Starts right, curves left (draw or hook) | Path in-to-out, face closed to path |

**Face before path.** If the ball starts well off line, the face is the first fix, even when the video shows an obvious path or body fault. Fixing the path alone leaves the same face and usually trades one miss for another. Fix path or body motion first only when the ball starts near the target line and curves away.

**Combining evidence.** Ball flight sets the face. Down-the-line delivery and ball start set the path. Face-on explains why (slide, hang back, sway, release). When Cahlan has given both views or a FlightScope session, write one diagnosis from all of it, not one per clip. If a FlightScope shot is matched (section 5a), its measured start direction and curve override anything inferred from video, and the diagnosis leads with them.

## 9. Fault table

Match measurements to at most one or two rows. If nothing matches clearly, say that rather than picking the nearest.

Some movement is normal and is not a fault. With a driver, good players move the pelvis toward the target by impact (roughly 10 to 20 percent of stance width) while the head stays behind the ball. Call it a fault only when it is past those marks or comes with the other signs in the row. These thresholds are working estimates, not measured tour data.

**Face-on**

| What the frames show | Likely effect | Typical miss |
| --- | --- | --- |
| Pelvis center moves more than about 20 percent of stance width toward the target by impact, lead hip reaches or passes the lead foot's outer edge, head drops more than about 8 percent of height, and the head finishes well behind the lead foot | Path far in-to-out, face left open | Push, push-slice; hook when the hands flip |
| Fewer than two lead-hand knuckles visible at address, trail hand on top of the grip (weak grip) | Face open at impact | Push, slice, push-slice |
| Four lead-hand knuckles visible, trail hand under the grip (strong grip) | Face closed at impact | Pull, hook |
| Head moves away from the target more than about 10 percent of stance width in the backswing (sway) | Low point moves around | Fat and thin, inconsistent start line |
| Head or upper body moves toward the target at the top (reverse pivot) | Steep, out-to-in | Slice, pull, pop-up |
| Shaft passes the lead arm before the hands reach the trail thigh (early release) | Lost speed, added loft, open face | Weak high fade, thin |
| Weight still on the trail foot at the finish, trail foot flat | Path left, face open | Fade, top |
| Driver ball position well back of the lead heel | Face still open at the ball | Push |
| Driver ball position forward of the lead toe | Shoulders open, path left | Pull or pull-slice |

**Down-the-line**

| What the frames show | Likely effect | Typical miss |
| --- | --- | --- |
| At delivery the clubhead is outside the hands; halfway-down shaft crosses the shoulder; club reappears low and left of the lead shoulder | Out-to-in path (over the top) | Pull, slice |
| At delivery the clubhead is well inside the hands (behind the trail thigh); hands farther from the body at impact than at address; club reappears high | Path far in-to-out (stuck) | Push, hook |
| Hips leave the tush line toward the ball; hands higher at impact than at address (early extension) | Path in-to-out, face unstable, heel strikes | Push, hook, shank |
| At takeaway the clubhead is well inside the hands | Club gets behind the body, then is rerouted steep | Push or pull depending on the reroute |
| Top: lead wrist cupped, toe hanging down | Open face | Slice, push |
| Top: lead wrist bowed, face to the sky | Closed face | Hook, pull |
| Feet, hips or shoulders aimed right of the target line at address | Aim, not swing | Straight ball that finishes right |

A swing can be steep at halfway and still arrive from the inside at delivery. Delivery and ball start line decide the path call, not the halfway frame.

## 10. Fixes

Pick one. Each has a pass/fail he can see without a coach.

| Problem | Drill | Pass |
| --- | --- | --- |
| Face open (ball starts right) | Start-line gate: alignment stick in the ground about 10 feet ahead on the target line, half-speed swings | Ball starts left of the stick |
| Face closed (ball starts left) | Same gate | Ball starts right of the stick |
| Grip weak or strong | Grip check at address before every ball | Two to three lead-hand knuckles visible |
| Hang back, hip slide | Held finish, filmed face-on | Head over the lead foot for 3 seconds, belt buckle at the target |
| Hip slide | Alignment stick upright just outside the lead hip | Hip doesn't touch it before the ball is gone |
| Path too far in-to-out | Headcover on the ground about 18 inches behind the ball and a few inches inside the target line | Club misses the headcover |
| Path out-to-in | Headcover the same distance behind the ball, a few inches outside the target line | Club misses the headcover |
| Inside takeaway | Alignment stick on the ground along the toe line | Clubhead stays outside the stick until the shaft is parallel to the ground |

## 11. Write the answer

Cahlan wants direct, concise answers and prefers external cues and objective ground truth over feels.

- Lead with the single most likely cause in one bold sentence, saying whether it is a face problem, a path problem or both, with a plain statement of confidence.
- State what this camera angle can't show.
- Give 3 to 5 observations, each with its frame time and reading. Mark any statement about face or path as inferred.
- Say what looks fine and should be left alone, including faults you checked for and ruled out.
- Give one fix from the table, and at most one more to try later. No internal feels, and never more than one swing change at a time. If ball flight is unknown, label the fix provisional.
- Give the FlightScope check: the club path and face-to-path readings that would confirm the diagnosis, and what the opposite reading would mean.
- If a FlightScope shot was matched, name it (session date, shot number, gap in seconds, clock offset used) and quote its start direction, curve and offline before the video observations. If matching was tried and failed, say so in one line.
- Ask for whatever is missing: ball flight, the target, a grip close-up, or the other camera angle.
- Send `keys.jpg` (SendUserFile, or name the path) so he can see the lines himself.

If the golfer is his son, keep the fix to something a teenager can do alone on the range.

## 12. swing_frames.py

```python
#!/usr/bin/env python3
"""Freeze-frame a golf swing video into labeled, gridded sheets and stills.

Pass 1:  swing_frames.py VIDEO --out DIR
Pass 2:  swing_frames.py VIDEO --out DIR --impact T --crop X0,X1,Y0,Y1
Pass 3:  ... --keys address=T,top=T,impact=T,finish=T --lines X,X --hlines Y
Match:   ... --shots SESSION.csv   (pairs the swing with a FlightScope shot by clock time)
Grid units run 0-10 across and 0-10 down whatever image they are drawn on.
Needs ffmpeg/ffprobe on PATH and Pillow (pip install pillow).
"""
import argparse, array, csv, json, os, re, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont


def run(cmd, binary=False):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        sys.exit("command failed: %s\n%s" % (" ".join(cmd), r.stderr.decode()[-400:]))
    return r.stdout if binary else r.stdout.decode()


def probe(v):
    j = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", v]))
    vs = next(s for s in j["streams"] if s["codec_type"] == "video")
    n, d = vs["avg_frame_rate"].split("/")
    return {"fps": float(n) / float(d), "duration": float(j["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"]),
            "recorded": j["format"].get("tags", {}).get("creation_time")}


def audio_peaks(v, k=3, gap=1.5):
    """Loudest 10 ms windows, at least `gap` seconds apart. Impact is usually the loudest."""
    sr = 8000
    raw = run(["ffmpeg", "-v", "error", "-i", v, "-vn", "-ac", "1", "-ar", str(sr),
               "-f", "s16le", "-"], binary=True)
    a = array.array("h"); a.frombytes(raw[:len(raw) // 2 * 2])
    w = sr // 100
    env = sorted(((max(abs(x) for x in a[i:i + w]), i / sr)
                  for i in range(0, len(a) - w, w)), reverse=True)
    out = []
    for amp, t in env:
        if all(abs(t - p[0]) > gap for p in out):
            out.append((round(t, 2), amp))
        if len(out) == k:
            break
    return out


def grab(v, t, height=None, crop=None):
    """One frame at time t."""
    return grab_range(v, t, 0, height, 1, crop)[0][1]


def grab_range(v, t0, length, height=None, limit=None, crop=None):
    """Every frame from t0 for `length` seconds, decoded in one ffmpeg call -> [(time, image)]."""
    t0 = max(t0, 0); fps = probe(v)["fps"]
    with tempfile.TemporaryDirectory() as d:
        cmd = ["ffmpeg", "-v", "error", "-ss", "%.4f" % t0, "-i", v]
        cmd += ["-frames:v", str(limit)] if limit else ["-t", "%.4f" % length]
        vf = []
        if crop:  # x0,x1,y0,y1 in full-frame grid units
            x0, x1, y0, y1 = [c / 10 for c in crop]
            vf.append("crop=iw*%.4f:ih*%.4f:iw*%.4f:ih*%.4f" % (x1 - x0, y1 - y0, x0, y0))
        if height:
            vf.append("scale=-2:%d" % height)
        cmd += (["-vf", ",".join(vf)] if vf else []) + ["-q:v", "2", os.path.join(d, "%05d.jpg")]
        run(cmd)
        return [(t0 + i / fps, Image.open(os.path.join(d, f)).convert("RGB"))
                for i, f in enumerate(sorted(os.listdir(d)))]


def pick(frames, n):
    """n evenly spaced items."""
    if len(frames) <= n:
        return frames
    return [frames[round(i * (len(frames) - 1) / (n - 1))] for i in range(n)]


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
              "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def decorate(im, label, lines=(), hlines=(), grid=True):
    """Label + grid. x runs 0 (left) to 10 (right); y runs 0 (top) to 10 (bottom)."""
    d = ImageDraw.Draw(im, "RGBA"); W, H = im.size; f = font(max(13, H // 34))
    if grid:
        for i in range(1, 20):
            major = i % 2 == 0; col = (255, 255, 255, 200 if major else 70)
            x, y = W * i // 20, H * i // 20
            d.line([(x, 0), (x, H)], fill=col, width=1)
            d.line([(0, y), (W, y)], fill=col, width=1)
            if major:
                d.text((x + 2, H - f.size - 4), str(i // 2), fill=(255, 255, 0), font=f)
                d.text((2, y + 1), str(i // 2), fill=(0, 255, 255), font=f)
    w = max(2, W // 250)
    for x in lines:
        d.line([(int(W * x / 10), 0), (int(W * x / 10), H)], fill=(255, 0, 0), width=w)
    for y in hlines:
        d.line([(0, int(H * y / 10)), (W, int(H * y / 10))], fill=(255, 0, 0), width=w)
    d.rectangle([0, 0, W, f.size + 8], fill=(0, 0, 0))
    d.text((4, 3), label, fill=(255, 255, 0), font=f)
    return im


def sheet(tiles, cols, path):
    w, h = tiles[0].size; rows = -(-len(tiles) // cols)
    s = Image.new("RGB", (cols * w, rows * h))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % cols) * w, (i // cols) * h))
    s.save(path, quality=88)
    print("wrote", path)


def utc(text):
    """Parse '2026-06-04 18:53:44' or '2026-06-04T18:53:44Z' as UTC."""
    m = re.search(r"(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d)", text or "")
    if not m:
        return None
    return datetime.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def load_shots(path):
    """FlightScope shots as [(label, club, utc time)] from the session .csv or the .md table."""
    text = open(path, encoding="utf-8-sig").read().replace("\\", "")
    shots = []
    if "ShotDateTime" in text.splitlines()[0] and "," in text.splitlines()[0]:
        for r in csv.DictReader(text.splitlines()):
            if utc(r.get("ShotDateTime")):
                shots.append((r.get("SwingIndex", "?"), r.get("Club", ""), utc(r["ShotDateTime"])))
    else:
        for line in text.splitlines():
            cells = [c.strip() for c in line.split("|")]
            when = next((utc(c) for c in cells if utc(c)), None)
            if line.lstrip().startswith("|") and when:
                club = next((c for c in cells if re.search(r"Driver|Wood|Iron|Hybrid|Wedge|Putter", c)), "")
                shots.append((next((c for c in cells if c.isdigit()), "?"), club, when))
    return shots


def match_shot(impact_utc, shots, offset, window=15):
    """Print the nearest shots. gap = shot time - impact time - clock offset."""
    ranked = sorted(shots, key=lambda s: abs((s[2] - impact_utc).total_seconds() - offset))[:3]
    for label, club, when in ranked:
        print("  shot #%s %-8s %s UTC  gap %+.0f s" % (label, club, when.strftime("%Y-%m-%d %H:%M:%S"),
                                                     (when - impact_utc).total_seconds() - offset))
    if not ranked:
        print("  no shots found in the session file")
        return
    best = abs((ranked[0][2] - impact_utc).total_seconds() - offset)
    near = [r for r in ranked if abs((r[2] - impact_utc).total_seconds() - offset) <= window]
    if best > window:
        print("NO MATCH: nearest shot is %.0f s away (limit %d s)" % (best, window))
    elif len(near) > 1:
        print("AMBIGUOUS: %d shots within %d s; do not pair without another clue" % (len(near), window))
    else:
        print("MATCH: shot #%s" % ranked[0][0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--out", default="swing_out")
    ap.add_argument("--impact", type=float, help="impact time in seconds (default: loudest sound)")
    ap.add_argument("--pre", type=float, default=1.6, help="seconds before impact to cover")
    ap.add_argument("--post", type=float, default=0.7)
    ap.add_argument("--keys", default="", help="name=time,... full-res stills")
    ap.add_argument("--shots", default="", help="FlightScope session .csv (or the .md table) to match by time")
    ap.add_argument("--clock-offset", type=float, default=0.0,
                    help="seconds FlightScope's clock runs ahead of the video's, once measured")
    ap.add_argument("--recorded-at", default="", help="recording start, UTC, if the file's own timestamp is wrong")
    ap.add_argument("--crop", default="", help="X0,X1,Y0,Y1 read off overview.jpg's grid; zooms every other image")
    ap.add_argument("--lines", default="", help="x values (0-10 on the cropped grid) to draw as red vertical lines")
    ap.add_argument("--hlines", default="", help="y values (0-10 on the cropped grid) to draw as red horizontal lines")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    info = probe(a.video); fps, dur = info["fps"], info["duration"]
    lines = [float(x) for x in a.lines.split(",") if x]
    hlines = [float(x) for x in a.hlines.split(",") if x]
    crop = [float(x) for x in a.crop.split(",") if x] or None
    if crop and (len(crop) != 4 or crop[0] >= crop[1] or crop[2] >= crop[3]):
        sys.exit("--crop needs X0,X1,Y0,Y1 with X0<X1 and Y0<Y1")
    print("fps=%.1f duration=%.2fs%s" % (fps, dur, "  (high-speed clip)" if fps > 100 else ""))

    peaks = audio_peaks(a.video) if info["audio"] else []
    print("audio peaks (time, level):", peaks or "no audio track")
    impact = a.impact if a.impact is not None else (peaks[0][0] if peaks else dur / 2)
    print("impact estimate: %.2fs%s" % (impact, "" if a.impact is not None else "  <- verify on impact.jpg"))

    start = utc(a.recorded_at) or utc(info["recorded"])
    if start:
        impact_utc = start + timedelta(seconds=impact)
        print("recording started %s UTC%s; impact at %s UTC" % (
            start.strftime("%Y-%m-%d %H:%M:%S"), "" if a.recorded_at else " (file timestamp)",
            impact_utc.strftime("%Y-%m-%d %H:%M:%S")))
        if a.shots:
            match_shot(impact_utc, load_shots(a.shots), a.clock_offset)
    else:
        print("no recording timestamp in this file; pass --recorded-at to match FlightScope shots")

    # 1. overview of the whole clip: never cropped, full-frame grid for choosing --crop
    sheet([decorate(im, "t=%.2f" % t)
           for t, im in pick(grab_range(a.video, 0, dur, 600), 24)], 8, os.path.join(a.out, "overview.jpg"))

    # 2. whole swing, 24 evenly spaced frames
    t0 = max(impact - a.pre, 0)
    sheet([decorate(im, "t=%.2f" % t, lines, hlines)
           for t, im in pick(grab_range(a.video, t0, min(impact + a.post, dur) - t0, 640, crop=crop), 24)],
          8, os.path.join(a.out, "swing.jpg"))

    # 3. every frame around impact (every 4th frame for high-speed clips)
    k = 4 if fps > 100 else 1
    fr = grab_range(a.video, impact - 9.5 * k / fps, 15 * k / fps, 800, crop=crop)[::k][:15]
    sheet([decorate(im, "t=%.3f" % t, lines, hlines) for t, im in fr], 5, os.path.join(a.out, "impact.jpg"))

    # 4. ball flight: 8 consecutive frames from impact, never cropped
    fr = grab_range(a.video, impact - 0.5 / fps, 8 * k / fps, 800)[::k][:8]
    sheet([decorate(im, "t=%.3f" % t) for t, im in fr], 4, os.path.join(a.out, "after.jpg"))

    # 5. key stills at 1400 px tall, plus one side-by-side strip
    keys = []
    for kv in filter(None, a.keys.split(",")):
        name, t = kv.split("="); p = os.path.join(a.out, "key_%s.jpg" % name)
        im = decorate(grab(a.video, float(t), 1400, crop), "%s t=%.2f" % (name, float(t)), lines, hlines)
        im.save(p, quality=92); keys.append(im); print("wrote", p)
    if keys:
        sheet([k.resize((k.width * 900 // k.height, 900)) for k in keys], len(keys), os.path.join(a.out, "keys.jpg"))


if __name__ == "__main__":
    main()
```