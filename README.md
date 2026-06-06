README.md
Fixed Viewport Screenshot Stitcher
A lightweight Windows tool for capturing and stitching long webpages, PDFs, code, tables, and images from a fixed screen region.

It compares adjacent screenshots without resizing them, selects the best verified vertical displacement, removes the duplicated overlap, and validates every seam before continuing.

Why It Works
Earlier versions resized screenshots before searching for the vertical displacement. Scaling introduced interpolation and rounding errors: a correct displacement such as Y=625 could be mistaken for Y=622.

The current version samples pixels directly from the original screenshots. It does not create resized copies for displacement measurement:

Original screenshots
-> SIFT/ORB feature-consensus candidates
-> dense Y search using unscaled original pixels
-> intensity, edge, and informative-pixel verification
-> reject blank-region false matches
-> lock the seam
-> continue with the next screenshot
If a seam cannot be verified, stitching stops immediately. Unverified content is never appended to the result.

Stitching Formula
For a capture region with height H and measured vertical displacement Y:

overlap = H - Y
new content starts at zero-based row overlap
Example for a 600px-high region:

Y=500 -> overlap=100px -> crop at index 100 (human-readable row 101)
Y=580 -> overlap=20px  -> crop at index 20  (human-readable row 21)
Y=30  -> overlap=570px -> crop at index 570 (human-readable row 571)
Each accepted seam is cropped once and appended once. The program does not warp, resize, or stretch the screenshots.

Features
Fixed-region screenshot capture
90% transparent, mouse-click-through region overlay
One-pixel vertical region adjustment
Dense search across possible Y values using sampled, unscaled original pixels
SIFT feature matching with ORB fallback
RANSAC-style vertical-displacement consensus
Intensity, edge, and informative-pixel continuity verification
Blank-area false-match rejection
Seam-by-seam validation and early stopping
Seam preview images and detailed motion reports
Compact always-on-top control bar
Requirements
Windows
Python 3 with the Windows py launcher (tested with Python 3.12)
PyPI packages (see requirements.txt):

Pillow>=10.0.0
numpy>=1.24.0
opencv-python-headless>=4.8.0
ctypes is part of Python's standard library. tkinter is included with the standard Python installer for Windows when Tcl/Tk support is enabled; neither is installed with pip.

Run
Double-click:

run_screenshot_tool.bat
The launcher installs missing dependencies automatically.

You can also run it manually:

py -m pip install -r requirements.txt
py screenshot_tool.py
Usage
Click 选择.
Drag over the fixed screen region you want to capture.
Click 截屏.
Manually scroll the webpage or PDF while keeping the selected region fixed.
Click 截屏 again.
Repeat until all required content has been captured.
Click 拼接.
Use 微调 to move the selected region up or down by one pixel. Use 清空 to begin a new capture session.

Output
Files are saved in captures:

region_YYYYMMDD_HHMMSS.png
stitched_YYYYMMDD_HHMMSS.png
stitched_YYYYMMDD_HHMMSS_motion.txt
stitched_YYYYMMDD_HHMMSS_seam_01.png
