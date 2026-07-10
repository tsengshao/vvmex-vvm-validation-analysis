#!/usr/bin/env python3
"""Rotate every page of a PDF 90 degrees clockwise.

Requires: pypdf (install with ``python3 -m pip install pypdf``)
"""

import argparse
import os
import tempfile
from pathlib import Path


def rotate_pdf(input_path: Path, output_path: Path) -> None:
    """Rotate every page, safely replacing the output only when complete."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as error:
        raise RuntimeError(
            "This script requires pypdf. Install it with: "
            "python3 -m pip install pypdf"
        ) from error

    reader = PdfReader(input_path)
    if reader.is_encrypted:
        if not reader.decrypt(""):
            raise ValueError("The PDF is encrypted and requires a password.")

    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(90)
        writer.add_page(page)

    # A temporary file prevents a failed write from corrupting the source when
    # input_path and output_path are the same file.
    temp_file = tempfile.NamedTemporaryFile(
        mode="wb", dir=str(output_path.parent), prefix=".rotate_pdf_", delete=False
    )
    temp_path = Path(temp_file.name)
    try:
        with temp_file:
            writer.write(temp_file)
        os.replace(str(temp_path), str(output_path))
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rotate every page of a PDF 90 degrees clockwise."
    )
    parser.add_argument("input", type=Path, help="source PDF file")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="destination PDF (default: overwrite INPUT)",
    )
    args = parser.parse_args()

    input_path = args.input.expanduser()
    output_path = (args.output or input_path).expanduser()
    if not input_path.is_file():
        parser.error(f"input PDF does not exist: {input_path}")

    try:
        rotate_pdf(input_path, output_path)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Rotated PDF written to: {output_path}")


if __name__ == "__main__":
    main()
