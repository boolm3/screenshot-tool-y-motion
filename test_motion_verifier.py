import unittest
import ctypes
from ctypes import wintypes

from PIL import Image, ImageDraw

from screenshot_tool import MotionEstimator, ScreenshotTool


def make_document():
    image = Image.new("RGB", (720, 2600), "white")
    draw = ImageDraw.Draw(image)
    for y in range(20, 2580, 37):
        draw.text(
            (30 + (y % 5) * 17, y),
            f"row {y:04d}  The quick brown fox  123456789",
            fill=(y % 190, 20, 40),
        )
        if y % 111 == 20:
            draw.line((15, y + 18, 690, y + 18), fill="black", width=2)
    return image


class MotionVerifierTests(unittest.TestCase):
    def test_main_window_is_compact(self):
        app = ScreenshotTool()
        try:
            app.update()
            self.assertLessEqual(app.winfo_height(), 100)
            self.assertLessEqual(app.winfo_width(), 520)
        finally:
            app.close()

    def test_exact_displacements(self):
        document = make_document()
        starts = [0, 317, 634, 901, 1290, 1667]
        images = [
            document.crop((0, start, document.width, start + 420))
            for start in starts
        ]

        for previous, current, expected in zip(images, images[1:], (317, 317, 267, 389, 377)):
            y, _measurement, quality = MotionEstimator.estimate(previous, current)
            self.assertEqual(expected, y)
            self.assertTrue(quality["passed"])
            self.assertIn("native-verify", _measurement["method"])

    def test_sift_and_dense_both_propose_candidates(self):
        document = make_document()
        previous = document.crop((0, 0, 720, 420))
        current = document.crop((0, 317, 720, 737))

        feature = MotionEstimator.feature_candidates(previous, current)
        dense = MotionEstimator.dense_candidates(previous, current)

        self.assertTrue(feature)
        self.assertTrue(dense)
        self.assertTrue(any(abs(item["y"] - 317) <= 2 for item in feature))
        self.assertTrue(any(abs(item["y"] - 317) <= 5 for item in dense))

    def test_stitching_stops_at_unverifiable_blank_seam(self):
        image = Image.new("RGB", (720, 420), "white")
        result, seams = ScreenshotTool.stitch_once([image, image])

        self.assertEqual(image.size, result.size)
        self.assertEqual(1, len(seams))
        self.assertFalse(seams[0]["passed"])

    def test_stitching_measures_each_original_pair(self):
        document = make_document()
        previous = document.crop((0, 0, 720, 420))
        current = document.crop((0, 317, 720, 737))

        result, seams = ScreenshotTool.stitch_once([previous, current])

        self.assertEqual(317, seams[0]["y"])
        self.assertEqual((720, 737), result.size)

    def test_failed_seam_prevents_later_images_from_polluting_result(self):
        document = make_document()
        first = document.crop((0, 0, 720, 420))
        blank = Image.new("RGB", (720, 420), "white")
        later = document.crop((0, 317, 720, 737))

        result, seams = ScreenshotTool.stitch_once([first, blank, later])

        self.assertEqual(first.size, result.size)
        self.assertEqual(1, len(seams))
        self.assertFalse(seams[0]["passed"])

    def test_overlay_is_mouse_click_through_on_windows(self):
        app = ScreenshotTool()
        try:
            app.update()
            overlay = app.overlay = __import__("screenshot_tool").RegionOverlay(
                app,
                __import__("screenshot_tool").Region(20, 20, 200, 120),
            )
            app.update()
            overlay.configure_safe_overlay()
            get_style = ctypes.windll.user32.GetWindowLongPtrW
            get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            get_style.restype = ctypes.c_ssize_t
            style = get_style(wintypes.HWND(overlay.winfo_id()), -20)
            self.assertTrue(style & 0x20)
            self.assertTrue(style & 0x08000000)
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
