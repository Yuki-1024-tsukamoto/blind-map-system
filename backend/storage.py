import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "projects"

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def get_project_dir(project_id: str) -> Path:
    return DATA_ROOT / project_id


def get_raw_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "raw"


def get_jobs_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "jobs"


def get_derived_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "derived"


def get_keyframes_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "frames" / "keyframes"

def get_graph_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "graph"

def get_descriptions_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "descriptions"

def get_sectors_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "sectors"

def get_ocr_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "ocr"


def save_job_status(project_id: str, job_data: dict) -> None:
    jobs_dir = get_jobs_dir(project_id)
    jobs_dir.mkdir(parents=True, exist_ok=True)

    job_path = jobs_dir / f"{job_data['job_id']}.json"

    with job_path.open("w", encoding="utf-8") as f:
        json.dump(job_data, f, ensure_ascii=False, indent=2)


def load_job_status(project_id: str, job_id: str) -> dict:
    job_path = get_jobs_dir(project_id) / f"{job_id}.json"

    if not job_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with job_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def update_job_status(project_id: str, job_id: str, updates: dict) -> dict:
    job_data = load_job_status(project_id, job_id)

    job_data.update(updates)
    job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    save_job_status(project_id, job_data)

    return job_data

def get_logs_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "logs"

def get_captures_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "captures"


def get_job_capture_dir(project_id: str, job_id: str) -> Path:
    return get_captures_dir(project_id) / job_id


def get_job_raw_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "raw"


def get_job_derived_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "derived"


def get_job_keyframes_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "frames" / "keyframes"


def get_job_graph_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "graph"


def get_job_sectors_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "sectors"


def get_job_ocr_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "ocr"


def get_job_descriptions_dir(project_id: str, job_id: str) -> Path:
    return get_job_capture_dir(project_id, job_id) / "descriptions"


def get_active_job_path(project_id: str) -> Path:
    return get_project_dir(project_id) / "active_job.json"


def set_active_job_id(project_id: str, job_id: str) -> None:
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    active_job_path = get_active_job_path(project_id)

    with active_job_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "project_id": project_id,
                "active_job_id": job_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def get_active_job_id(project_id: str) -> str | None:
    active_job_path = get_active_job_path(project_id)

    if not active_job_path.exists():
        return None

    with active_job_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("active_job_id")