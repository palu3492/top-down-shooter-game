from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Assets/map_10000_high_detail/map_preview_simplified_cartoon_tree_vehicle_free_v10.png"
OUT = ROOT / "Assets/map_10000_cartoon/layered/masks/source_resolution"

PROTOTYPES = {
    "grass": [(113, 120, 12), (73, 84, 11), (92, 94, 31), (120, 131, 14)],
    "asphalt": [(101, 99, 91), (86, 84, 79), (109, 106, 100), (133, 123, 111)],
    "dirt": [(150, 112, 43), (157, 135, 34), (146, 120, 33)],
    "sand": [(206, 163, 73), (197, 154, 60)],
    "water": [(9, 120, 177), (48, 132, 170), (72, 117, 146)],
    "swamp": [(61, 79, 62), (86, 100, 88), (117, 137, 112)],
    "exterior": [(39, 40, 22), (56, 73, 13), (73, 84, 11)],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB"), dtype=np.float32)
    h, w, _ = rgb.shape

    names = list(PROTOTYPES)
    distances = []
    for name in names:
        colors = np.asarray(PROTOTYPES[name], dtype=np.float32)
        delta = rgb[:, :, None, :] - colors[None, None, :, :]
        distances.append(np.min(np.sum(delta * delta, axis=3), axis=2))
    labels = np.argmin(np.stack(distances, axis=2), axis=2)

    # The perimeter rocks/buildings share gray tones with asphalt. Prevent the
    # border ring from leaking into the road mask; fixed structures are layered later.
    yy, xx = np.mgrid[:h, :w]
    border = (xx < 72) | (xx >= w - 72) | (yy < 72) | (yy >= h - 72)

    masks = {}
    for index, name in enumerate(names):
        mask = labels == index
        if name == "asphalt":
            mask &= ~border
        image = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L")
        image = image.filter(ImageFilter.MedianFilter(3))
        image.save(OUT / f"{name}_mask.png")
        masks[name] = np.asarray(image)

    palette = {
        "grass": (0, 200, 83),
        "asphalt": (66, 66, 66),
        "dirt": (184, 115, 51),
        "sand": (255, 209, 102),
        "water": (0, 140, 255),
        "swamp": (74, 124, 89),
        "exterior": (20, 61, 32),
    }
    preview = np.zeros((h, w, 3), dtype=np.uint8)
    for index, name in enumerate(names):
        preview[labels == index] = palette[name]
    preview[border & (labels == names.index("asphalt"))] = palette["exterior"]
    Image.fromarray(preview, mode="RGB").save(OUT / "surface_classification_preview.png")


if __name__ == "__main__":
    main()
