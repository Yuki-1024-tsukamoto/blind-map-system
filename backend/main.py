import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from dummy_data import DUMMY_EDGES, DUMMY_NODES, DUMMY_PROJECTS
from schemas import (
    JobStatusResponse,
    MapResponse,
    PreprocessResponse,
    Project,
    RouteRequest,
    RouteResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    UploadVideoResponse,
    VideoInfoResponse,
)
from storage import (
    ALLOWED_VIDEO_EXTENSIONS,
    get_derived_dir,
    get_keyframes_dir,
    get_raw_dir,
    load_job_status,
    save_job_status,
    update_job_status,
)
from video_processing import get_video_info

app = FastAPI(
    title="Blind Map System API",
    description="視覚障碍者向けノードベース探索・経路訓練システムの研究用MVP API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "backend is running",
    }


@app.get("/projects", response_model=list[Project])
def get_projects():
    return DUMMY_PROJECTS


@app.post("/projects", response_model=Project)
def create_project(project: Project):
    # 今は保存処理はしません。
    # 受け取ったprojectをそのまま返すだけです。
    # 後でDBまたはJSON保存に置き換えます。
    return project


@app.get("/projects/{project_id}/map", response_model=MapResponse)
def get_project_map(project_id: str):
    return MapResponse(
        project_id=project_id,
        nodes=DUMMY_NODES,
        edges=DUMMY_EDGES,
    )


@app.post("/projects/{project_id}/search", response_model=SearchResponse)
def search_project(project_id: str, request: SearchRequest):
    results: list[SearchResult] = []

    for node in DUMMY_NODES:
        if request.language == "ja":
            target_text = f"{node.name} {node.description_ja}"
        else:
            target_text = f"{node.name} {node.description_en}"

        if request.query.lower() in target_text.lower():
            results.append(
                SearchResult(
                    node_id=node.node_id,
                    name=node.name,
                    matched_text=target_text,
                )
            )

    return SearchResponse(
        query=request.query,
        results=results,
    )


@app.post("/projects/{project_id}/route", response_model=RouteResponse)
def get_route(project_id: str, request: RouteRequest):
    # 今は非常に単純なダミールートです。
    # N001 -> N002 -> N003 の一本道だけを想定します。
    all_route = ["N001", "N002", "N003"]

    try:
        start_index = all_route.index(request.start_node_id)
        goal_index = all_route.index(request.goal_node_id)
    except ValueError:
        return RouteResponse(
            start_node_id=request.start_node_id,
            goal_node_id=request.goal_node_id,
            mode=request.mode,
            route=[],
            instructions_ja=["指定されたノードが見つかりません。"],
            instructions_en=["The specified node was not found."],
        )

    if start_index <= goal_index:
        route = all_route[start_index : goal_index + 1]
    else:
        route = list(reversed(all_route[goal_index : start_index + 1]))

    return RouteResponse(
        start_node_id=request.start_node_id,
        goal_node_id=request.goal_node_id,
        mode=request.mode,
        route=route,
        instructions_ja=[
            "入口から受付へ進みます。",
            "受付から展示室入口へ進みます。",
        ],
        instructions_en=[
            "Move from the entrance to the reception desk.",
            "Move from the reception desk to the exhibition entrance.",
        ],
    )


@app.post("/projects/{project_id}/upload-video", response_model=UploadVideoResponse)
async def upload_video(project_id: str, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}",
        )

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    raw_dir = get_raw_dir(project_id)
    raw_dir.mkdir(parents=True, exist_ok=True)

    saved_filename = f"{job_id}_{original_filename}"
    saved_path = raw_dir / saved_filename

    now = datetime.now(timezone.utc).isoformat()

    job_data = {
        "project_id": project_id,
        "job_id": job_id,
        "status": "uploaded",
        "step": "upload_video",
        "filename": original_filename,
        "saved_path": str(saved_path),
        "created_at": now,
        "updated_at": now,
        "error_message": None,
    }

    try:
        with saved_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        save_job_status(project_id, job_data)

    except Exception as error:
        job_data["status"] = "failed"
        job_data["error_message"] = str(error)
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_job_status(project_id, job_data)

        raise HTTPException(status_code=500, detail="Failed to save uploaded video")

    finally:
        file.file.close()

    return UploadVideoResponse(
        project_id=project_id,
        job_id=job_id,
        filename=original_filename,
        saved_path=str(saved_path),
        status="uploaded",
        message="Video uploaded successfully",
    )


@app.get("/projects/{project_id}/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)
    return JobStatusResponse(**job_data)

@app.get(
    "/projects/{project_id}/jobs/{job_id}/video-info",
    response_model=VideoInfoResponse,
)
def get_uploaded_video_info(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    saved_path = job_data.get("saved_path")
    if not saved_path:
        raise HTTPException(status_code=400, detail="Uploaded video path is missing")

    info = get_video_info(Path(saved_path))

    return VideoInfoResponse(
        project_id=project_id,
        job_id=job_id,
        **info,
    )

@app.post(
    "/projects/{project_id}/jobs/{job_id}/preprocess",
    response_model=PreprocessResponse,
)
def preprocess_video(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in ["uploaded", "failed", "preprocessed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be preprocessed from status: {job_data['status']}",
        )

    saved_path = job_data.get("saved_path")
    if not saved_path:
        raise HTTPException(status_code=400, detail="Uploaded video path is missing")

    input_video_path = Path(saved_path)
    if not input_video_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded video file not found")

    derived_dir = get_derived_dir(project_id)
    keyframes_dir = get_keyframes_dir(project_id)

    derived_dir.mkdir(parents=True, exist_ok=True)
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    update_job_status(
        project_id,
        job_id,
        {
            "status": "preprocessing",
            "step": "preprocess_video",
            "error_message": None,
        },
    )

    # 今回はまだFFmpeg処理は行わない。
    # 後続ステップで、ここに ocr_master.mp4 / slam_erp.mp4 / keyframes 生成を追加する。
    marker_path = derived_dir / f"{job_id}_preprocess_placeholder.txt"
    marker_path.write_text(
        "Preprocess placeholder completed.\n"
        "FFmpeg processing will be added in the next step.\n",
        encoding="utf-8",
    )

    update_job_status(
        project_id,
        job_id,
        {
            "status": "preprocessed",
            "step": "preprocess_video",
            "derived_dir": str(derived_dir),
            "keyframes_dir": str(keyframes_dir),
            "preprocess_marker": str(marker_path),
            "error_message": None,
        },
    )

    return PreprocessResponse(
        project_id=project_id,
        job_id=job_id,
        status="preprocessed",
        step="preprocess_video",
        message="Preprocess placeholder completed",
        derived_dir=str(derived_dir),
        keyframes_dir=str(keyframes_dir),
    )