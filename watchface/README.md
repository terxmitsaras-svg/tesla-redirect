# "Come Forth" — Galaxy Watch6 Classic watch face

A watch face built around the raising of Lazarus: Jesus stands fixed at the
tomb, and his own outstretched arms *are* the hands of the clock — no
separate needle graphics, no seconds hand.

- **Left arm = hour hand** — the shorter arm, in the "Lazarus, come forth"
  pointing gesture.
- **Right arm = minute hand** — the longer arm, in a blessing gesture.
- **No second hand** by design (simply don't add one in Watch Face Studio).
- Background: the tomb's rock-cut arch, the stone rolled away, Lazarus
  emerging in his grave-cloths, two mourners, a resurrection lily, and dawn
  light breaking behind the halo.

This is original vector artwork (not a copy of any existing photo/painting),
built to be crisp and legible at watch scale on an AMOLED display.

## Preview

| 10:10 | 3:15 |
|---|---|
| ![preview](preview/preview_10-10.png) | ![preview](preview/preview_03-15.png) |

## Files

```
watchface/
  assets/
    background.png    450x450  — static background layer (opaque)
    hour_hand.png      100x156 — left arm, HOUR hand (transparent PNG)
    minute_hand.png     90x211 — right arm, MINUTE hand (transparent PNG)
    center_cap.png       40x40 — gold pivot cap, top-most static layer
  source/              editable SVG/HTML source for every asset above
  preview/             composited renders at sample times
```

### Pivot points (important for assembly)

Both hands rotate around the *same* center point as the watch face itself.
Each hand image is drawn pointing straight up (12:00 rest position), with
its pivot expressed as a fraction of the image's own width/height so it
scales cleanly to any project resolution:

| Layer | Size (px) | Pivot (fraction) | Pivot (px, at native size) |
|---|---|---|---|
| `hour_hand.png`   | 100 × 156 | (0.50, 0.904) | (50, 141) |
| `minute_hand.png` | 90 × 211  | (0.50, 0.905) | (45, 191) |
| `center_cap.png`  | 40 × 40   | (0.50, 0.50)  | (20, 20)  |

`background.png` is designed on a 450×450 canvas with the dial center at
(225, 225). Galaxy Watch6 Classic ships in two sizes — 43 mm (432×432) and
47 mm (480×480) — Watch Face Studio scales the whole canvas uniformly to
whichever project resolution you pick, so the pivot fractions above stay
correct either way.

## Build it with Samsung Watch Face Studio (recommended, no coding)

Watch Face Studio is Samsung's free official tool for building watch faces
for Galaxy Watch / Wear OS. This is the realistic, supported path — actually
compiling and signing a watch-face APK isn't something that can be done
headlessly here, so these are the exact steps to finish it yourself in the
GUI:

1. **Install Watch Face Studio** (Windows or macOS):
   https://developer.samsung.com/watch-face-studio
2. **New Project** → shape **Round** → resolution: **480×480** if you have
   the 47 mm Galaxy Watch6 Classic, or **432×432** for the 43 mm. (If unsure,
   check *Settings → Watch info* on the watch, or the box — 47 mm is the
   larger case.)
3. **Background layer**: drag in `assets/background.png`, stretch to fill
   the full canvas (0,0 to canvas edge).
4. **Add a Hand layer → Hour**:
   - Image: `assets/hour_hand.png`
   - Pivot / anchor: **X = 0.5, Y = 0.904** (Watch Face Studio's hand tool
     lets you set the pivot as a normalized point on the image — drag it to
     just above the bottom edge, centered horizontally, or type the values).
   - Rotation binding: **Hour**, 12-hour analog (30° per hour + minute
     contribution — this is the tool's default "smooth hour hand" mode).
5. **Add a Hand layer → Minute**:
   - Image: `assets/minute_hand.png`
   - Pivot: **X = 0.5, Y = 0.905**
   - Rotation binding: **Minute**, 6° per minute.
6. **Do not add a Second hand layer.** That's the whole trick to "no
   seconds" — Watch Face Studio only draws what you give it.
7. **Top layer (optional but recommended)**: add `assets/center_cap.png` as
   a static (non-rotating) image, centered at the dial's exact center, so it
   sits above both hands and hides the seam where they pivot — exactly like
   a real watch's center cap.
8. **Preview**: use the built-in simulator's time slider to check the hands
   sweep correctly and nothing clips at the round bezel edge.
9. **Install on your Galaxy Watch6 Classic**:
   - Easiest: pair your watch with Watch Face Studio over Wi-Fi (Studio →
     *Run on device*, watch needs Developer Mode + ADB debugging enabled in
     its Watch Face settings) and it installs directly.
   - Or: *Export* → *Export to APK*, then sideload via the Galaxy Wearable
     app on your phone (Watch faces → My Watch Faces → install from file) or
     via `adb install` over Wi-Fi/USB.

Total time for someone doing this the first time: ~15–20 minutes.

## Editing the artwork

`source/*.html` are the actual SVG sources (viewable by opening in any
browser). Each is a self-contained SVG you can edit directly — colors,
gestures, and the tomb scene are all plain vector paths with named
gradients (`mantle`, `tunic`, `skin`, `stone`, `wrap`, `halo`, etc.) at the
top of each file. After editing, re-export to PNG at the same pixel
dimensions listed above (any SVG-to-PNG renderer works — a headless browser
screenshot at the exact viewport size is what was used here).
