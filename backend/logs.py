import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_events_log_path(logs_dir: Path) -> Path:
    return logs_dir / "events.jsonl"


def append_log_event(
    logs_dir: Path,
    project_id: str,
    event_data: dict[str, Any],
) -> dict[str, Any]:
    """
    1操作を JSONL 形式で追記する。
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "project_id": project_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event_data,
    }

    log_path = get_events_log_path(logs_dir)

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def read_log_events(
    logs_dir: Path,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    events.jsonl の末尾から最大 limit 件を返す。
    """
    log_path = get_events_log_path(logs_dir)

    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").splitlines()
    selected_lines = lines[-limit:]

    events: list[dict[str, Any]] = []

    for line in selected_lines:
        if not line.strip():
            continue

        events.append(json.loads(line))

    return events