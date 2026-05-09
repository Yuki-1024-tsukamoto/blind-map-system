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