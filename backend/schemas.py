from typing import Literal

from pydantic import BaseModel


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

    derived_dir: str | None = None
    keyframes_dir: str | None = None
    ocr_master_path: str | None = None
    slam_erp_path: str | None = None
    keyframe_count: int | None = None
    preprocess_marker: str | None = None


class PreprocessResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    derived_dir: str
    keyframes_dir: str
    ocr_master_path: str | None = None
    slam_erp_path: str | None = None
    keyframe_count: int = 0


class VideoInfoResponse(BaseModel):
    project_id: str
    job_id: str
    path: str
    filename: str
    width: int | None = None
    height: int | None = None
    codec_name: str | None = None
    avg_frame_rate: str
    duration_sec: float | None = None
    size_bytes: int | None = None