import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException


def get_sector_descriptions_path(descriptions_dir: Path) -> Path:
    return descriptions_dir / "sector_descriptions.json"


def get_review_log_path(descriptions_dir: Path) -> Path:
    return descriptions_dir / "review_log.jsonl"


def load_sector_descriptions_data(descriptions_dir: Path) -> dict[str, Any]:
    descriptions_path = get_sector_descriptions_path(descriptions_dir)

    if not descriptions_path.exists():
        raise HTTPException(
            status_code=404,
            detail="sector_descriptions.json not found. Generate descriptions first.",
        )

    return json.loads(descriptions_path.read_text(encoding="utf-8"))


def save_sector_descriptions_data(
    descriptions_dir: Path,
    data: dict[str, Any],
) -> None:
    descriptions_dir.mkdir(parents=True, exist_ok=True)
    descriptions_path = get_sector_descriptions_path(descriptions_dir)

    descriptions_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_review_log(
    descriptions_dir: Path,
    log_event: dict[str, Any],
) -> None:
    descriptions_dir.mkdir(parents=True, exist_ok=True)
    review_log_path = get_review_log_path(descriptions_dir)

    with review_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_event, ensure_ascii=False) + "\n")


def list_review_tasks(
    descriptions_dir: Path,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    review_required=true のdescriptionだけを返す。
    """
    data = load_sector_descriptions_data(descriptions_dir)
    descriptions_by_node = data.get("descriptions_by_node", {})

    tasks: list[dict[str, Any]] = []

    for node_descriptions in descriptions_by_node.values():
        for description in node_descriptions:
            if description.get("review_required") is True:
                tasks.append(description)

            if len(tasks) >= limit:
                return tasks

    return tasks


def update_description_review(
    descriptions_dir: Path,
    description_id: str,
    review_update: dict[str, Any],
) -> dict[str, Any]:
    """
    description_id 単位で承認・編集・差し戻しを行う。
    """
    data = load_sector_descriptions_data(descriptions_dir)
    descriptions_by_node = data.get("descriptions_by_node", {})

    approval_status = review_update.get("approval_status", "approved")
    edited_by = review_update.get("edited_by", "local_user")
    notes = review_update.get("notes")
    edited_at = datetime.now(timezone.utc).isoformat()

    for node_id, node_descriptions in descriptions_by_node.items():
        for index, description in enumerate(node_descriptions):
            if description.get("description_id") != description_id:
                continue

            old_description = deepcopy(description)

            current_version = int(description.get("version", 1))
            description["version"] = current_version + 1
            description["approval_status"] = approval_status
            description["edited_by"] = edited_by
            description["edited_at"] = edited_at
            description["notes"] = notes

            if approval_status == "approved":
                description["review_required"] = False

            elif approval_status == "edited":
                if review_update.get("ja") is not None:
                    description["ja"] = review_update["ja"]

                if review_update.get("en") is not None:
                    description["en"] = review_update["en"]

                description["review_required"] = False

            elif approval_status == "rejected":
                description["review_required"] = True

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported approval_status: {approval_status}",
                )

            node_descriptions[index] = description
            save_sector_descriptions_data(descriptions_dir, data)

            append_review_log(
                descriptions_dir,
                {
                    "event_type": "review_description",
                    "description_id": description_id,
                    "node_id": node_id,
                    "sector": description.get("sector"),
                    "approval_status": approval_status,
                    "edited_by": edited_by,
                    "edited_at": edited_at,
                    "notes": notes,
                    "old_description": old_description,
                    "new_description": description,
                },
            )

            return description

    raise HTTPException(
        status_code=404,
        detail=f"Description not found: {description_id}",
    )

def update_description_from_ai_generation(
    descriptions_dir: Path,
    description_id: str,
    generated_result: dict[str, Any],
    provider_name: str,
) -> dict[str, Any]:
    """
    Gemini/OpenAIなどのAI生成結果で、既存descriptionを上書きする。
    review編集とは分けて扱う。
    """
    data = load_sector_descriptions_data(descriptions_dir)
    descriptions_by_node = data.get("descriptions_by_node", {})

    updated_at = datetime.now(timezone.utc).isoformat()

    for node_id, node_descriptions in descriptions_by_node.items():
        for index, description in enumerate(node_descriptions):
            if description.get("description_id") != description_id:
                continue

            old_description = deepcopy(description)

            current_version = int(description.get("version", 1))

            description["ja"] = generated_result["ja"]
            description["en"] = generated_result["en"]
            description["landmarks"] = generated_result.get("landmarks", [])
            description["confidence"] = float(generated_result.get("confidence", 0.0))
            description["review_required"] = True

            description["version"] = current_version + 1
            description["approval_status"] = "ai_generated"
            description["edited_by"] = provider_name
            description["edited_at"] = updated_at
            description["notes"] = f"Generated by {provider_name}"

            node_descriptions[index] = description
            save_sector_descriptions_data(descriptions_dir, data)

            append_review_log(
                descriptions_dir,
                {
                    "event_type": "ai_generate_description",
                    "description_id": description_id,
                    "node_id": node_id,
                    "sector": description.get("sector"),
                    "provider": provider_name,
                    "edited_at": updated_at,
                    "old_description": old_description,
                    "new_description": description,
                },
            )

            return description

    raise HTTPException(
        status_code=404,
        detail=f"Description not found: {description_id}",
    )