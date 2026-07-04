#!/usr/bin/env python3
"""Create a side-by-side VVMex/VVM MP4 from matching PNG frames."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image


FRAME_RE = re.compile(r"^(.*?)(\d+)\.png$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop matching PNGs, place VVMex left and VVM right, and encode MP4."
    )
    parser.add_argument("--left-dir", type=Path, default=Path("figs_cwv_VVMex"))
    parser.add_argument("--right-dir", type=Path, default=Path("figs_cwv_VVM"))
    parser.add_argument("--output", type=Path, default=Path("cwv_VVMex_VVM_12fps.mp4"))
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument(
        "--ffmpeg",
        type=Path,
        default=Path("~/miniforge3/envs/py311/bin/ffmpeg").expanduser(),
    )
    parser.add_argument(
        "--crop-x",
        type=int,
        default=None,
        help="Horizontal crop start. By default it is detected from the first frame.",
    )
    parser.add_argument(
        "--crop-width",
        type=int,
        default=None,
        help="Horizontal crop width. By default it is detected from the first frame.",
    )
    parser.add_argument(
        "--margin", type=int, default=24, help="White margin retained around detected content."
    )
    parser.add_argument(
        "--white-threshold",
        type=int,
        default=250,
        help="RGB values at or above this value are treated as white.",
    )
    parser.add_argument("--crf", type=int, default=18, help="H.264 quality; lower is higher quality.")
    return parser.parse_args()


def numbered_pngs(directory: Path) -> dict[str, tuple[int, Path]]:
    frames: dict[str, tuple[int, Path]] = {}
    for path in directory.glob("*.png"):
        match = FRAME_RE.match(path.name)
        if match:
            frames[path.name] = (int(match.group(2)), path.resolve())
    return frames


def detect_horizontal_crop(path: Path, threshold: int, margin: int) -> tuple[int, int, int]:
    pixels = np.asarray(Image.open(path).convert("RGB"))
    height, image_width = pixels.shape[:2]
    nonwhite_columns = np.any(np.any(pixels < threshold, axis=2), axis=0)
    indices = np.flatnonzero(nonwhite_columns)
    if not len(indices):
        raise ValueError(f"No non-white content detected in {path}")

    x0 = max(0, int(indices[0]) - margin)
    x1 = min(image_width, int(indices[-1]) + 1 + margin)
    # yuv420p requires even dimensions. Expand when possible instead of discarding content.
    if x0 % 2:
        x0 -= 1
    if (x1 - x0) % 2:
        x1 = min(image_width, x1 + 1)
        if (x1 - x0) % 2:
            x0 += 1
    return x0, x1 - x0, height


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise SystemExit("--fps must be greater than zero")
    if not args.ffmpeg.is_file():
        raise SystemExit(f"ffmpeg not found: {args.ffmpeg}")
    if (args.crop_x is None) != (args.crop_width is None):
        raise SystemExit("Use --crop-x and --crop-width together")

    left = numbered_pngs(args.left_dir)
    right = numbered_pngs(args.right_dir)
    common_names = sorted(left.keys() & right.keys(), key=lambda name: (left[name][0], name))
    if not common_names:
        raise SystemExit("No matching numbered PNG filenames were found")

    first_left = left[common_names[0]][1]
    first_right = right[common_names[0]][1]
    with Image.open(first_left) as image:
        left_size = image.size
    with Image.open(first_right) as image:
        right_size = image.size
    if left_size != right_size:
        raise SystemExit(f"First-frame sizes differ: {left_size} versus {right_size}")

    if args.crop_x is None:
        crop_x, crop_width, height = detect_horizontal_crop(
            first_left, args.white_threshold, args.margin
        )
    else:
        crop_x, crop_width = args.crop_x, args.crop_width
        height = left_size[1]
    if crop_x < 0 or crop_width <= 0 or crop_x + crop_width > left_size[0]:
        raise SystemExit("Requested crop lies outside the image")
    if crop_width % 2 or height % 2:
        raise SystemExit("Crop width and image height must be even for yuv420p")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = args.output.resolve()
    with tempfile.TemporaryDirectory(prefix="cwv_movie_") as temp_name:
        temp = Path(temp_name)
        left_temp = temp / "left"
        right_temp = temp / "right"
        left_temp.mkdir()
        right_temp.mkdir()
        for index, name in enumerate(common_names, start=1):
            os.symlink(left[name][1], left_temp / f"frame_{index:06d}.png")
            os.symlink(right[name][1], right_temp / f"frame_{index:06d}.png")

        filter_graph = (
            f"[0:v]crop={crop_width}:{height}:{crop_x}:0[left];"
            f"[1:v]crop={crop_width}:{height}:{crop_x}:0[right];"
            "[left][right]hstack=inputs=2,format=yuv420p[out]"
        )
        command = [
            str(args.ffmpeg),
            "-y",
            "-framerate",
            str(args.fps),
            "-i",
            str(left_temp / "frame_%06d.png"),
            "-framerate",
            str(args.fps),
            "-i",
            str(right_temp / "frame_%06d.png"),
            "-filter_complex",
            filter_graph,
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(args.crf),
            "-tag:v",
            "avc1",
            "-movflags",
            "+faststart",
            "-an",
            str(output),
        ]
        print(f"Frames: {len(common_names)} matching pairs")
        print(f"Crop: x={crop_x}, width={crop_width}, height={height}")
        print(f"Output: {crop_width * 2}x{height} at {args.fps:g} fps")
        subprocess.run(command, check=True)

    extra_left = len(left.keys() - right.keys())
    extra_right = len(right.keys() - left.keys())
    print(f"Created {output}")
    if extra_left or extra_right:
        print(f"Skipped unmatched frames: left={extra_left}, right={extra_right}")


if __name__ == "__main__":
    main()
