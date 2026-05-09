import json
from pathlib import Path


def generate_dummy_graph_from_keyframes(
    project_id: str,
    keyframes_dir: Path,
    graph_dir: Path,
) -> dict:
    """
    代表フレームを仮ノードとして扱い、一本道の仮グラフを作る。
    OpenSfM統合前の中間実装。
    """
    if not keyframes_dir.exists():
        raise FileNotFoundError(f"Keyframes directory not found: {keyframes_dir}")

    keyframe_paths = sorted(keyframes_dir.glob("frame_*.jpg"))

    if len(keyframe_paths) == 0:
        raise FileNotFoundError(f"No keyframe images found in: {keyframes_dir}")

    graph_dir.mkdir(parents=True, exist_ok=True)

    nodes = []
    edges = []

    for index, keyframe_path in enumerate(keyframe_paths, start=1):
        node_id = f"N{index:04d}"

        node = {
            "node_id": node_id,
            "project_id": project_id,
            "floor_id": "F1",
            "pose": {
                "x": float(index - 1),
                "y": 0.0,
                "z": 0.0,
                "yaw_deg": 0.0,
            },
            "heading_reference": "video_order",
            "media": {
                "keyframe_image": str(keyframe_path),
            },
            "name": f"仮ノード {index}",
            "description_ja": f"動画から抽出された代表フレーム {index} に対応する仮ノードです。",
            "description_en": f"This is a temporary node corresponding to keyframe {index}.",
            "confidence": {
                "pose": 0.5,
                "ocr": 0.0,
                "description": 0.0,
            },
            "review_required": True,
        }
        nodes.append(node)

        if index > 1:
            previous_node_id = f"N{index - 1:04d}"
            edge_id = f"E{index - 1:04d}_{index:04d}"

            edge = {
                "edge_id": edge_id,
                "from_node_id": previous_node_id,
                "to_node_id": node_id,
                "edge_type": "walk",
                "directionality": "bidirectional",
                "cost_shortest": 1.0,
                "cost_landmark": 1.0,
            }
            edges.append(edge)

    graph = {
        "project_id": project_id,
        "graph_type": "dummy_keyframe_graph",
        "nodes": nodes,
        "edges": edges,
    }

    nodes_path = graph_dir / "nodes.json"
    edges_path = graph_dir / "edges.json"
    graph_path = graph_dir / "graph.json"

    nodes_path.write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    edges_path.write_text(
        json.dumps(edges, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "graph_path": str(graph_path),
        "nodes_path": str(nodes_path),
        "edges_path": str(edges_path),
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def load_graph(graph_dir: Path) -> dict | None:
    """
    graph.json が存在すれば読み込む。
    存在しなければ None を返す。
    """
    graph_path = graph_dir / "graph.json"

    if not graph_path.exists():
        return None

    return json.loads(graph_path.read_text(encoding="utf-8"))