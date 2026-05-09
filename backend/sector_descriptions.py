import json
from pathlib import Path
from typing import Any


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


def generate_dummy_sector_descriptions(
    project_id: str,
    graph: dict[str, Any],
    descriptions_dir: Path,
) -> dict[str, Any]:
    """
    graph.json の nodes に対して、8方向の仮説明を作る。
    後でVLM/AI説明生成に差し替えるため、保存形式だけ先に整える。
    """
    descriptions_dir.mkdir(parents=True, exist_ok=True)

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

            description = {
                "description_id": description_id,
                "node_id": node_id,
                "sector": sector_id,
                "sector_label_ja": sector_label_ja,
                "sector_label_en": sector_label_en,
                "ja": {
                    "brief": f"{node_name}の{sector_label_ja}方向の仮説明です。",
                    "detailed": (
                        f"{node_name}の{sector_label_ja}方向を確認しています。"
                        "現段階では動画フレームから作った仮説明で、後でAI説明生成に置き換えます。"
                    ),
                    "very_detailed": (
                        f"{node_name}の{sector_label_ja}方向に関する詳細な仮説明です。"
                        "現在はOCR、ランドマーク検出、画像理解をまだ行っていないため、"
                        "この説明は方向別UIを確認するためのプレースホルダーです。"
                    ),
                },
                "en": {
                    "brief": f"Temporary description for the {sector_label_en} direction at {node_name}.",
                    "detailed": (
                        f"This is a temporary description for the {sector_label_en} direction at {node_name}. "
                        "It will later be replaced by AI-generated visual descriptions."
                    ),
                    "very_detailed": (
                        f"This is a detailed temporary description for the {sector_label_en} direction at {node_name}. "
                        "OCR, landmark detection, and image understanding are not yet applied."
                    ),
                },
                "ocr_refs": [],
                "landmark_refs": [],
                "confidence": 0.3,
                "review_required": True,
            }

            node_descriptions.append(description)
            sector_description_count += 1

        descriptions_by_node[node_id] = node_descriptions

    output = {
        "project_id": project_id,
        "description_type": "dummy_sector_descriptions",
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
    """
    N001 のような入力を N0001 に寄せる補助関数。
    """
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
    """
    指定ノードの8方向説明を読み込む。
    descriptions が未生成なら None を返す。
    """
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