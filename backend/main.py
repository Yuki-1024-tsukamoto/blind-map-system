import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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

# -----------------------------
# ファイル保存先
# -----------------------------
# main.py は backend フォルダ内にあるため、
# parents[1] でプロジェクト直下 blind-map-system を指します。
# その下の data/projects にアップロード動画やジョブ情報を保存します。

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "projects"

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

# -----------------------------
# データ型の定義
# -----------------------------
# ここではまだDBは使わず、Pythonのリストと辞書でダミーデータを返します。
# 後でOpenSfMやOCRの結果を読み込むときも、この形式に近づけていきます。


class Project(BaseModel):
    project_id: str
    title: str
    facility_type: str
    status: str


class Node(BaseModel):
    node_id: str
    name: str
    floor_id: str
    x: float
    y: float
    description_ja: str
    description_en: str


class Edge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    direction: str


class MapResponse(BaseModel):
    project_id: str
    nodes: list[Node]
    edges: list[Edge]


class SearchRequest(BaseModel):
    query: str
    language: Literal["ja", "en"] = "ja"


class SearchResult(BaseModel):
    node_id: str
    name: str
    matched_text: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class RouteRequest(BaseModel):
    start_node_id: str
    goal_node_id: str
    mode: Literal["shortest", "landmark"] = "shortest"


class RouteResponse(BaseModel):
    start_node_id: str
    goal_node_id: str
    mode: str
    route: list[str]
    instructions_ja: list[str]
    instructions_en: list[str]

class UploadVideoResponse(BaseModel):
    project_id: str
    job_id: str
    filename: str
    saved_path: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    filename: str | None = None
    saved_path: str | None = None
    created_at: str
    updated_at: str
    error_message: str | None = None

# -----------------------------
# ダミーデータ
# -----------------------------
# まずは3つのノードだけで、探索・検索・経路の流れを確認します。
# 実動画処理が入ると、この部分が自動生成データに置き換わります。


DUMMY_PROJECTS = [
    Project(
        project_id="demo",
        title="Museum Demo",
        facility_type="exhibition",
        status="ready",
    )
]


DUMMY_NODES = [
    Node(
        node_id="N001",
        name="入口",
        floor_id="F1",
        x=0.0,
        y=0.0,
        description_ja="入口です。前方に受付があり、右側に展示室への通路があります。",
        description_en="This is the entrance. The reception desk is ahead, and the exhibition corridor is on the right.",
    ),
    Node(
        node_id="N002",
        name="受付",
        floor_id="F1",
        x=1.0,
        y=0.0,
        description_ja="受付カウンターです。案内表示とパンフレットがあります。",
        description_en="This is the reception counter. There are information signs and brochures.",
    ),
    Node(
        node_id="N003",
        name="展示室入口",
        floor_id="F1",
        x=2.0,
        y=0.0,
        description_ja="展示室の入口です。左側に展示パネル、右側に順路案内があります。",
        description_en="This is the entrance to the exhibition room. There is an exhibit panel on the left and route guidance on the right.",
    ),
]


DUMMY_EDGES = [
    Edge(
        edge_id="E001",
        from_node_id="N001",
        to_node_id="N002",
        direction="forward",
    ),
    Edge(
        edge_id="E002",
        from_node_id="N002",
        to_node_id="N003",
        direction="forward",
    ),
]

# -----------------------------
# ファイル・ジョブ管理の補助関数
# -----------------------------


def get_project_dir(project_id: str) -> Path:
    return DATA_ROOT / project_id


def get_raw_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "raw"


def get_jobs_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "jobs"


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

# -----------------------------
# API
# -----------------------------


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
    # ファイル名が空の場合は受け付けません。
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    # MVPでは動画ファイルだけを受け付けます。
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}",
        )

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    raw_dir = get_raw_dir(project_id)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 同名ファイルの衝突を避けるため、job_id を先頭に付けます。
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
        # 大きい動画でも一度にメモリへ載せないように、
        # shutil.copyfileobj でストリームとして保存します。
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