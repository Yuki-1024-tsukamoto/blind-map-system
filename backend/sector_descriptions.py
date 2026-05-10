import json
from pathlib import Path
from typing import Any

from description_provider import create_description_provider


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


def load_sector_images_data(sectors_dir: Path) -> dict[str, Any] | None:
    manifest_path = sectors_dir / "sector_images.json"

    if not manifest_path.exists():
        return None

    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_ocr_data(ocr_dir: Path) -> dict[str, Any] | None:
    ocr_path = ocr_dir / "ocr_results.json"

    if not ocr_path.exists():
        return None

    return json.loads(ocr_path.read_text(encoding="utf-8"))


def get_sector_image_url(
    sector_images_data: dict[str, Any] | None,
    node_id: str,
    sector: str,
) -> str | None:
    if sector_images_data is None:
        return None

    images_by_node = sector_images_data.get("images_by_node", {})
    sector_images = images_by_node.get(node_id, [])

    for image in sector_images:
        if image.get("sector") == sector:
            return image.get("image_url")

    return None


def get_ocr_results_for_sector(
    ocr_data: dict[str, Any] | None,
    node_id: str,
    sector: str,
) -> list[dict[str, Any]]:
    if ocr_data is None:
        return []

    results_by_node = ocr_data.get("results_by_node", {})
    node_results = results_by_node.get(node_id, [])

    return [
        result
        for result in node_results
        if result.get("sector") == sector
    ]


def generate_dummy_sector_descriptions(
    project_id: str,
    graph: dict[str, Any],
    descriptions_dir: Path,
    sectors_dir: Path | None = None,
    ocr_dir: Path | None = None,
) -> dict[str, Any]:
    """
    graph.json の nodes に対して、8方向の説明を作る。
    現段階では DummyDescriptionProvider を使う。
    sector画像とOCR結果が存在すれば、それも説明文に反映する。
    """
    descriptions_dir.mkdir(parents=True, exist_ok=True)

    sector_images_data = (
        load_sector_images_data(sectors_dir)
        if sectors_dir is not None
        else None
    )
    ocr_data = (
        load_ocr_data(ocr_dir)
        if ocr_dir is not None
        else None
    )

    provider = create_description_provider()

    descriptions_by_node: dict[str, list[dict[str, Any]]] = {}
    sector_description_count = 0

    for node in graph.get("nodes", []):
        node_id = str(node.get("node_id", ""))
        if node_id == "":
            continue

        node_name = str(node.get("name", node_id))
        node_descriptions: list[dict[str, Any]] = []

        for sector_id, sector_label_ja, sector_label_en in SECTORS:
            description_id = f"DESC_{node_id}_{sector_id}"

            sector_image_url = get_sector_image_url(
                sector_images_data=sector_images_data,
                node_id=node_id,
                sector=sector_id,
            )

            ocr_results = get_ocr_results_for_sector(
                ocr_data=ocr_data,
                node_id=node_id,
                sector=sector_id,
            )

            generated = provider.generate_sector_description(
                node_id=node_id,
                node_name=node_name,
                sector=sector_id,
                sector_label_ja=sector_label_ja,
                sector_label_en=sector_label_en,
                sector_image_url=sector_image_url,
                ocr_results=ocr_results,
            )

            description = {
                "description_id": description_id,
                "node_id": node_id,
                "sector": sector_id,
                "sector_label_ja": sector_label_ja,
                "sector_label_en": sector_label_en,
                "ja": generated["ja"],
                "en": generated["en"],
                "ocr_refs": [
                    result.get("ocr_id", "")
                    for result in ocr_results
                    if result.get("ocr_id")
                ],
                "landmark_refs": [],
                "confidence": generated["confidence"],
                "review_required": generated["review_required"],
                "version": 1,
                "approval_status": None,
                "edited_by": None,
                "edited_at": None,
                "notes": None,
            }

            node_descriptions.append(description)
            sector_description_count += 1

        descriptions_by_node[node_id] = node_descriptions

    output = {
        "project_id": project_id,
        "description_type": "dummy_provider_sector_descriptions",
        "node_count": len(descriptions_by_node),
        "sector_description_count": sector_description_count,
        "descriptions_by_node": descriptions_by_node,
    }

    descriptions_path = descriptions_dir / "sector_descriptions.json"
    descriptions_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "descriptions_path": str(descriptions_path),
        "node_count": len(descriptions_by_node),
        "sector_description_count": sector_description_count,
    }


def normalize_node_id_for_descriptions(
    node_id: str,
    descriptions_by_node: dict[str, list[dict[str, Any]]],
) -> str:
    if node_id in descriptions_by_node:
        return node_id

    if node_id.startswith("N") and node_id[1:].isdigit():
        number = int(node_id[1:])
        candidates = [
            f"N{number:04d}",
            f"N{number:03d}",
            f"N{number}",
        ]

        for candidate in candidates:
            if candidate in descriptions_by_node:
                return candidate

    return node_id


def load_descriptions_for_node(
    descriptions_dir: Path,
    node_id: str,
) -> list[dict[str, Any]] | None:
    descriptions_path = descriptions_dir / "sector_descriptions.json"

    if not descriptions_path.exists():
        return None

    data = json.loads(descriptions_path.read_text(encoding="utf-8"))
    descriptions_by_node = data.get("descriptions_by_node", {})

    normalized_node_id = normalize_node_id_for_descriptions(
        node_id,
        descriptions_by_node,
    )

    return descriptions_by_node.get(normalized_node_id, [])