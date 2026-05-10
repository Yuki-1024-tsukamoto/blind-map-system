import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dummy_data import DUMMY_EDGES, DUMMY_NODES, DUMMY_PROJECTS

from schemas import (
    GenerateAndSaveDescriptionResponse,
    GenerateDescriptionsResponse,
    GenerateGraphResponse,
    GenerateSectorImagesResponse,
    JobStatusResponse,
    MapResponse,
    NodeDescriptionsResponse,
    NodeOCRResponse,
    NodeSectorImagesResponse,
    OCRResult,
    PreprocessResponse,
    Project,
    ReviewDescriptionRequest,
    ReviewDescriptionResponse,
    ReviewTasksResponse,
    RouteRequest,
    RouteResponse,
    RunOCRResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SectorDescription,
    SectorImageInfo,
    UploadVideoResponse,
    VideoInfoResponse,
)
from storage import (
    ALLOWED_VIDEO_EXTENSIONS,
    DATA_ROOT,
    get_derived_dir,
    get_descriptions_dir,
    get_graph_dir,
    get_keyframes_dir,
    get_ocr_dir,
    get_raw_dir,
    get_sectors_dir,
    load_job_status,
    save_job_status,
    update_job_status,
)
from sector_images import (
    generate_sector_images_from_graph,
    load_sector_images_for_node,
)
from video_processing import get_video_info, preprocess_video_files

from graph_generation import generate_dummy_graph_from_keyframes, load_graph

from graph_queries import (
    build_route_instructions,
    find_route_in_graph,
    search_graph_nodes,
    search_ocr_results,
)

from sector_descriptions import (
    generate_dummy_sector_descriptions,
    load_descriptions_for_node,
)

from review import (
    list_review_tasks,
    update_description_from_ai_generation,
    update_description_review,
)

from ocr import (
    load_all_ocr_results,
    load_ocr_results_for_node,
    run_dummy_ocr_for_project,
)

from description_provider import OpenAIDescriptionProvider, load_prompt_text
from settings import get_openai_api_key, get_openai_description_model

from description_provider import (
    GeminiDescriptionProvider,
    OpenAIDescriptionProvider,
    load_prompt_text,
)
from settings import (
    get_gemini_api_key,
    get_gemini_description_model,
    get_openai_api_key,
    get_openai_description_model,
)

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
app.mount(
    "/data",
    StaticFiles(directory=str(DATA_ROOT)),
    name="data",
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


@app.get("/projects/{project_id}/map")
def get_project_map(project_id: str):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is not None:
        return generated_graph

    return MapResponse(
        project_id=project_id,
        nodes=DUMMY_NODES,
        edges=DUMMY_EDGES,
    )


@app.post("/projects/{project_id}/search", response_model=SearchResponse)
def search_project(project_id: str, request: SearchRequest):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    combined_results: list[SearchResult] = []

    # 1. graph.json の node_id / name / description を検索
    if generated_graph is not None:
        graph_results = search_graph_nodes(
            graph=generated_graph,
            query=request.query,
            language=request.language,
        )

        combined_results.extend(
            [
                SearchResult(
                    node_id=result["node_id"],
                    name=result["name"],
                    matched_text=result["matched_text"],
                )
                for result in graph_results
            ]
        )

    # 2. ocr_results.json の OCR text を検索
    ocr_dir = get_ocr_dir(project_id)
    ocr_results_by_node = load_all_ocr_results(ocr_dir)

    if ocr_results_by_node is not None:
        ocr_results = search_ocr_results(
            ocr_results_by_node=ocr_results_by_node,
            query=request.query,
        )

        existing_keys = {
            f"{result.node_id}:{result.matched_text}"
            for result in combined_results
        }

        for result in ocr_results:
            key = f"{result['node_id']}:{result['matched_text']}"
            if key in existing_keys:
                continue

            combined_results.append(
                SearchResult(
                    node_id=result["node_id"],
                    name=result["name"],
                    matched_text=result["matched_text"],
                )
            )

    # 3. graph.json がない場合だけ、旧3ノードダミーデータを検索
    if generated_graph is None:
        for node in DUMMY_NODES:
            if request.language == "ja":
                target_text = f"{node.name} {node.description_ja}"
            else:
                target_text = f"{node.name} {node.description_en}"

            if request.query.lower() in target_text.lower():
                combined_results.append(
                    SearchResult(
                        node_id=node.node_id,
                        name=node.name,
                        matched_text=target_text,
                    )
                )

    return SearchResponse(
        query=request.query,
        results=combined_results,
    )

@app.post("/projects/{project_id}/route", response_model=RouteResponse)
def get_route(project_id: str, request: RouteRequest):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is not None:
        route = find_route_in_graph(
            graph=generated_graph,
            start_node_id=request.start_node_id,
            goal_node_id=request.goal_node_id,
        )

        instructions_ja, instructions_en = build_route_instructions(route)

        return RouteResponse(
            start_node_id=route[0] if route else request.start_node_id,
            goal_node_id=route[-1] if route else request.goal_node_id,
            mode=request.mode,
            route=route,
            instructions_ja=instructions_ja,
            instructions_en=instructions_en,
        )

    # graph.json がまだない場合は、従来の3ノードダミールートを使う。
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

@app.post(
    "/projects/{project_id}/jobs/{job_id}/preprocess",
    response_model=PreprocessResponse,
)
def preprocess_video(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in [
        "uploaded",
        "failed",
        "preprocessed",
        "graph_generated",
        "dummy_descriptions_generated",
        "generating_graph",
        "generating_descriptions",
    ]:
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

    update_job_status(
        project_id,
        job_id,
        {
            "status": "preprocessing",
            "step": "preprocess_video",
            "error_message": None,
        },
    )

    try:
        preprocess_result = preprocess_video_files(
            input_video_path=input_video_path,
            derived_dir=derived_dir,
            keyframes_dir=keyframes_dir,
            interval_sec=1,
        )

        update_job_status(
            project_id,
            job_id,
            {
                "status": "preprocessed",
                "step": "preprocess_video",
                "derived_dir": str(derived_dir),
                "keyframes_dir": str(keyframes_dir),
                "ocr_master_path": preprocess_result["ocr_master_path"],
                "slam_erp_path": preprocess_result["slam_erp_path"],
                "keyframe_count": preprocess_result["keyframe_count"],
                "error_message": None,
            },
        )

        return PreprocessResponse(
            project_id=project_id,
            job_id=job_id,
            status="preprocessed",
            step="preprocess_video",
            message="Video preprocessing completed",
            derived_dir=str(derived_dir),
            keyframes_dir=str(keyframes_dir),
            ocr_master_path=preprocess_result["ocr_master_path"],
            slam_erp_path=preprocess_result["slam_erp_path"],
            keyframe_count=preprocess_result["keyframe_count"],
        )

    except Exception as error:
        update_job_status(
            project_id,
            job_id,
            {
                "status": "failed",
                "step": "preprocess_video",
                "error_message": str(error),
            },
        )
        raise



@app.post(
    "/projects/{project_id}/jobs/{job_id}/generate-dummy-graph",
    response_model=GenerateGraphResponse,
)
def generate_dummy_graph(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in [
        "preprocessed",
        "graph_generated",
        "dummy_descriptions_generated",
        "failed",
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot generate graph from status: {job_data['status']}",
        )

    keyframes_dir = get_keyframes_dir(project_id)
    graph_dir = get_graph_dir(project_id)

    update_job_status(
        project_id,
        job_id,
        {
            "status": "generating_graph",
            "step": "generate_dummy_graph",
            "error_message": None,
        },
    )

    try:
        graph_result = generate_dummy_graph_from_keyframes(
            project_id=project_id,
            keyframes_dir=keyframes_dir,
            graph_dir=graph_dir,
        )

        update_job_status(
            project_id,
            job_id,
            {
                "status": "graph_generated",
                "step": "generate_dummy_graph",
                "graph_path": graph_result["graph_path"],
                "nodes_path": graph_result["nodes_path"],
                "edges_path": graph_result["edges_path"],
                "node_count": graph_result["node_count"],
                "edge_count": graph_result["edge_count"],
                "error_message": None,
            },
        )

        return GenerateGraphResponse(
            project_id=project_id,
            job_id=job_id,
            status="graph_generated",
            step="generate_dummy_graph",
            message="Dummy graph generated from keyframes",
            graph_path=graph_result["graph_path"],
            nodes_path=graph_result["nodes_path"],
            edges_path=graph_result["edges_path"],
            node_count=graph_result["node_count"],
            edge_count=graph_result["edge_count"],
        )

    except Exception as error:
        update_job_status(
            project_id,
            job_id,
            {
                "status": "failed",
                "step": "generate_dummy_graph",
                "error_message": str(error),
            },
        )
        raise

@app.post(
    "/projects/{project_id}/jobs/{job_id}/generate-dummy-descriptions",
    response_model=GenerateDescriptionsResponse,
)
def generate_dummy_descriptions(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in [
        "graph_generated",
        "dummy_descriptions_generated",
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot generate descriptions from status: {job_data['status']}",
        )

    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is None:
        raise HTTPException(status_code=404, detail="Generated graph not found")

    descriptions_dir = get_descriptions_dir(project_id)

    update_job_status(
        project_id,
        job_id,
        {
            "status": "generating_descriptions",
            "step": "generate_dummy_descriptions",
            "error_message": None,
        },
    )

    try:
        result = generate_dummy_sector_descriptions(
            project_id=project_id,
            graph=generated_graph,
            descriptions_dir=descriptions_dir,
            sectors_dir=get_sectors_dir(project_id),
            ocr_dir=get_ocr_dir(project_id),
        )

        update_job_status(
            project_id,
            job_id,
            {
                "status": "dummy_descriptions_generated",
                "step": "generate_dummy_descriptions",
                "descriptions_path": result["descriptions_path"],
                "sector_description_count": result["sector_description_count"],
                "error_message": None,
            },
        )

        return GenerateDescriptionsResponse(
            project_id=project_id,
            job_id=job_id,
            status="dummy_descriptions_generated",
            step="generate_dummy_descriptions",
            message="Dummy 8-sector descriptions generated",
            descriptions_path=result["descriptions_path"],
            node_count=result["node_count"],
            sector_description_count=result["sector_description_count"],
        )

    except Exception as error:
        update_job_status(
            project_id,
            job_id,
            {
                "status": "failed",
                "step": "generate_dummy_descriptions",
                "error_message": str(error),
            },
        )
        raise


@app.get(
    "/projects/{project_id}/nodes/{node_id}/descriptions",
    response_model=NodeDescriptionsResponse,
)
def get_node_descriptions(project_id: str, node_id: str):
    descriptions_dir = get_descriptions_dir(project_id)
    descriptions = load_descriptions_for_node(descriptions_dir, node_id)

    if descriptions is None:
        raise HTTPException(
            status_code=404,
            detail="Descriptions have not been generated yet",
        )

    if len(descriptions) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Descriptions for node not found: {node_id}",
        )

    return NodeDescriptionsResponse(
        project_id=project_id,
        node_id=node_id,
        descriptions=[
            SectorDescription(**description)
            for description in descriptions
        ],
    )

@app.get(
    "/projects/{project_id}/review/tasks",
    response_model=ReviewTasksResponse,
)
def get_review_tasks(project_id: str, limit: int = 50):
    descriptions_dir = get_descriptions_dir(project_id)
    tasks = list_review_tasks(
        descriptions_dir=descriptions_dir,
        limit=limit,
    )

    return ReviewTasksResponse(
        project_id=project_id,
        task_count=len(tasks),
        tasks=[
            SectorDescription(**task)
            for task in tasks
        ],
    )


@app.post(
    "/projects/{project_id}/review/description/{description_id}",
    response_model=ReviewDescriptionResponse,
)
def review_description(
    project_id: str,
    description_id: str,
    request: ReviewDescriptionRequest,
):
    descriptions_dir = get_descriptions_dir(project_id)

    updated_description = update_description_review(
        descriptions_dir=descriptions_dir,
        description_id=description_id,
        review_update=request.model_dump(
            mode="json",
            exclude_none=True,
        ),
    )

    return ReviewDescriptionResponse(
        project_id=project_id,
        description_id=description_id,
        node_id=updated_description["node_id"],
        sector=updated_description["sector"],
        approval_status=updated_description["approval_status"],
        review_required=updated_description["review_required"],
        version=updated_description["version"],
        message="Description review updated",
    )

@app.post(
    "/projects/{project_id}/jobs/{job_id}/generate-sector-images",
    response_model=GenerateSectorImagesResponse,
)
def generate_sector_images(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in [
        "graph_generated",
        "dummy_descriptions_generated",
        "sector_images_generated",
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot generate sector images from status: {job_data['status']}",
        )

    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is None:
        raise HTTPException(status_code=404, detail="Generated graph not found")

    sectors_dir = get_sectors_dir(project_id)

    update_job_status(
        project_id,
        job_id,
        {
            "status": "generating_sector_images",
            "step": "generate_sector_images",
            "error_message": None,
        },
    )

    try:
        result = generate_sector_images_from_graph(
            project_id=project_id,
            graph=generated_graph,
            sectors_dir=sectors_dir,
        )

        update_job_status(
            project_id,
            job_id,
            {
                "status": "sector_images_generated",
                "step": "generate_sector_images",
                "sectors_dir": result["sectors_dir"],
                "sector_image_count": result["sector_image_count"],
                "error_message": None,
            },
        )

        return GenerateSectorImagesResponse(
            project_id=project_id,
            job_id=job_id,
            status="sector_images_generated",
            step="generate_sector_images",
            message="8-sector images generated",
            sectors_dir=result["sectors_dir"],
            node_count=result["node_count"],
            sector_image_count=result["sector_image_count"],
        )

    except Exception as error:
        update_job_status(
            project_id,
            job_id,
            {
                "status": "failed",
                "step": "generate_sector_images",
                "error_message": str(error),
            },
        )
        raise


@app.get(
    "/projects/{project_id}/nodes/{node_id}/sector-images",
    response_model=NodeSectorImagesResponse,
)
def get_node_sector_images(project_id: str, node_id: str):
    sectors_dir = get_sectors_dir(project_id)
    images = load_sector_images_for_node(sectors_dir, node_id)

    if images is None:
        raise HTTPException(
            status_code=404,
            detail="Sector images have not been generated yet",
        )

    if len(images) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Sector images for node not found: {node_id}",
        )

    return NodeSectorImagesResponse(
        project_id=project_id,
        node_id=node_id,
        images=[
            SectorImageInfo(**image)
            for image in images
        ],
    )

@app.post(
    "/projects/{project_id}/jobs/{job_id}/run-dummy-ocr",
    response_model=RunOCRResponse,
)
def run_dummy_ocr(project_id: str, job_id: str):
    job_data = load_job_status(project_id, job_id)

    if job_data["status"] not in [
        "sector_images_generated",
        "dummy_ocr_completed",
        "dummy_descriptions_generated",
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot run OCR from status: {job_data['status']}",
        )

    sectors_dir = get_sectors_dir(project_id)
    ocr_dir = get_ocr_dir(project_id)

    update_job_status(
        project_id,
        job_id,
        {
            "status": "running_dummy_ocr",
            "step": "run_dummy_ocr",
            "error_message": None,
        },
    )

    try:
        result = run_dummy_ocr_for_project(
            project_id=project_id,
            sectors_dir=sectors_dir,
            ocr_dir=ocr_dir,
        )

        update_job_status(
            project_id,
            job_id,
            {
                "status": "dummy_ocr_completed",
                "step": "run_dummy_ocr",
                "ocr_results_path": result["ocr_results_path"],
                "ocr_result_count": result["ocr_result_count"],
                "error_message": None,
            },
        )

        return RunOCRResponse(
            project_id=project_id,
            job_id=job_id,
            status="dummy_ocr_completed",
            step="run_dummy_ocr",
            message="Dummy OCR completed",
            ocr_results_path=result["ocr_results_path"],
            node_count=result["node_count"],
            ocr_result_count=result["ocr_result_count"],
        )

    except Exception as error:
        update_job_status(
            project_id,
            job_id,
            {
                "status": "failed",
                "step": "run_dummy_ocr",
                "error_message": str(error),
            },
        )
        raise


@app.get(
    "/projects/{project_id}/nodes/{node_id}/ocr",
    response_model=NodeOCRResponse,
)
def get_node_ocr_results(project_id: str, node_id: str):
    ocr_dir = get_ocr_dir(project_id)
    results = load_ocr_results_for_node(ocr_dir, node_id)

    if results is None:
        raise HTTPException(
            status_code=404,
            detail="OCR results have not been generated yet",
        )

    return NodeOCRResponse(
        project_id=project_id,
        node_id=node_id,
        results=[
            OCRResult(**result)
            for result in results
        ],
    )

@app.post(
    "/projects/{project_id}/nodes/{node_id}/sectors/{sector}/generate-openai-description"
)
def generate_openai_description_for_one_sector(
    project_id: str,
    node_id: str,
    sector: str,
):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is None:
        raise HTTPException(status_code=404, detail="Generated graph not found")

    node = None
    for candidate in generated_graph.get("nodes", []):
        if candidate.get("node_id") == node_id:
            node = candidate
            break

    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    sectors_dir = get_sectors_dir(project_id)
    sector_images = load_sector_images_for_node(sectors_dir, node_id)

    if sector_images is None:
        raise HTTPException(status_code=404, detail="Sector images not generated")

    target_sector_image = None
    for image in sector_images:
        if image.get("sector") == sector:
            target_sector_image = image
            break

    if target_sector_image is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sector image not found: {node_id}/{sector}",
        )

    ocr_dir = get_ocr_dir(project_id)
    ocr_results = load_ocr_results_for_node(ocr_dir, node_id) or []
    ocr_results_for_sector = [
        result
        for result in ocr_results
        if result.get("sector") == sector
    ]

    sector_label_ja = target_sector_image.get("sector_label_ja", sector)
    sector_label_en = target_sector_image.get("sector_label_en", sector)

    provider = OpenAIDescriptionProvider(
        api_key=get_openai_api_key(),
        prompt_text=load_prompt_text(),
        model=get_openai_description_model(),
    )

    result = provider.generate_sector_description(
        node_id=node_id,
        node_name=node.get("name", node_id),
        sector=sector,
        sector_label_ja=sector_label_ja,
        sector_label_en=sector_label_en,
        sector_image_url=target_sector_image.get("image_url"),
        sector_image_path=target_sector_image.get("image_path"),
        ocr_results=ocr_results_for_sector,
    )

    return {
        "project_id": project_id,
        "node_id": node_id,
        "sector": sector,
        "provider": "openai",
        "result": result,
    }

@app.post(
    "/projects/{project_id}/nodes/{node_id}/sectors/{sector}/generate-gemini-description"
)
def generate_gemini_description_for_one_sector(
    project_id: str,
    node_id: str,
    sector: str,
):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is None:
        raise HTTPException(status_code=404, detail="Generated graph not found")

    node = None
    for candidate in generated_graph.get("nodes", []):
        if candidate.get("node_id") == node_id:
            node = candidate
            break

    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    sectors_dir = get_sectors_dir(project_id)
    sector_images = load_sector_images_for_node(sectors_dir, node_id)

    if sector_images is None:
        raise HTTPException(status_code=404, detail="Sector images not generated")

    target_sector_image = None
    for image in sector_images:
        if image.get("sector") == sector:
            target_sector_image = image
            break

    if target_sector_image is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sector image not found: {node_id}/{sector}",
        )

    ocr_dir = get_ocr_dir(project_id)
    ocr_results = load_ocr_results_for_node(ocr_dir, node_id) or []
    ocr_results_for_sector = [
        result for result in ocr_results if result.get("sector") == sector
    ]

    provider = GeminiDescriptionProvider(
        api_key=get_gemini_api_key(),
        prompt_text=load_prompt_text(),
        model=get_gemini_description_model(),
    )

    result = provider.generate_sector_description(
        node_id=node_id,
        node_name=node.get("name", node_id),
        sector=sector,
        sector_label_ja=target_sector_image.get("sector_label_ja", sector),
        sector_label_en=target_sector_image.get("sector_label_en", sector),
        sector_image_url=target_sector_image.get("image_url"),
        sector_image_path=target_sector_image.get("image_path"),
        ocr_results=ocr_results_for_sector,
    )

    return {
        "project_id": project_id,
        "node_id": node_id,
        "sector": sector,
        "provider": "gemini",
        "result": result,
    }

@app.post(
    "/projects/{project_id}/nodes/{node_id}/sectors/{sector}/generate-and-save-gemini-description",
    response_model=GenerateAndSaveDescriptionResponse,
)
def generate_and_save_gemini_description_for_one_sector(
    project_id: str,
    node_id: str,
    sector: str,
):
    graph_dir = get_graph_dir(project_id)
    generated_graph = load_graph(graph_dir)

    if generated_graph is None:
        raise HTTPException(status_code=404, detail="Generated graph not found")

    node = None
    for candidate in generated_graph.get("nodes", []):
        if candidate.get("node_id") == node_id:
            node = candidate
            break

    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    sectors_dir = get_sectors_dir(project_id)
    sector_images = load_sector_images_for_node(sectors_dir, node_id)

    if sector_images is None:
        raise HTTPException(status_code=404, detail="Sector images not generated")

    target_sector_image = None
    for image in sector_images:
        if image.get("sector") == sector:
            target_sector_image = image
            break

    if target_sector_image is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sector image not found: {node_id}/{sector}",
        )

    ocr_dir = get_ocr_dir(project_id)
    ocr_results = load_ocr_results_for_node(ocr_dir, node_id) or []
    ocr_results_for_sector = [
        result for result in ocr_results if result.get("sector") == sector
    ]

    provider = GeminiDescriptionProvider(
        api_key=get_gemini_api_key(),
        prompt_text=load_prompt_text(),
        model=get_gemini_description_model(),
    )

    generated_result = provider.generate_sector_description(
        node_id=node_id,
        node_name=node.get("name", node_id),
        sector=sector,
        sector_label_ja=target_sector_image.get("sector_label_ja", sector),
        sector_label_en=target_sector_image.get("sector_label_en", sector),
        sector_image_url=target_sector_image.get("image_url"),
        sector_image_path=target_sector_image.get("image_path"),
        ocr_results=ocr_results_for_sector,
    )

    description_id = f"DESC_{node_id}_{sector}"
    descriptions_dir = get_descriptions_dir(project_id)

    updated_description = update_description_from_ai_generation(
        descriptions_dir=descriptions_dir,
        description_id=description_id,
        generated_result=generated_result,
        provider_name="gemini",
    )

    return GenerateAndSaveDescriptionResponse(
        project_id=project_id,
        node_id=node_id,
        sector=sector,
        description_id=description_id,
        provider="gemini",
        version=updated_description["version"],
        confidence=updated_description["confidence"],
        review_required=updated_description["review_required"],
        message="Gemini description generated and saved",
        updated_description=SectorDescription(**updated_description),
    )