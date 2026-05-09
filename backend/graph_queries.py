from collections import deque
from typing import Any


def search_graph_nodes(
    graph: dict[str, Any],
    query: str,
    language: str = "ja",
    limit: int = 50,
) -> list[dict[str, str]]:
    """
    生成済みgraph.jsonのnodesを検索する。
    今はOCRやlandmarkがないため、node_id, name, description_ja/en を検索対象にする。
    """
    normalized_query = query.strip().casefold()

    if normalized_query == "":
        return []

    results: list[dict[str, str]] = []

    for node in graph.get("nodes", []):
        node_id = str(node.get("node_id", ""))
        name = str(node.get("name", node_id))

        description_ja = str(node.get("description_ja", ""))
        description_en = str(node.get("description_en", ""))

        if language == "ja":
            matched_text = " ".join(
                [
                    node_id,
                    name,
                    description_ja,
                    description_en,
                ]
            )
        else:
            matched_text = " ".join(
                [
                    node_id,
                    name,
                    description_en,
                    description_ja,
                ]
            )

        if normalized_query in matched_text.casefold():
            results.append(
                {
                    "node_id": node_id,
                    "name": name,
                    "matched_text": matched_text,
                }
            )

        if len(results) >= limit:
            break

    return results


def normalize_node_id(node_id: str, existing_node_ids: set[str]) -> str:
    """
    N001 のような入力を N0001 に寄せるための補助関数。
    生成済みグラフでは N0001, N0002 の形式を使っている。
    """
    if node_id in existing_node_ids:
        return node_id

    if node_id.startswith("N") and node_id[1:].isdigit():
        number = int(node_id[1:])

        candidates = [
            f"N{number:04d}",
            f"N{number:03d}",
            f"N{number}",
        ]

        for candidate in candidates:
            if candidate in existing_node_ids:
                return candidate

    return node_id


def find_route_in_graph(
    graph: dict[str, Any],
    start_node_id: str,
    goal_node_id: str,
) -> list[str]:
    """
    生成済みgraph.jsonのedgesを使って、単純な幅優先探索で経路を探す。
    今は全エッジのコストを同じとして扱う。
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    existing_node_ids = {
        str(node.get("node_id"))
        for node in nodes
        if node.get("node_id") is not None
    }

    start = normalize_node_id(start_node_id, existing_node_ids)
    goal = normalize_node_id(goal_node_id, existing_node_ids)

    if start not in existing_node_ids:
        return []

    if goal not in existing_node_ids:
        return []

    if start == goal:
        return [start]

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in existing_node_ids}

    for edge in edges:
        from_node_id = edge.get("from_node_id")
        to_node_id = edge.get("to_node_id")

        if from_node_id is None or to_node_id is None:
            continue

        from_node_id = str(from_node_id)
        to_node_id = str(to_node_id)

        if from_node_id not in existing_node_ids:
            continue

        if to_node_id not in existing_node_ids:
            continue

        directionality = edge.get("directionality", "bidirectional")

        adjacency[from_node_id].append(to_node_id)

        if directionality == "bidirectional":
            adjacency[to_node_id].append(from_node_id)

    queue: deque[str] = deque([start])
    visited = {start}
    parent: dict[str, str | None] = {start: None}

    while queue:
        current = queue.popleft()

        if current == goal:
            break

        for next_node in adjacency.get(current, []):
            if next_node in visited:
                continue

            visited.add(next_node)
            parent[next_node] = current
            queue.append(next_node)

    if goal not in parent:
        return []

    route: list[str] = []
    current_node: str | None = goal

    while current_node is not None:
        route.append(current_node)
        current_node = parent[current_node]

    route.reverse()
    return route


def build_route_instructions(route: list[str]) -> tuple[list[str], list[str]]:
    """
    route配列から日英の簡易案内文を作る。
    """
    if len(route) == 0:
        return (
            ["指定されたノード間の経路が見つかりません。"],
            ["No route was found between the specified nodes."],
        )

    if len(route) == 1:
        return (
            ["出発ノードと目的ノードは同じです。"],
            ["The start node and goal node are the same."],
        )

    instructions_ja: list[str] = []
    instructions_en: list[str] = []

    for index in range(len(route) - 1):
        from_node_id = route[index]
        to_node_id = route[index + 1]

        instructions_ja.append(f"{from_node_id} から {to_node_id} へ進みます。")
        instructions_en.append(f"Move from {from_node_id} to {to_node_id}.")

    return instructions_ja, instructions_en