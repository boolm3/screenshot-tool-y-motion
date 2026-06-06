import datetime as dt
import ctypes
import os
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass
from tkinter import messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageGrab, ImageTk


APP_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURE_DIR = os.path.join(APP_DIR, "captures")


def ensure_capture_dir():
    os.makedirs(CAPTURE_DIR, exist_ok=True)


def output_path(prefix, extension=".png"):
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(CAPTURE_DIR, f"{prefix}_{stamp}{extension}")


@dataclass
class Region:
    x: int
    y: int
    width: int
    height: int

    @property
    def bbox(self):
        return self.x, self.y, self.x + self.width, self.y + self.height


@dataclass
class Selection:
    capture: Region
    overlay: Region
    screen_width: int
    screen_height: int
    canvas_width: int
    canvas_height: int

    def overlay_from_capture(self, region):
        return Region(
            round(region.x * self.canvas_width / self.screen_width),
            round(region.y * self.canvas_height / self.screen_height),
            round(region.width * self.canvas_width / self.screen_width),
            round(region.height * self.canvas_height / self.screen_height),
        )


class RegionSelector(tk.Toplevel):
    def __init__(self, master, on_done, on_cancel):
        super().__init__(master)
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.screen_image = ImageGrab.grab()
        self.screen_photo = None
        self.start_x = 0
        self.start_y = 0
        self.rectangle = None

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.canvas = tk.Canvas(self, cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", self.cancel)
        self.after(30, self.render)

    def render(self):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        preview = self.screen_image.resize((width, height), Image.Resampling.LANCZOS)
        self.screen_photo = ImageTk.PhotoImage(preview)
        self.canvas.create_image(0, 0, image=self.screen_photo, anchor="nw")
        self.canvas.create_text(
            24,
            24,
            anchor="nw",
            fill="white",
            font=("Microsoft YaHei UI", 16, "bold"),
            text="在真实屏幕截图上拖动选择区域；按 Esc 取消",
        )

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rectangle = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#00e5ff",
            width=3,
        )

    def on_drag(self, event):
        if self.rectangle is not None:
            self.canvas.coords(self.rectangle, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        x1 = max(0, min(self.start_x, event.x))
        y1 = max(0, min(self.start_y, event.y))
        x2 = min(canvas_width, max(self.start_x, event.x))
        y2 = min(canvas_height, max(self.start_y, event.y))
        overlay = Region(x1, y1, x2 - x1, y2 - y1)
        if overlay.width < 5 or overlay.height < 5:
            self.cancel()
            messagebox.showwarning("区域太小", "请重新选择更大的截图区域。")
            return

        scale_x = self.screen_image.width / canvas_width
        scale_y = self.screen_image.height / canvas_height
        capture = Region(
            round(overlay.x * scale_x),
            round(overlay.y * scale_y),
            round(overlay.width * scale_x),
            round(overlay.height * scale_y),
        )
        selection = Selection(
            capture,
            overlay,
            self.screen_image.width,
            self.screen_image.height,
            canvas_width,
            canvas_height,
        )
        self.destroy()
        self.on_done(selection)

    def cancel(self, _event=None):
        self.destroy()
        self.on_cancel()


class RegionOverlay(tk.Toplevel):
    def __init__(self, master, region):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.10)
        self.canvas = tk.Canvas(
            self,
            bg="#00e5ff",
            highlightthickness=2,
            highlightbackground="#00a7c4",
        )
        self.canvas.pack(fill="both", expand=True)
        self.set_region(region)
        self.after(50, self.configure_safe_overlay)

    def configure_safe_overlay(self):
        try:
            hwnd = wintypes.HWND(self.winfo_id())
            get_style = ctypes.windll.user32.GetWindowLongPtrW
            get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            get_style.restype = ctypes.c_ssize_t
            set_style = ctypes.windll.user32.SetWindowLongPtrW
            set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            set_style.restype = ctypes.c_ssize_t
            extended_style = get_style(hwnd, -20)
            set_style(
                hwnd,
                -20,
                extended_style | 0x20 | 0x80 | 0x08000000,
            )
            if not ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11):
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x01)
        except (AttributeError, OSError):
            pass

    def set_region(self, region):
        self.geometry(f"{region.width}x{region.height}+{region.x}+{region.y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(self.configure_safe_overlay)


class NudgeDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("微调")
        self.resizable(False, False)
        self.transient(master)
        self.attributes("-topmost", True)
        body = ttk.Frame(self, padding=14)
        body.grid()
        ttk.Label(body, text="每次移动布 1 像素").grid(row=0, column=0, pady=(0, 10))
        ttk.Button(body, text="上移 1px", command=lambda: master.nudge(-1)).grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(body, text="下移 1px", command=lambda: master.nudge(1)).grid(
            row=2, column=0, sticky="ew"
        )
        self.bind("<Up>", lambda _event: master.nudge(-1))
        self.bind("<Down>", lambda _event: master.nudge(1))
        self.focus_set()


class MotionEstimator:
    @staticmethod
    def estimate(previous, current):
        feature_candidates = MotionEstimator.feature_candidates(previous, current)
        dense_candidates = MotionEstimator.dense_candidates(previous, current)
        seeds = []
        for candidate in feature_candidates:
            seeds.append((candidate["y"], candidate))
        for candidate in dense_candidates:
            seeds.append((candidate["y"], candidate))

        if not seeds:
            fallback = max(1, min(previous.height - 1, previous.height // 2))
            seeds.append(
                (
                    fallback,
                    {
                        "method": "fallback",
                        "y": fallback,
                        "confidence": 0.0,
                        "inliers": 0,
                        "matches": 0,
                    },
                )
            )

        y, quality, ranking = DisplacementVerifier.resolve(previous, current, seeds)
        source_y, source = min(seeds, key=lambda item: abs(item[0] - y))
        measurement = {
            **source,
            "method": f"{source['method']}+native-verify",
            "original_y": source_y,
            "calibration": y - source_y,
            "candidate_count": len(ranking),
        }
        return y, measurement, quality

    @staticmethod
    def feature_candidates(previous, current):
        previous_gray = np.asarray(previous.convert("L"))
        current_gray = np.asarray(current.convert("L"))
        if hasattr(cv2, "SIFT_create"):
            detector = cv2.SIFT_create(nfeatures=2200)
            norm = cv2.NORM_L2
            ratio = 0.75
            method = "SIFT-RANSAC"
        else:
            detector = cv2.ORB_create(nfeatures=2800, fastThreshold=8)
            norm = cv2.NORM_HAMMING
            ratio = 0.82
            method = "ORB-RANSAC"

        kp1, des1 = detector.detectAndCompute(previous_gray, None)
        kp2, des2 = detector.detectAndCompute(current_gray, None)
        if des1 is None or des2 is None:
            return []

        matcher = cv2.BFMatcher(norm)
        motions = []
        x_tolerance = max(6.0, previous.width * 0.02)
        for pair in matcher.knnMatch(des1, des2, k=2):
            if len(pair) != 2:
                continue
            best, second = pair
            if best.distance >= ratio * second.distance:
                continue
            p1 = kp1[best.queryIdx].pt
            p2 = kp2[best.trainIdx].pt
            delta_x = p1[0] - p2[0]
            delta_y = p1[1] - p2[1]
            if abs(delta_x) <= x_tolerance and 1 <= delta_y < previous.height:
                motions.append((delta_y, delta_x))

        if len(motions) < 4:
            return []

        results = []
        for hypothesis, _x in motions:
            inliers = [
                motion
                for motion in motions
                if abs(motion[0] - hypothesis) <= 2.5
            ]
            if len(inliers) < 4:
                continue
            ys = np.asarray([item[0] for item in inliers], dtype=np.float32)
            xs = np.asarray([item[1] for item in inliers], dtype=np.float32)
            y = int(round(float(np.median(ys))))
            results.append(
                {
                    "method": method,
                    "y": y,
                    "inliers": len(inliers),
                    "matches": len(motions),
                    "confidence": len(inliers) / len(motions),
                    "residual": float(np.median(np.abs(ys - y))),
                    "x_error": float(np.median(np.abs(xs))),
                }
            )

        unique = {}
        for item in sorted(
            results,
            key=lambda value: (-value["inliers"], value["residual"], value["x_error"]),
        ):
            unique.setdefault(item["y"], item)
        return list(unique.values())[:5]

    @staticmethod
    def dense_candidates(previous, current):
        previous_gray = np.asarray(previous.convert("L"), dtype=np.float32) / 255.0
        current_gray = np.asarray(current.convert("L"), dtype=np.float32) / 255.0
        sample_width = min(256, previous_gray.shape[1], current_gray.shape[1])
        columns = np.linspace(
            0,
            min(previous_gray.shape[1], current_gray.shape[1]) - 1,
            sample_width,
        ).astype(np.int32)
        scores = []
        for y in range(1, previous.height - 15):
            overlap = min(previous_gray.shape[0] - y, current_gray.shape[0])
            if overlap < 4:
                continue
            sample_count = min(80, overlap)
            indices = np.linspace(0, overlap - 1, sample_count).astype(np.int32)
            left = previous_gray[y + indices][:, columns]
            right = current_gray[indices][:, columns]
            score = float(np.abs(left - right).mean())
            scores.append((score, y))

        local_minima = []
        for index, item in enumerate(scores):
            left = scores[max(0, index - 3):index]
            right = scores[index + 1:index + 4]
            if all(item[0] <= neighbor[0] for neighbor in left + right):
                local_minima.append(item)

        selected = []
        for score, y in sorted(local_minima or scores):
            if any(abs(y - item["y"]) < 12 for item in selected):
                continue
            selected.append(
                {
                    "method": "dense",
                    "y": y,
                    "confidence": max(0.0, 1.0 - score / 0.20),
                    "score": score,
                    "inliers": 0,
                    "matches": 0,
                }
            )
            if len(selected) == 5:
                break
        return selected

class DisplacementVerifier:
    FINE_RADIUS = 8

    @staticmethod
    def resolve(previous, current, seeds):
        candidate_ys = set()
        maximum = min(previous.height, current.height) - 1
        for seed_y, _source in seeds:
            for y in range(max(1, seed_y - DisplacementVerifier.FINE_RADIUS), min(maximum, seed_y + DisplacementVerifier.FINE_RADIUS) + 1):
                candidate_ys.add(y)

        ranking = [
            (DisplacementVerifier.score(previous, current, y), y)
            for y in sorted(candidate_ys)
        ]
        ranking.sort(
            key=lambda item: (
                item[0]["support"] < 0.002,
                item[0]["score"],
                -item[0]["support"],
                item[1],
            )
        )
        quality, y = ranking[0]

        separated = [
            item for item in ranking[1:]
            if abs(item[1] - y) > 1 and item[0]["support"] >= 0.002
        ]
        runner_up_score = separated[0][0]["score"] if separated else float("inf")
        margin = runner_up_score - quality["score"]
        relative_margin = margin / max(runner_up_score, 1e-9)
        passed = (
            quality["score"] <= 0.030
            and quality["support"] >= 0.002
            and (
                quality["score"] <= 0.001
                or margin >= 0.0005
                or relative_margin >= 0.12
            )
        )
        quality = {
            **quality,
            "passed": passed,
            "runner_up_score": runner_up_score,
            "score_margin": margin,
            "relative_margin": relative_margin,
        }
        return y, quality, ranking

    @staticmethod
    def score(previous, current, y):
        overlap = min(previous.height - y, current.height)
        if overlap < 4:
            return {
                "score": float("inf"),
                "pixel_mae": 1.0,
                "edge_mae": 1.0,
                "match_ratio": 0.0,
                "support": 0.0,
            }

        left = np.asarray(
            previous.crop((0, y, previous.width, y + overlap)).convert("L"),
            dtype=np.float32,
        )
        right = np.asarray(
            current.crop((0, 0, current.width, overlap)).convert("L"),
            dtype=np.float32,
        )

        if left.shape[1] > 640:
            columns = np.linspace(0, left.shape[1] - 1, 640).astype(np.int32)
            left = left[:, columns]
            right = right[:, columns]
        if left.shape[0] > 320:
            rows = np.linspace(0, left.shape[0] - 1, 320).astype(np.int32)
            left = left[rows]
            right = right[rows]

        left_edges = np.abs(np.diff(left, axis=1, prepend=left[:, :1]))
        right_edges = np.abs(np.diff(right, axis=1, prepend=right[:, :1]))
        informative = (
            (left < 248)
            | (right < 248)
            | (left_edges > 5)
            | (right_edges > 5)
        )
        support = float(informative.mean())
        if informative.sum() < 128:
            informative = np.ones_like(informative, dtype=bool)

        pixel_diff = np.abs(left - right)[informative]
        edge_diff = np.abs(left_edges - right_edges)[informative]
        pixel_limit = np.quantile(pixel_diff, 0.90)
        edge_limit = np.quantile(edge_diff, 0.90)
        pixel_trimmed = pixel_diff[pixel_diff <= pixel_limit]
        edge_trimmed = edge_diff[edge_diff <= edge_limit]
        pixel_mae = float(pixel_trimmed.mean() / 255.0)
        edge_mae = float(edge_trimmed.mean() / 255.0)
        match_ratio = float((pixel_diff <= 2.0).mean())
        score = pixel_mae + 0.55 * edge_mae + 0.03 * (1.0 - match_ratio)
        return {
            "score": score,
            "pixel_mae": pixel_mae,
            "edge_mae": edge_mae,
            "match_ratio": match_ratio,
            "support": support,
        }


class ScreenshotTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Y 位移截图拼接工具")
        self.geometry("500x92")
        self.minsize(440, 92)
        self.resizable(True, False)
        self.attributes("-topmost", True)
        self.selection = None
        self.overlay = None
        self.images = []
        self.preview_photo = None
        self.x_var = tk.IntVar(value=0)
        self.y_var = tk.IntVar(value=0)
        self.width_var = tk.IntVar(value=0)
        self.height_var = tk.IntVar(value=0)
        self.columnconfigure(0, weight=1)
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def create_widgets(self):
        buttons = ttk.Frame(self, padding=(10, 10, 10, 6))
        buttons.grid(row=0, column=0, sticky="ew")
        buttons.columnconfigure(5, weight=1)
        ttk.Button(buttons, text="选择", command=self.select_region).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="截屏", command=self.capture).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(buttons, text="拼接", command=self.finish).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(buttons, text="微调", command=self.open_nudge).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(buttons, text="清空", command=self.clear).grid(row=0, column=4)
        info = ttk.Frame(self, padding=(10, 0, 10, 8))
        info.grid(row=1, column=0, sticky="ew")
        info.columnconfigure(0, weight=1)
        self.status = ttk.Label(info, text="未选择区域", foreground="#555")
        self.status.grid(row=0, column=0, sticky="w")
        self.preview = ttk.Label(self)

    def select_region(self):
        self.withdraw()
        self.after(180, lambda: RegionSelector(self, self.set_selection, self.deiconify))

    def set_selection(self, selection):
        self.deiconify()
        self.selection = selection
        self.images = []
        self.sync_fields(selection.capture)
        self.position_away_from_selection()
        self.show_overlay()
        self.update_status("已选择")

    def position_away_from_selection(self):
        region = self.selection.overlay
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        gap = 10

        if region.y >= height + gap:
            x = min(max(0, region.x), screen_width - width)
            y = region.y - height - gap
        elif region.y + region.height + height + gap <= screen_height:
            x = min(max(0, region.x), screen_width - width)
            y = region.y + region.height + gap
        elif region.x >= width + gap:
            x = region.x - width - gap
            y = min(max(0, region.y), screen_height - height)
        else:
            x = min(screen_width - width, region.x + region.width + gap)
            y = min(max(0, region.y), screen_height - height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def sync_fields(self, region):
        self.x_var.set(region.x)
        self.y_var.set(region.y)
        self.width_var.set(region.width)
        self.height_var.set(region.height)

    def apply_fields(self):
        try:
            region = Region(
                int(self.x_var.get()),
                int(self.y_var.get()),
                int(self.width_var.get()),
                int(self.height_var.get()),
            )
        except tk.TclError:
            messagebox.showwarning("坐标无效", "请输入有效整数。")
            return
        if region.width < 5 or region.height < 5:
            messagebox.showwarning("区域太小", "宽和高至少为 5 像素。")
            return
        if self.selection is None:
            self.selection = Selection(region, region, region.width, region.height, region.width, region.height)
        else:
            self.selection.capture = region
            self.selection.overlay = self.selection.overlay_from_capture(region)
        self.show_overlay()
        self.update_status("已应用")

    def show_overlay(self):
        if self.selection is None:
            return
        if self.overlay is None or not self.overlay.winfo_exists():
            self.overlay = RegionOverlay(self, self.selection.overlay)
        else:
            self.overlay.set_region(self.selection.overlay)

    def open_nudge(self):
        if self.selection is None:
            messagebox.showinfo("先选择区域", "请先选择截图区域。")
            return
        NudgeDialog(self)

    def nudge(self, dy):
        region = self.selection.capture
        moved = Region(region.x, max(0, region.y + dy), region.width, region.height)
        self.selection.capture = moved
        self.selection.overlay = self.selection.overlay_from_capture(moved)
        self.sync_fields(moved)
        self.show_overlay()
        self.update_status("已微调")

    def capture(self):
        if self.selection is None:
            messagebox.showinfo("先选择区域", "请先选择截图区域。")
            return
        if self.overlay is not None:
            self.overlay.withdraw()
        self.withdraw()
        self.after(180, self._capture)

    def _capture(self):
        ensure_capture_dir()
        image = ImageGrab.grab(bbox=self.selection.capture.bbox).convert("RGB")
        self.images.append(image)
        path = output_path("region")
        image.save(path)
        self.deiconify()
        self.show_overlay()
        self.show_preview(path)
        self.update_status("已截")

    def finish(self):
        if not self.images:
            messagebox.showinfo("没有截图", "请至少截取一张图片。")
            return
        ensure_capture_dir()
        result, seams = self.stitch_once(self.images)
        path = output_path("stitched")
        result.save(path)
        report = os.path.splitext(path)[0] + "_motion.txt"
        self.write_report(report, path, seams)
        self.save_seam_previews(path, seams)
        if self.overlay is not None:
            self.overlay.withdraw()
        self.show_preview(path)
        warnings = sum(not seam["passed"] for seam in seams)
        if warnings:
            self.status.configure(
                text=f"第 {seams[-1]['index']} 条接缝未通过质检，拼接已停止。报告：{report}",
                foreground="#b00020",
            )
            return
        self.status.configure(
            text=f"拼接完成：{path}",
            foreground="#087a31",
        )

    @staticmethod
    def stitch_once(images):
        result = images[0]
        seams = []
        for index, (previous, current) in enumerate(zip(images, images[1:]), start=1):
            y, measurement, qc = MotionEstimator.estimate(previous, current)
            overlap = max(0, current.height - y)
            seams.append(
                {
                    "index": index,
                    "y": y,
                    "overlap": overlap,
                    "measurement": measurement,
                    **qc,
                    "previous": previous,
                    "current": current,
                }
            )
            if not qc["passed"]:
                break

            new_content = current.crop((0, overlap, current.width, current.height))
            combined = Image.new("RGB", (result.width, result.height + new_content.height), "white")
            combined.paste(result, (0, 0))
            combined.paste(new_content, (0, result.height))
            result = combined
        return result, seams

    @staticmethod
    def save_seam_previews(stitched_path, seams):
        prefix = os.path.splitext(stitched_path)[0]
        for seam in seams:
            previous = seam["previous"]
            current = seam["current"]
            overlap = seam["overlap"]
            band = min(120, previous.height, current.height)
            top = previous.crop((0, previous.height - band, previous.width, previous.height))
            start = min(max(0, overlap), current.height - 1)
            bottom = current.crop((0, start, current.width, min(current.height, start + band)))
            preview = Image.new("RGB", (previous.width, top.height + 2 + bottom.height), "white")
            preview.paste(top, (0, 0))
            preview.paste((255, 0, 0), (0, top.height, previous.width, top.height + 2))
            preview.paste(bottom, (0, top.height + 2))
            preview.save(f"{prefix}_seam_{seam['index']:02d}.png")

    @staticmethod
    def write_report(report_path, stitched_path, seams):
        lines = [
            "Y Motion Screenshot Stitcher",
            f"stitched={os.path.basename(stitched_path)}",
            "formula=overlap = viewport_height - Y",
            "",
        ]
        for seam in seams:
            measurement = seam["measurement"]
            lines.append(
                f"seam{seam['index']}: Y={seam['y']}, overlap={seam['overlap']}, "
                f"method={measurement['method']}, confidence={measurement['confidence']:.4f}, "
                f"inliers={measurement.get('inliers', 0)}/{measurement.get('matches', 0)}, "
                f"original_y={measurement.get('original_y', seam['y'])}, "
                f"calibration={measurement.get('calibration', 0):+d}, "
                f"pixel_mae={seam['pixel_mae']:.6f}, edge_mae={seam['edge_mae']:.6f}, "
                f"match_ratio={seam['match_ratio']:.4f}, support={seam['support']:.4f}, "
                f"score={seam['score']:.6f}, margin={seam['score_margin']:.6f}, "
                f"passed={seam['passed']}"
            )
        with open(report_path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

    def update_status(self, prefix):
        region = self.selection.capture
        self.status.configure(
            text=f"{prefix}：x={region.x}, y={region.y}, 宽={region.width}, 高={region.height}；已截 {len(self.images)} 张",
            foreground="#555",
        )

    def show_preview(self, path):
        image = Image.open(path)
        max_width = max(240, self.preview.winfo_width() - 20)
        max_height = max(180, self.preview.winfo_height() - 20)
        image.thumbnail((max_width, max_height))
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="")

    def clear(self):
        self.selection = None
        self.images = []
        if self.overlay is not None and self.overlay.winfo_exists():
            self.overlay.destroy()
        self.overlay = None
        self.preview_photo = None
        self.preview.configure(image="", text="截图预览会显示在这里")
        self.status.configure(text="已清空，请重新选择区域")

    def close(self):
        if self.overlay is not None and self.overlay.winfo_exists():
            self.overlay.destroy()
        self.destroy()


def main():
    ensure_capture_dir()
    ScreenshotTool().mainloop()


if __name__ == "__main__":
    main()
