import json
from pathlib import Path
from typing import Any

from PIL import Image


SECTORS = [
    ("front", "前", "front"),
    ("front_right", "右前", "front-right"),
    ("right", "右", "right"),
    ("back_right", "右後", "back-right"),
    ("back", "後", "back"),
    ("back_left", "左後", "back-left"),
    ("left", "左", "left"),
    ("front_left", "左前", "front-left"),
]


def crop_8_sectors_from_equirectangular(
    image_path: Path,
    output_node_dir: Path,
    project_id: str,
    job_id: str,
    node_id: str,
) -> list[dict[str, str]]:
    """
    equirectangular画像を横方向に8等分してsector画像を作る。
    初期MVPでは、横幅8等分の簡易分割とする。
    """
    output_node_dir.mkdir(parents=True, exist_ok=True)

    sector_infos: list[dict[str, str]] = []

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        width, height = image.size
        sector_width = width // 8

        for index, (sector_id, sector_label_ja, sector_label_en) in enumerate(SECTORS):
            left = index * sector_width

            if index == 7:
                right = width
            else:
                right = (index + 1) * sector_width

            crop = image.crop((left, 0, right, height))

            output_path = output_node_dir / f"{sector_id}.jpg"
            crop.save(output_path, quality=92)

            sector_infos.append(
                {
                    "sector": sector_id,
                    "sector_label_ja": sector_label_ja,
                    "sector_label_en": sector_label_en,
                    "image_path": str(output_path),
                    "image_url": f"/data/{project_id}/captures/{job_id}/sectors/{node_id}/{sector_id}.jpg",
                }
            )

    return sector_infos


def generate_sector_images_from_graph(
    project_id: str,
    job_id: str,
    graph: dict[str, Any],
    sectors_dir: Path,
) -> dict[str, Any]:
    """
    graph.json の nodes に含まれる keyframe_image を使って、
    各ノードごとに8方向sector画像を作る。
    """
    sectors_dir.mkdir(parents=True, exist_ok=True)

    images_by_node: dict[str, list[dict[str, str]]] = {}
    sector_image_count = 0

    for node in graph.get("nodes", []):
        node_id = str(node.get("node_id", ""))
        if node_id == "":
            continue

        media = node.get("media", {})
        keyframe_image = media.get("keyframe_image")

        if not keyframe_image:
            continue

        keyframe_path = Path(keyframe_image)

        if not keyframe_path.exists():
            continue

        output_node_dir = sectors_dir / node_id

        sector_infos = crop_8_sectors_from_equirectangular(
            image_path=keyframe_path,
            output_node_dir=output_node_dir,
            project_id=project_id,
            job_id=job_id,
            node_id=node_id,
        )

        images_by_node[node_id] = sector_infos
        sector_image_count += len(sector_infos)

    output = {
        "project_id": project_id,
        "image_type": "dummy_8_sector_images",
        "node_count": len(images_by_node),
        "sector_image_count": sector_image_count,
        "images_by_node": images_by_node,
    }

    manifest_path = sectors_dir / "sector_images.json"
    manifest_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "sectors_dir": str(sectors_dir),
        "manifest_path": str(manifest_path),
        "node_count": len(images_by_node),
        "sector_image_count": sector_image_count,
    }


def load_sector_images_for_node(
    sectors_dir: Path,
    node_id: str,
) -> list[dict[str, str]] | None:
    """
    指定ノードのsector画像一覧を読み込む。
    """
    manifest_path = sectors_dir / "sector_images.json"

    if not manifest_path.exists():
        return None

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    images_by_node = data.get("images_by_node", {})

    if node_id in images_by_node:
        return images_by_node[node_id]

    if node_id.startswith("N") and node_id[1:].isdigit():
        number = int(node_id[1:])
        candidates = [
            f"N{number:04d}",
            f"N{number:03d}",
            f"N{number}",
        ]

        for candidate in candidates:
            if candidate in images_by_node:
                return images_by_node[candidate]

    return []