#!/usr/bin/env python3
"""Create a numbered structural-cleanup audit overlay for the rough map preview."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("Assets/map_10000_cartoon")
SOURCE = ROOT / "map_complete_rough_10000_v1_preview.png"
OUTPUT = ROOT / "cleanup" / "map_cleanup_structural_audit_v1.png"


REGIONS = [
    (1, "Northwest compound: sliced building/fence and row-boundary color shift", (120, 90, 610, 570)),
    (2, "Farm and gas station: fence/road/building continuity", (560, 125, 1290, 690)),
    (3, "Graveyard: duplicated debris, fence joins, and large color blocks", (145, 520, 690, 1040)),
    (4, "Roundabout: rebuild as one continuous road landmark", (650, 650, 1260, 1270)),
    (5, "Residential blocks: sliced houses, roads, paths, and fence openings", (1240, 480, 1770, 1210)),
    (6, "Warehouse: sliced roof/yard and road/fence alignment", (230, 1080, 820, 1510)),
    (7, "Hospital: sliced building/lot and perimeter road", (1170, 1050, 1660, 1510)),
    (8, "Campsite: tents, firepit, loop road, and fence continuity", (650, 1360, 1320, 1830)),
    (9, "Swamp and west perimeter: shoreline and boulder continuity", (0, 1360, 680, 2000)),
    (10, "River and southeast perimeter: sand/water/rock continuity", (1240, 1300, 2000, 2000)),
    (11, "South gate: gate halves, road alignment, and bottom barrier", (740, 1730, 1130, 2000)),
]


def font(size: int, bold: bool = False):
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def main() -> None:
    image = Image.open(SOURCE).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    width, height = image.size

    # Exact 8x8 production tile boundaries.
    for index in range(1, 8):
        x = round(width * index / 8)
        y = round(height * index / 8)
        draw.line((x, 0, x, height), fill=(255, 225, 0, 115), width=3)
        draw.line((0, y, width, y), fill=(255, 225, 0, 115), width=3)

    title_font = font(34, bold=True)
    number_font = font(28, bold=True)
    legend_font = font(21)

    draw.rounded_rectangle((20, 18, 760, 72), radius=12, fill=(10, 14, 18, 220), outline=(255, 255, 255, 180), width=2)
    draw.text((38, 27), "STRUCTURAL CLEANUP AUDIT — ROUGH MAP V1", font=title_font, fill="white")

    for number, _, box in REGIONS:
        left, top, right, bottom = box
        draw.rounded_rectangle(box, radius=18, fill=(255, 45, 35, 20), outline=(255, 55, 40, 220), width=6)
        badge = (left + 10, top + 10, left + 58, top + 58)
        draw.ellipse(badge, fill=(220, 30, 24, 245), outline="white", width=3)
        text = str(number)
        bounds = draw.textbbox((0, 0), text, font=number_font)
        tx = (badge[0] + badge[2] - (bounds[2] - bounds[0])) / 2
        ty = (badge[1] + badge[3] - (bounds[3] - bounds[1])) / 2 - 2
        draw.text((tx, ty), text, font=number_font, fill="white")

    legend_top = 85
    legend_left = 25
    legend_width = 780
    legend_height = 34 * len(REGIONS) + 24
    draw.rounded_rectangle(
        (legend_left, legend_top, legend_left + legend_width, legend_top + legend_height),
        radius=12,
        fill=(8, 12, 16, 205),
        outline=(255, 255, 255, 120),
        width=2,
    )
    for row, (number, label, _) in enumerate(REGIONS):
        y = legend_top + 12 + row * 34
        draw.text((legend_left + 14, y), f"{number}. {label}", font=legend_font, fill="white")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
