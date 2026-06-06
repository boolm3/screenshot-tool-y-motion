# Fixed Viewport Screenshot Stitcher

A lightweight Windows tool for capturing and stitching long webpages, PDFs, code, tables, and images from a fixed screen region.

It compares adjacent screenshots at their original resolution, finds the exact vertical displacement, removes the duplicated overlap, and validates every seam before continuing.

## Why It Works

Earlier versions resized screenshots before searching for the vertical displacement. Scaling introduced interpolation and rounding errors: a correct displacement such as `Y=625` could be mistaken for `Y=622`.

The current version uses original image pixels throughout the dense search and final verification:

```text
Original screenshots
-> SIFT/ORB + RANSAC candidates
-> dense original-pixel Y candidates
-> original-resolution text, edge, and texture verification
-> reject blank-region false matches
-> lock the seam
-> continue with the next screenshot
```

If a seam cannot be verified, stitching stops immediately. Unverified content is never appended to the result.

## Stitching Formula

For a capture region with height `H` and measured vertical displacement `Y`:

```text
overlap = H - Y
new content starts at row overlap
```

Example for a `600px`-high region:

```text
Y=500 -> overlap=100px -> append from row 101
Y=580 -> overlap=20px  -> append from row 21
Y=30  -> overlap=570px -> append from row 571
```

Each accepted seam is cropped once and appended once. The program does not warp, resize, or stretch the screenshots.

## Features

- Fixed-region screenshot capture
- 90% transparent, mouse-click-through region overlay
- One-pixel vertical region adjustment
- Original-resolution dense Y search
- SIFT feature matching with ORB fallback
- RANSAC displacement consensus
- Text, edge, and texture continuity verification
- Blank-area false-match rejection
- Seam-by-seam validation and early stopping
- Seam preview images and detailed motion reports
- Compact always-on-top control bar

## Requirements

- Windows
- Python 3.10 or newer

Python packages:

```text
Pillow>=10.0.0
numpy>=1.24.0
opencv-python-headless>=4.8.0
```

## Run

Double-click:

```text
run_screenshot_tool.bat
```

The launcher installs missing dependencies automatically.

You can also run it manually:

```powershell
py -m pip install -r requirements.txt
py screenshot_tool.py
```

## Usage

1. Click `选择`.
2. Drag over the fixed screen region you want to capture.
3. Click `截屏`.
4. Manually scroll the webpage or PDF while keeping the selected region fixed.
5. Click `截屏` again.
6. Repeat until all required content has been captured.
7. Click `拼接`.

Use `微调` to move the selected region up or down by one pixel. Use `清空` to begin a new capture session.

## Output

Files are saved in `captures`:

```text
region_YYYYMMDD_HHMMSS.png
stitched_YYYYMMDD_HHMMSS.png
stitched_YYYYMMDD_HHMMSS_motion.txt
stitched_YYYYMMDD_HHMMSS_seam_01.png
```

The motion report records:

- selected Y displacement
- overlap height
- candidate source
- SIFT/ORB confidence and inliers
- original-pixel and edge errors
- texture support
- candidate score margin
- final pass/fail result

## Tests

Run the regression suite with:

```powershell
py -m unittest -v test_motion_verifier.py
```

The tests cover exact displacement recovery, SIFT and dense candidates, original-pair stitching, blank-region rejection, early stopping, compact UI, and overlay click-through behavior.

## License

MIT
