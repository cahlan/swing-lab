---
name: lab-measure
description: Measure one golf swing from one video and write a swing record JSON. Use only when handed a single swing to measure by the lab-batch skill (a video path, a strike time, a unit id and a scratch folder). Not for coaching or diagnosis.
---

# Measure one swing

You are a measuring instrument. You get one video and one strike time. You return one record of what the frames show. You know nothing about this golfer and you are not asked what is wrong with the swing.

## Rules

1. **Only this swing.** Do not open any other swing's record, any roll-up, profile, golden set or coaching notes. Do not look in the archive's `_analysis` folder at all. Work only in the scratch folder you were given.
2. **Measure, don't diagnose.** No fixes, no drills, no ball-flight theory, no guesses about the clubface.
3. **Unreadable is an answer.** A landmark you can't see is `null`. An observation you can't judge is `unreadable`. Never guess to fill a field.
4. **One crop for the whole swing.** Every landmark is read on the same cropped grid.
5. **Read to one decimal.** Every image carries a grid: x runs 0 (left) to 10 (right) in yellow, y runs 0 (top) to 10 (bottom) in cyan, with faint half-unit lines.

## Inputs you were given

- `VIDEO`: path to the video file.
- `IMPACT`: the candidate strike time in seconds, found by sound. It can be wrong.
- `UNIT`: the swing's id.
- `SCRATCH`: a folder for frame sheets and your record.

## Step 1: find the swing

```bash
python3 scripts/swing_frames.py VIDEO --out SCRATCH --impact IMPACT
```

Read `SCRATCH/overview.jpg` and `SCRATCH/impact.jpg`.

- **Is there a strike at IMPACT?** The club should reach the ball within a frame or two. If the strike is at a different time, rerun with the right `--impact` and set `impact_corrected` in the record to the reason. If there is no strike, no ball, or no golfer, stop and return a skip (see "Returning").
- **View:** `face-on` (camera facing the chest, target to one side), `dtl` (down the line: camera behind the golfer, looking toward the target) or `angled` (in between).
- **Camera line (down the line only):** where the camera stood. `on_line`: behind the hands, looking along the target line; you see the golfer side-on. `inside`: closer to the golfer's heel side; you see part of his back and the trail arm hides the lead arm. `outside`: beyond the ball side; you see part of his chest. `unknown` if you can't tell. An off-line camera shifts every inside/outside reading, so this matters.
- **Handedness.** The definitions below are for a right-hander. Mirror left and right for a left-hander and say so in `notes`.
- **Club.** `driver`, `wood`, `hybrid`, `iron`, `wedge` or `unknown`.
- **High-speed clip?** The script says so above 100 fps. Widen the window, for example `--pre 8 --post 3`.
- **Crop box** from the overview grid: `X0,X1,Y0,Y1`. Face-on: feet to cap with about one unit of margin each side. Down the line: include the ball and the clubhead at the top of the backswing.

## Step 2: zoom in and pick key frames

```bash
python3 scripts/swing_frames.py VIDEO --out SCRATCH --impact T --crop X0,X1,Y0,Y1
```

Read `swing.jpg`, `impact.jpg` and `after.jpg`. Pick key times off the labels:

- **Face-on:** `address` (last still frame before takeaway), `top`, `impact`, `finish`.
- **Finish is not a judgment.** In both views it is the frame 1.0 s after your impact frame. If the clip ends sooner, it is the last frame.
- **Down the line:** `address`, `takeaway`, `top`, `halfway` (lead arm parallel to the ground coming down), `delivery`, `impact`, `finish`. Takeaway and delivery are roughly where the shaft is parallel to the ground; Step 3 pins them exactly.

## Step 3: pin the takeaway and delivery frames (down the line only)

These two frames decide the clubhead-versus-hands readings, and the club moves far enough between frames that being one frame off changes the answer. Do not pick them by eye. Pick them by this rule:

**Takeaway is the frame going back, and delivery is the frame coming down, in which the clubhead is closest to level with the hands in the image.**

1. Estimate each time: takeaway from `swing.jpg`, delivery from `impact.jpg`.
2. Rerun with five candidates one frame apart around each estimate. One frame is 1 divided by the frame rate the script printed (0.017 s at 60, 0.033 s at 30).

```bash
python3 scripts/swing_frames.py VIDEO --out SCRATCH --impact T --crop X0,X1,Y0,Y1 \
  --keys ta1=T,ta2=T,ta3=T,ta4=T,ta5=T,de1=T,de2=T,de3=T,de4=T,de5=T
```

3. On each candidate still, read `hands` and `clubhead`. For each set of five, choose the one with the smallest difference between the clubhead's y and the hands' y. If two tie, take the earlier.
4. If the best candidate is the first or last of its five, the level frame may be outside the window. Shift the window that way and repeat.
5. Use the chosen times as `takeaway` and `delivery` in the next step.
6. **Both need a second frame.** The level moment usually falls between two frames. Coming down, the clubhead can travel a third of the golfer's height in one frame; going back at 30 frames per second it moves enough to change the reading. For each of takeaway and delivery, also record the adjacent candidate on the other side of level as `takeaway_other` and `delivery_other`, with its `t`, `hands` and `clubhead`. If the clubhead is below the hands in `takeaway`, `takeaway_other` is the next frame, where it is above, and the reverse. The script reads the level moment off the two. If the clubhead can't be read in a frame, record that clubhead as `null`.

Read `hands` as the middle of the grip, between the two hands, and `clubhead` as the center of the clubhead, on every frame.

## Step 4: key stills

```bash
python3 scripts/swing_frames.py VIDEO --out SCRATCH --impact T --crop X0,X1,Y0,Y1 \
  --keys address=T,top=T,impact=T,finish=T
```

Run this step last, with every key frame for the view, so `keys.jpg` shows exactly the frames you record.

Read each `key_<name>.jpg` and read off every landmark below. If you set red reference lines with `--lines` or `--hlines`, the values you pass must equal the address readings you record.

**Camera check.** The feet should sit at the same grid position in address, top and impact. If they don't, set `camera_moved` to true and lower `quality`.

**Things the frames cannot show.** Near impact the shaft looks bent and the ball can appear to move before the club arrives; that is the phone's rolling shutter. Never read shaft bend, shaft lean or strike quality from the impact frame.

## Landmarks

Each is `[x, y]` on the cropped grid, or `null`. Each key frame also has `t`, its time in seconds.

**Face-on**

| Frame | Landmarks |
| --- | --- |
| address | `head` (center of the head), `cap_top` (top of the cap or head), `ground` (ground under the feet; only y is used), `lead_foot_outer`, `trail_foot_outer` (outer edges of the shoes), `pelvis_center` (midpoint of the hips at belt height), `lead_hip_outer`, `hands`, `ball` |
| top | `head`, `pelvis_center` |
| impact | `head`, `pelvis_center`, `lead_hip_outer` |
| finish | `head` |

**Down the line**

| Frame | Landmarks |
| --- | --- |
| address | `hips_back` (rearmost point of the hips), `head`, `cap_top`, `ground`, `hands` (middle of the grip), `ball`, `clubhead` (center of the clubhead) |
| takeaway | `hands`, `clubhead` |
| top | `hands` |
| halfway | `hands` |
| delivery | `hands`, `clubhead` |
| takeaway_other, delivery_other (the adjacent frame across level) | `hands`, `clubhead` |
| impact | `hips_back`, `head`, `hands` |
| finish | time only |

## Observations

Answer every code below for the view: `yes`, `no` or `unreadable`, with `confidence` (`high`, `medium`, `low`). A `yes` needs `evidence` naming the frame and what you saw.

These are only the things a reader has to look at. Anything that follows from positions, such as whether the hips moved toward the ball or the clubhead was inside the hands, is worked out by the script from your landmarks. Do not answer those; read the landmarks carefully.

**Face-on**

| Code | Yes when |
| --- | --- |
| `early_release` | Shaft passes the lead arm before the hands reach the trail thigh |
| `trail_heel_up_before_impact` | Trail heel is clearly off the ground in the frame before the strike |
| `ball_too_far_back` | Ball is well back of where that club is normally played (driver: back of the lead heel) |
| `ball_too_far_forward` | Ball is well forward of normal (driver: forward of the lead toe) |
| `weak_grip` | Fewer than two lead-hand knuckles visible, trail hand on top of the grip |
| `strong_grip` | Four lead-hand knuckles visible, trail hand under the grip |

For the grip codes, rerun with a tight crop on the hands at address if needed. Sleeves and distance often hide the grip: answer `unreadable`.

**Down the line**

| Code | Yes when |
| --- | --- |
| `steep_at_halfway` | At halfway the shaft crosses the trail shoulder or upper arm, not the forearm or elbow |
| `open_face_at_top` | Lead wrist cupped, toe of the club hanging down |
| `closed_face_at_top` | Lead wrist bowed, clubface toward the sky |
| `weight_on_heels_at_address` | Hips set well behind the heels with the chest far over the toes to balance |
| `aimed_right`, `aimed_left` | Feet, hips or shoulders point clearly off the target line. `unreadable` unless the target line is evident |
| `ball_starts_right`, `ball_starts_left` | On `after.jpg` the ball's track drifts steadily that way from the camera's line |

## The record

Write `SCRATCH/record.json`:

```json
{
  "schema": 1,
  "model": "the model you are, for example claude-opus-5-5",
  "view": "face-on",
  "club": "driver",
  "camera_line": "on_line",
  "quality": "good",
  "impact_s": 5.05,
  "crop": [1.5, 8, 1.8, 9],
  "camera_moved": false,
  "frames": {
    "address": {"t": 3.80, "head": [4.3, 1.8], "cap_top": [4.3, 1.2], "ground": [5.0, 7.4], "ball": null},
    "top": {"t": 4.80, "head": [4.3, 1.8]}
  },
  "observations": [
    {"code": "early_release", "present": "no", "confidence": "high", "evidence": ""},
    {"code": "trail_heel_up_before_impact", "present": "yes", "confidence": "medium", "evidence": "t=5.03, one frame before the strike: heel clearly off the ground"}
  ],
  "summary": "One plain sentence on what this swing shows.",
  "notes": "Anything odd: slow motion, sleeve hides the grip, left-handed."
}
```

- `camera_line`: required for a down-the-line swing: `on_line`, `inside`, `outside` or `unknown`.
- `quality`: count the problems: under 50 frames per second; camera off line or not square; camera moved; a body part or the club hidden at a key frame; golfer partly out of frame. None is `good`, one is `usable`, two or more is `poor`.
- `impact_corrected`: set it only when the strike you confirmed is more than 0.25 s from `IMPACT`. Small differences need no note; just record your `impact_s`.
- An `angled` view needs only `model`, `view`, `club`, `crop`, `summary` and whatever is readable.
- Optional: `sanity_override` (see below).

## Returning

Return to the caller exactly one of these and nothing else. Do not describe the swing, your readings or your answers; the caller must stay blind to them.

- `record: SCRATCH/record.json` and `evidence: SCRATCH/keys.jpg`, or
- `skip: <reason>` when there is no usable swing (no strike, practice swing with no ball, golfer cut off, too dark, camera moving throughout).

If the caller reports that the record was rejected, fix exactly what the rejection lists and return it again. A rejection saying a takeaway or delivery frame is not level means Step 3 was not followed: redo it. If a rejection says the readings are impossible, re-read those landmarks from the stills. Only if the stills really show an unusual setup, add `"sanity_override": "<why>"`.
