from typing import Literal

from pydantic import BaseModel, Field


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

    graph_path: str | None = None
    nodes_path: str | None = None
    edges_path: str | None = None
    node_count: int | None = None
    edge_count: int | None = None

    descriptions_path: str | None = None
    sector_description_count: int | None = None

    sectors_dir: str | None = None
    sector_image_count: int | None = None

    ocr_results_path: str | None = None
    ocr_result_count: int | None = None

class ActiveJobResponse(BaseModel):
    project_id: str
    active_job_id: str | None = None
    job_status: JobStatusResponse | None = None
    message: str

class BasicPipelineStepResult(BaseModel):
    step: str
    status: str
    message: str


class BasicPipelineResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    steps: list[BasicPipelineStepResult]


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

class GenerateGraphResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    graph_path: str
    nodes_path: str
    edges_path: str
    node_count: int
    edge_count: int

class SectorText(BaseModel):
    brief: str
    detailed: str
    very_detailed: str


class SectorDescription(BaseModel):
    description_id: str
    node_id: str
    sector: str
    sector_label_ja: str
    sector_label_en: str
    ja: SectorText
    en: SectorText
    ocr_refs: list[str] = Field(default_factory=list)
    landmark_refs: list[str] = Field(default_factory=list)
    confidence: float
    review_required: bool

    version: int = 1
    approval_status: str | None = None
    edited_by: str | None = None
    edited_at: str | None = None
    notes: str | None = None


class GenerateDescriptionsResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    descriptions_path: str
    node_count: int
    sector_description_count: int


class NodeDescriptionsResponse(BaseModel):
    project_id: str
    node_id: str
    descriptions: list[SectorDescription]

class ReviewTasksResponse(BaseModel):
    project_id: str
    task_count: int
    tasks: list[SectorDescription]


class ReviewDescriptionRequest(BaseModel):
    approval_status: Literal["approved", "edited", "rejected"] = "approved"
    ja: SectorText | None = None
    en: SectorText | None = None
    notes: str | None = None
    edited_by: str = "local_user"


class ReviewDescriptionResponse(BaseModel):
    project_id: str
    description_id: str
    node_id: str
    sector: str
    approval_status: str
    review_required: bool
    version: int
    message: str

class SectorImageInfo(BaseModel):
    sector: str
    sector_label_ja: str
    sector_label_en: str
    image_path: str
    image_url: str


class GenerateSectorImagesResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    sectors_dir: str
    node_count: int
    sector_image_count: int


class NodeSectorImagesResponse(BaseModel):
    project_id: str
    node_id: str
    images: list[SectorImageInfo]

class OCRBBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class OCRResult(BaseModel):
    ocr_id: str
    node_id: str
    sector: str
    text: str
    language_hint: str
    bbox: OCRBBox
    confidence: float


class RunOCRResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    step: str
    message: str
    ocr_results_path: str
    node_count: int
    ocr_result_count: int


class NodeOCRResponse(BaseModel):
    project_id: str
    node_id: str
    results: list[OCRResult]

class GenerateAndSaveDescriptionResponse(BaseModel):
    project_id: str
    node_id: str
    sector: str
    description_id: str
    provider: str
    version: int
    confidence: float
    review_required: bool
    message: str
    updated_description: SectorDescription

class GenerateNodeDescriptionsResponse(BaseModel):
    project_id: str
    node_id: str
    provider: str
    updated_count: int
    failed_count: int
    updated_description_ids: list[str]
    failed_sectors: list[str]
    message: str

class LogEventRequest(BaseModel):
    session_id: str = "local_session"
    participant_id: str = "local_user"
    event_type: str
    node_id: str | None = None
    sector: str | None = None
    language: str | None = None
    granularity: str | None = None
    query: str | None = None
    route_start_node_id: str | None = None
    route_goal_node_id: str | None = None
    route_mode: str | None = None
    description_id: str | None = None
    metadata: dict | None = None


class LogEventResponse(BaseModel):
    project_id: str
    event_id: str
    message: str


class LogEventsResponse(BaseModel):
    project_id: str
    event_count: int
    events: list[dict]