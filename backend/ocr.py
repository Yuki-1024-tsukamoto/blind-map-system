import json
from pathlib import Path
from typing import Any


class OCRProvider:
    """
    OCRProvider の抽象的な親クラス。
    今後 Google Cloud Vision OCR に差し替えるときも、
    run_ocr_for_sector_image() の返り値形式を揃える。
    """

    def run_ocr_for_sector_image(
        self,
        node_id: str,
        sector: str,
        image_path: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class DummyOCRProvider(OCRProvider):
    """
    ダミーOCR。
    実際に画像を読まず、sectorごとに仮のOCR結果を返す。
    OCR保存形式とUI確認のための初期実装。
    """

    def run_ocr_for_sector_image(
        self,
        node_id: str,
        sector: str,
        image_path: str,
    ) -> list[dict[str, Any]]:
        # すべてのsectorにOCR結果を出すと量が多いので、
        # MVP確認用に front / right / left だけに仮テキストを出す。
        dummy_text_by_sector = {
            "front": "案内",
            "right": "SHOP",
            "left": "入口",
        }

        if sector not in dummy_text_by_sector:
            return []

        return [
            {
                "ocr_id": f"OCR_{node_id}_{sector}_001",
                "node_id": node_id,
                "sector": sector,
                "text": dummy_text_by_sector[sector],
                "language_hint": "ja" if sector in ["front", "left"] else "en",
                "bbox": {
                    "x": 100,
                    "y": 80,
                    "width": 240,
                    "height": 80,
                },
                "confidence": 0.75,
            }
        ]


def load_sector_images_manifest(sectors_dir: Path) -> dict[str, Any]:
    manifest_path = sectors_dir / "sector_images.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"sector_images.json not found: {manifest_path}"
        )

    return json.loads(manifest_path.read_text(encoding="utf-8"))


def run_dummy_ocr_for_project(
    project_id: str,
    sectors_dir: Path,
    ocr_dir: Path,
) -> dict[str, Any]:
    """
    sector_images.json を読み、各sector画像に対して DummyOCRProvider を実行する。
    """
    ocr_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_sector_images_manifest(sectors_dir)
    images_by_node = manifest.get("images_by_node", {})

    provider = DummyOCRProvider()

    results_by_node: dict[str, list[dict[str, Any]]] = {}
    ocr_result_count = 0

    for node_id, sector_images in images_by_node.items():
        node_results: list[dict[str, Any]] = []

        for sector_image in sector_images:
            sector = sector_image.get("sector", "")
            image_path = sector_image.get("image_path", "")

            ocr_results = provider.run_ocr_for_sector_image(
                node_id=node_id,
                sector=sector,
                image_path=image_path,
            )

            node_results.extend(ocr_results)
            ocr_result_count += len(ocr_results)

        results_by_node[node_id] = node_results

    output = {
        "project_id": project_id,
        "ocr_type": "dummy_ocr",
        "node_count": len(results_by_node),
        "ocr_result_count": ocr_result_count,
        "results_by_node": results_by_node,
    }

    ocr_results_path = ocr_dir / "ocr_results.json"
    ocr_results_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "ocr_results_path": str(ocr_results_path),
        "node_count": len(results_by_node),
        "ocr_result_count": ocr_result_count,
    }


def load_ocr_results_for_node(
    ocr_dir: Path,
    node_id: str,
) -> list[dict[str, Any]] | None:
    ocr_results_path = ocr_dir / "ocr_results.json"

    if not ocr_results_path.exists():
        return None

    data = json.loads(ocr_results_path.read_text(encoding="utf-8"))
    results_by_node = data.get("results_by_node", {})

    if node_id in results_by_node:
        return results_by_node[node_id]

    if node_id.startswith("N") and node_id[1:].isdigit():
        number = int(node_id[1:])
        candidates = [
            f"N{number:04d}",
            f"N{number:03d}",
            f"N{number}",
        ]

        for candidate in candidates:
            if candidate in results_by_node:
                return results_by_node[candidate]

    return []