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
