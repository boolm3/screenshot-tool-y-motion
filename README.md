# Y Motion Screenshot Stitcher

A Windows screenshot stitcher built around one rule:

```text
overlap = viewport height - measured Y displacement
```

The program measures the net vertical displacement between two adjacent screenshots, removes the already captured overlap, and appends the new content exactly once.

## 核心逻辑

假设截图区域高度为 `600px`：

```text
测得 Y=500 → 重合100px → 从当前图第101行开始追加
测得 Y=580 → 重合20px  → 从当前图第21行开始追加
测得 Y=30  → 重合570px → 从当前图第571行开始追加
```

每条接缝只执行：

```text
测量一次净Y
→ overlap = 高度 - Y
→ 裁切一次
→ 拼接一次
→ 质检一次
```

## Y测量

1. SIFT 特征匹配。
2. ORB 作为兼容兜底。
3. RANSAC 统计多数匹配点共同认可的 Y 位移。
4. 特征不足时使用密集像素位移作为兜底。

程序不使用单应矩阵或透视变换，因此不会拉伸网页文字。

## 使用

双击：

```text
run_screenshot_tool.bat
```

首次启动会自动安装缺失依赖。

1. 点击 `选择区域`。
2. 在真实屏幕预览上框选固定区域。
3. 点击 `区域截屏`。
4. 手动滚动网页或PDF，再次截图。
5. 重复截图，最后点击 `完成拼接`。

输出保存在 `captures`。

## 接缝报告

每次拼接会生成：

```text
stitched_时间.png
stitched_时间_motion.txt
stitched_时间_seam_01.png
```

报告包含每条缝的 Y、重合量、测量方法、RANSAC置信度和像素质检结果。
