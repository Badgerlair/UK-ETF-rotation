"""Create deterministic contact sheets for rendered-paper visual QA."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def natural_page_number(path: Path) -> int:
    return int(path.stem.rsplit("-", 1)[-1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pages_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--pages-per-sheet", type=int, default=8)
    args = parser.parse_args()

    pages = sorted(args.pages_dir.glob("page-*.png"), key=natural_page_number)
    if not pages:
        raise SystemExit(f"No rendered pages found in {args.pages_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=18)
    thumb_width = 520
    thumb_height = 735
    label_height = 34
    gutter = 24
    columns = 2
    rows = math.ceil(args.pages_per_sheet / columns)
    sheet_width = columns * thumb_width + (columns + 1) * gutter
    sheet_height = rows * (thumb_height + label_height) + (rows + 1) * gutter

    for sheet_index, start in enumerate(range(0, len(pages), args.pages_per_sheet), 1):
        batch = pages[start : start + args.pages_per_sheet]
        sheet = Image.new("RGB", (sheet_width, sheet_height), "#d8dde5")
        draw = ImageDraw.Draw(sheet)

        for offset, page_path in enumerate(batch):
            row, column = divmod(offset, columns)
            x = gutter + column * thumb_width
            y = gutter + row * (thumb_height + label_height)
            page_number = natural_page_number(page_path)

            with Image.open(page_path) as source:
                page = source.convert("RGB")
                page.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
                page_x = x + (thumb_width - page.width) // 2
                page_y = y + (thumb_height - page.height) // 2
                sheet.paste(page, (page_x, page_y))
                draw.rectangle(
                    (page_x, page_y, page_x + page.width - 1, page_y + page.height - 1),
                    outline="#546170",
                    width=2,
                )

            label = f"Page {page_number}"
            label_box = draw.textbbox((0, 0), label, font=font)
            label_width = label_box[2] - label_box[0]
            draw.text(
                (x + (thumb_width - label_width) // 2, y + thumb_height + 7),
                label,
                fill="#17202a",
                font=font,
            )

        first_page = natural_page_number(batch[0])
        last_page = natural_page_number(batch[-1])
        output = args.output_dir / f"contact-{sheet_index:02d}-pages-{first_page:02d}-{last_page:02d}.png"
        sheet.save(output, format="PNG", optimize=False, compress_level=9)

    print(f"Created {math.ceil(len(pages) / args.pages_per_sheet)} contact sheets for {len(pages)} pages.")


if __name__ == "__main__":
    main()
