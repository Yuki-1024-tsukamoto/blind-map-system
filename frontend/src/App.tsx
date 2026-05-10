import { useEffect, useState } from "react";
import "./App.css";

type PageName =
  | "projects"
  | "upload"
  | "explore"
  | "search"
  | "route"
  | "review";

type Project = {
  project_id: string;
  title: string;
  facility_type: string;
  status: string;
};

type Pose = {
  x: number;
  y: number;
  z?: number;
  yaw_deg?: number;
};

type NodeMedia = {
  keyframe_image?: string;
  keyframe_url?: string;
  erp_image?: string;
};

type NodeConfidence = {
  pose?: number;
  ocr?: number;
  description?: number;
};

type MapNode = {
  node_id: string;
  project_id?: string;
  name?: string;
  floor_id?: string;

  // 旧ダミーデータ用
  x?: number;
  y?: number;

  // 生成済みgraph.json用
  pose?: Pose;
  heading_reference?: string;
  media?: NodeMedia;
  confidence?: NodeConfidence;
  review_required?: boolean;

  description_ja?: string;
  description_en?: string;
};

type MapEdge = {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;

  // 旧ダミーデータ用
  direction?: string;

  // 生成済みgraph.json用
  edge_type?: string;
  directionality?: string;
  cost_shortest?: number;
  cost_landmark?: number;
};

type MapResponse = {
  project_id: string;
  graph_type?: string;
  nodes: MapNode[];
  edges: MapEdge[];
};

type SearchResult = {
  node_id: string;
  name: string;
  matched_text: string;
};

type SearchResponse = {
  query: string;
  results: SearchResult[];
};

type RouteResponse = {
  start_node_id: string;
  goal_node_id: string;
  mode: string;
  route: string[];
  instructions_ja: string[];
  instructions_en: string[];
};

type UploadVideoResponse = {
  project_id: string;
  job_id: string;
  filename: string;
  saved_path: string;
  status: string;
  message: string;
};

type JobStatusResponse = {
  project_id: string;
  job_id: string;
  status: string;
  step: string;
  filename: string | null;
  saved_path: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;

  derived_dir?: string | null;
  keyframes_dir?: string | null;
  ocr_master_path?: string | null;
  slam_erp_path?: string | null;
  keyframe_count?: number | null;
  preprocess_marker?: string | null;

  graph_path?: string | null;
  nodes_path?: string | null;
  edges_path?: string | null;
  node_count?: number | null;
  edge_count?: number | null;
  descriptions_path?: string | null;
  sector_description_count?: number | null;
};

type PreprocessResponse = {
  project_id: string;
  job_id: string;
  status: string;
  step: string;
  message: string;
  derived_dir: string;
  keyframes_dir: string;
  ocr_master_path: string | null;
  slam_erp_path: string | null;
  keyframe_count: number;
};

type GenerateGraphResponse = {
  project_id: string;
  job_id: string;
  status: string;
  step: string;
  message: string;
  graph_path: string;
  nodes_path: string;
  edges_path: string;
  node_count: number;
  edge_count: number;
};

type GenerateNodeDescriptionsResponse = {
  project_id: string;
  node_id: string;
  provider: string;
  updated_count: number;
  failed_count: number;
  updated_description_ids: string[];
  failed_sectors: string[];
  message: string;
};

type SectorText = {
  brief: string;
  detailed: string;
  very_detailed: string;
};

type SectorDescription = {
  description_id: string;
  node_id: string;
  sector: string;
  sector_label_ja: string;
  sector_label_en: string;
  ja: SectorText;
  en: SectorText;
  ocr_refs: string[];
  landmark_refs: string[];
  confidence: number;
  review_required: boolean;

  version?: number;
  approval_status?: string | null;
  edited_by?: string | null;
  edited_at?: string | null;
  notes?: string | null;
};

type SectorImageInfo = {
  sector: string;
  sector_label_ja: string;
  sector_label_en: string;
  image_path: string;
  image_url: string;
};

type NodeSectorImagesResponse = {
  project_id: string;
  node_id: string;
  images: SectorImageInfo[];
};

type OCRBBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type OCRResult = {
  ocr_id: string;
  node_id: string;
  sector: string;
  text: string;
  language_hint: string;
  bbox: OCRBBox;
  confidence: number;
};

type NodeOCRResponse = {
  project_id: string;
  node_id: string;
  results: OCRResult[];
};

type ReviewTasksResponse = {
  project_id: string;
  task_count: number;
  tasks: SectorDescription[];
};

type ReviewDescriptionResponse = {
  project_id: string;
  description_id: string;
  node_id: string;
  sector: string;
  approval_status: string;
  review_required: boolean;
  version: number;
  message: string;
};

type NodeDescriptionsResponse = {
  project_id: string;
  node_id: string;
  descriptions: SectorDescription[];
};

type GenerateDescriptionsResponse = {
  project_id: string;
  job_id: string;
  status: string;
  step: string;
  message: string;
  descriptions_path: string;
  node_count: number;
  sector_description_count: number;
};


const API_BASE_URL = "http://127.0.0.1:8000";

function buildMediaUrl(pathOrUrl?: string): string | null {
  if (!pathOrUrl) {
    return null;
  }

  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }

  if (pathOrUrl.startsWith("/")) {
    return `${API_BASE_URL}${pathOrUrl}`;
  }

  return null;
}

const pageLabels: Record<PageName, string> = {
  projects: "プロジェクト一覧",
  upload: "アップロード",
  explore: "探索",
  search: "検索",
  route: "経路訓練",
  review: "レビュー",
};

function App() {
  const [currentPage, setCurrentPage] = useState<PageName>("projects");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null
  );
  const [mapData, setMapData] = useState<MapResponse | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>("受付");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const [startNodeId, setStartNodeId] = useState<string>("N0001");
  const [goalNodeId, setGoalNodeId] = useState<string>("N0010");
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] =
    useState<UploadVideoResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [preprocessResult, setPreprocessResult] =
    useState<PreprocessResponse | null>(null);
  const [graphGenerationResult, setGraphGenerationResult] =
    useState<GenerateGraphResponse | null>(null);
  const [descriptionGenerationResult, setDescriptionGenerationResult] =
    useState<GenerateDescriptionsResponse | null>(null);
  const [geminiNodeGenerationResult, setGeminiNodeGenerationResult] =
    useState<GenerateNodeDescriptionsResponse | null>(null);
  const [loadingGeminiNodeGeneration, setLoadingGeminiNodeGeneration] =
    useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeDescriptions, setNodeDescriptions] = useState<SectorDescription[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("front");
  const [nodeSectorImages, setNodeSectorImages] = useState<SectorImageInfo[]>([]);
  const [loadingNodeSectorImages, setLoadingNodeSectorImages] =
    useState<boolean>(false);
  const [nodeOCRResults, setNodeOCRResults] = useState<OCRResult[]>([]);
  const [loadingNodeOCRResults, setLoadingNodeOCRResults] =
    useState<boolean>(false);
  const [reviewTasks, setReviewTasks] = useState<SectorDescription[]>([]);
  const [loadingReviewTasks, setLoadingReviewTasks] = useState<boolean>(false);
  const [updatingReviewDescriptionId, setUpdatingReviewDescriptionId] =
    useState<string | null>(null);
  const [reviewMessage, setReviewMessage] = useState<string>("");
  const [loadingProjects, setLoadingProjects] = useState<boolean>(false);
  const [loadingMap, setLoadingMap] = useState<boolean>(false);
  const [loadingSearch, setLoadingSearch] = useState<boolean>(false);
  const [loadingRoute, setLoadingRoute] = useState<boolean>(false);
  const [loadingUpload, setLoadingUpload] = useState<boolean>(false);
  const [loadingJobStatus, setLoadingJobStatus] = useState<boolean>(false);
  const [loadingPreprocess, setLoadingPreprocess] = useState<boolean>(false);
  const [loadingGraphGeneration, setLoadingGraphGeneration] =
    useState<boolean>(false);
  const [loadingDescriptionGeneration, setLoadingDescriptionGeneration] =
    useState<boolean>(false);
  const [loadingNodeDescriptions, setLoadingNodeDescriptions] =
    useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    async function fetchProjects() {
      try {
        setLoadingProjects(true);
        setErrorMessage("");

        const response = await fetch(`${API_BASE_URL}/projects`);

        if (!response.ok) {
          throw new Error("プロジェクト一覧の取得に失敗しました。");
        }

        const data: Project[] = await response.json();
        setProjects(data);

        if (data.length > 0) {
          setSelectedProjectId(data[0].project_id);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "不明なエラーが発生しました。"
        );
      } finally {
        setLoadingProjects(false);
      }
    }

    fetchProjects();
  }, []);

  async function fetchMap(projectId: string) {
    try {
      setLoadingMap(true);
      setErrorMessage("");

      const response = await fetch(`${API_BASE_URL}/projects/${projectId}/map`);

      if (!response.ok) {
        throw new Error("地図データの取得に失敗しました。");
      }

      const data: MapResponse = await response.json();
      setMapData(data);

      if (data.nodes.length > 0) {
        setCurrentNodeId(data.nodes[0].node_id);
      }

      setCurrentPage("explore");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingMap(false);
    }
  }

  async function searchProject() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    try {
      setLoadingSearch(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/search`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: searchQuery,
            language: "ja",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("検索に失敗しました。");
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data.results);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingSearch(false);
    }
  }

  async function calculateRoute() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    try {
      setLoadingRoute(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/route`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            start_node_id: startNodeId,
            goal_node_id: goalNodeId,
            mode: "shortest",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("経路検索に失敗しました。");
      }

      const data: RouteResponse = await response.json();
      setRouteResult(data);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingRoute(false);
    }
  }

  async function uploadVideo() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    if (!selectedFile) {
      setErrorMessage("アップロードする動画ファイルを選択してください。");
      return;
    }

    try {
      setLoadingUpload(true);
      setErrorMessage("");
      setUploadResult(null);
      setJobStatus(null);
      setPreprocessResult(null);
      setGraphGenerationResult(null);
      setNodeSectorImages([]);
      setNodeOCRResults([]);

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/upload-video`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`動画アップロードに失敗しました: ${errorText}`);
      }

      const data: UploadVideoResponse = await response.json();
      setUploadResult(data);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingUpload(false);
    }
  }

  async function fetchJobStatus() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    if (!uploadResult) {
      setErrorMessage("先に動画をアップロードしてください。");
      return;
    }

    try {
      setLoadingJobStatus(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/jobs/${uploadResult.job_id}`
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`ジョブ状態の取得に失敗しました: ${errorText}`);
      }

      const data: JobStatusResponse = await response.json();
      setJobStatus(data);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingJobStatus(false);
    }
  }

  async function startPreprocess() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    if (!uploadResult) {
      setErrorMessage("先に動画をアップロードしてください。");
      return;
    }

    try {
      setLoadingPreprocess(true);
      setErrorMessage("");
      setPreprocessResult(null);
      setGraphGenerationResult(null);
      setDescriptionGenerationResult(null);
      setNodeDescriptions([]);
      setSelectedNodeId(null);

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/jobs/${uploadResult.job_id}/preprocess`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`前処理の開始に失敗しました: ${errorText}`);
      }

      const data: PreprocessResponse = await response.json();
      setPreprocessResult(data);
      await fetchJobStatus();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingPreprocess(false);
    }
  }

  async function generateDummyGraph() {
    if (!selectedProjectId) {
      setErrorMessage("プロジェクトが選択されていません。");
      return;
    }

    if (!uploadResult) {
      setErrorMessage("先に動画をアップロードしてください。");
      return;
    }

    try {
      setLoadingGraphGeneration(true);
      setErrorMessage("");
      setGraphGenerationResult(null);

      const response = await fetch(
        `${API_BASE_URL}/projects/${selectedProjectId}/jobs/${uploadResult.job_id}/generate-dummy-graph`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`仮グラフ生成に失敗しました: ${errorText}`);
      }

      const data: GenerateGraphResponse = await response.json();
      setGraphGenerationResult(data);
      await fetchJobStatus();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "不明なエラーが発生しました。"
      );
    } finally {
      setLoadingGraphGeneration(false);
    }
  }

  async function generateDummyDescriptions() {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  if (!uploadResult) {
    setErrorMessage("先に動画をアップロードしてください。");
    return;
  }

  try {
    setLoadingDescriptionGeneration(true);
    setErrorMessage("");
    setDescriptionGenerationResult(null);

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/jobs/${uploadResult.job_id}/generate-dummy-descriptions`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`8方向説明生成に失敗しました: ${errorText}`);
    }

    const data: GenerateDescriptionsResponse = await response.json();
    setDescriptionGenerationResult(data);
    await fetchJobStatus();
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingDescriptionGeneration(false);
  }
}
async function fetchNodeDescriptions(nodeId: string) {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  try {
    setLoadingNodeDescriptions(true);
    setErrorMessage("");
    setSelectedNodeId(nodeId);
    setNodeDescriptions([]);
    setSelectedSector("front");

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/nodes/${nodeId}/descriptions`
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`ノード説明の取得に失敗しました: ${errorText}`);
    }

    const data: NodeDescriptionsResponse = await response.json();
    setNodeDescriptions(data.descriptions);
    await fetchNodeSectorImages(nodeId);
    await fetchNodeOCRResults(nodeId);
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingNodeDescriptions(false);
  }
}
async function fetchNodeSectorImages(nodeId: string) {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  try {
    setLoadingNodeSectorImages(true);
    setErrorMessage("");
    setNodeSectorImages([]);

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/nodes/${nodeId}/sector-images`
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`sector画像の取得に失敗しました: ${errorText}`);
    }

    const data: NodeSectorImagesResponse = await response.json();
    setNodeSectorImages(data.images);
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingNodeSectorImages(false);
  }
}
async function fetchNodeOCRResults(nodeId: string) {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  try {
    setLoadingNodeOCRResults(true);
    setErrorMessage("");
    setNodeOCRResults([]);

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/nodes/${nodeId}/ocr`
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OCR結果の取得に失敗しました: ${errorText}`);
    }

    const data: NodeOCRResponse = await response.json();
    setNodeOCRResults(data.results);
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingNodeOCRResults(false);
  }
}
async function generateGeminiDescriptionsForCurrentNode() {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  if (!currentNodeId) {
    setErrorMessage("現在ノードが選択されていません。");
    return;
  }

  try {
    setLoadingGeminiNodeGeneration(true);
    setErrorMessage("");
    setGeminiNodeGenerationResult(null);

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/nodes/${currentNodeId}/generate-gemini-descriptions`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Gemini説明生成に失敗しました: ${errorText}`);
    }

    const data: GenerateNodeDescriptionsResponse = await response.json();
    setGeminiNodeGenerationResult(data);

    // 生成後、現在ノードの説明を再読み込みする
    await fetchNodeDescriptions(currentNodeId);
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingGeminiNodeGeneration(false);
  }
}
async function fetchReviewTasks() {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  try {
    setLoadingReviewTasks(true);
    setErrorMessage("");
    setReviewMessage("");

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/review/tasks?limit=20`
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`レビュー対象の取得に失敗しました: ${errorText}`);
    }

    const data: ReviewTasksResponse = await response.json();
    setReviewTasks(data.tasks);
    setReviewMessage(`レビュー対象を ${data.task_count} 件読み込みました。`);
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setLoadingReviewTasks(false);
  }
}
async function approveReviewDescription(descriptionId: string) {
  if (!selectedProjectId) {
    setErrorMessage("プロジェクトが選択されていません。");
    return;
  }

  try {
    setUpdatingReviewDescriptionId(descriptionId);
    setErrorMessage("");
    setReviewMessage("");

    const response = await fetch(
      `${API_BASE_URL}/projects/${selectedProjectId}/review/description/${descriptionId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          approval_status: "approved",
          notes: "frontend review approval",
          edited_by: "local_user",
        }),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`レビュー承認に失敗しました: ${errorText}`);
    }

    const data: ReviewDescriptionResponse = await response.json();
    setReviewMessage(
      `${data.description_id} を承認しました。version=${data.version}`
    );

    await fetchReviewTasks();
  } catch (error) {
    setErrorMessage(
      error instanceof Error ? error.message : "不明なエラーが発生しました。"
    );
  } finally {
    setUpdatingReviewDescriptionId(null);
  }
}
  function handleProjectChange(projectId: string) {
  setSelectedProjectId(projectId);
  setMapData(null);
  setCurrentNodeId(null);
  setSearchResults([]);
  setRouteResult(null);
  setSelectedNodeId(null);
  setNodeDescriptions([]);
  setNodeSectorImages([]);
  setNodeOCRResults([]);
  setGeminiNodeGenerationResult(null);
}
  function getNeighborNodeIds(nodeId: string, edges: MapEdge[]): string[] {
  const neighborIds: string[] = [];

  for (const edge of edges) {
    if (edge.from_node_id === nodeId) {
      neighborIds.push(edge.to_node_id);
    }

    const isBidirectional =
      edge.directionality === "bidirectional" || edge.directionality === undefined;

    if (isBidirectional && edge.to_node_id === nodeId) {
      neighborIds.push(edge.from_node_id);
    }
  }

  return Array.from(new Set(neighborIds)).sort();
}

function moveToNode(nodeId: string) {
  setCurrentNodeId(nodeId);

  setSelectedNodeId(null);
  setNodeDescriptions([]);
  setNodeSectorImages([]);
  setNodeOCRResults([]);
  setGeminiNodeGenerationResult(null);
  setSelectedSector("front");
}

  function renderProjectPage() {
    return (
      <section className="card">
        <h2>プロジェクト一覧</h2>

        {loadingProjects && <p>プロジェクト一覧を読み込み中...</p>}

        {!loadingProjects && projects.length === 0 && (
          <p>プロジェクトがありません。</p>
        )}

        {projects.length > 0 && (
          <div className="formRow">
            <label htmlFor="projectSelect">プロジェクトを選択</label>
            <select
              id="projectSelect"
              value={selectedProjectId ?? ""}
              onChange={(event) => handleProjectChange(event.target.value)}
            >
              {projects.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.title} / {project.status}
                </option>
              ))}
            </select>
          </div>
        )}

        {selectedProjectId && (
          <button type="button" onClick={() => fetchMap(selectedProjectId)}>
            地図データを読み込んで探索画面へ
          </button>
        )}
      </section>
    );
  }

  function renderUploadPage() {
    return (
      <section className="card">
        <h2>アップロード</h2>
        <p>
          360度動画をアップロードし、前処理、仮グラフ生成まで順番に実行します。
        </p>

        <div className="formRow">
          <label htmlFor="videoFile">動画ファイル</label>
          <input
            id="videoFile"
            type="file"
            accept=".mp4,.mov,.avi,.mkv,video/*"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
              setUploadResult(null);
              setJobStatus(null);
              setPreprocessResult(null);
              setGraphGenerationResult(null);
              setDescriptionGenerationResult(null);
              setNodeDescriptions([]);
              setSelectedNodeId(null);
            }}
          />
        </div>

        {selectedFile && (
          <div className="resultBox">
            <h3>選択中のファイル</h3>
            <p>ファイル名: {selectedFile.name}</p>
            <p>サイズ: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        )}

        <button type="button" onClick={uploadVideo}>
          アップロードする
        </button>

        {loadingUpload && <p>アップロード中...</p>}

        {uploadResult && (
          <div className="resultBox">
            <h3>アップロード結果</h3>
            <p>status: {uploadResult.status}</p>
            <p>job_id: {uploadResult.job_id}</p>
            <p>filename: {uploadResult.filename}</p>
            <p>message: {uploadResult.message}</p>

            <div className="buttonRow">
              <button type="button" onClick={fetchJobStatus}>
                ジョブ状態を確認
              </button>

              <button type="button" onClick={startPreprocess}>
                前処理を開始
              </button>
            </div>
          </div>
        )}

        {loadingPreprocess && <p>前処理中...</p>}

        {preprocessResult && (
          <div className="resultBox">
            <h3>前処理結果</h3>
            <p>status: {preprocessResult.status}</p>
            <p>step: {preprocessResult.step}</p>
            <p>message: {preprocessResult.message}</p>
            <p>keyframe_count: {preprocessResult.keyframe_count}</p>
            <p className="smallText">
              ocr_master_path: {preprocessResult.ocr_master_path}
            </p>
            <p className="smallText">
              slam_erp_path: {preprocessResult.slam_erp_path}
            </p>

            <button type="button" onClick={generateDummyGraph}>
              仮グラフを生成
            </button>
          </div>
        )}

        {loadingGraphGeneration && <p>仮グラフ生成中...</p>}

        {graphGenerationResult && (
          <div className="resultBox">
            <h3>仮グラフ生成結果</h3>
            <p>status: {graphGenerationResult.status}</p>
            <p>node_count: {graphGenerationResult.node_count}</p>
            <p>edge_count: {graphGenerationResult.edge_count}</p>
            <p>  sector_description_count:{" "}
                {jobStatus?.sector_description_count ?? "未設定"}
            </p>
            <p className="smallText">
              graph_path: {graphGenerationResult.graph_path}
            </p>
            <div className="buttonRow">
              <button type="button" onClick={generateDummyDescriptions}>
                8方向説明を生成
              </button>
            {selectedProjectId && (
              <button type="button" onClick={() => fetchMap(selectedProjectId)}>
                生成済みグラフを探索画面で表示
              </button>
            )}
          </div>
          </div>
        )}
        {loadingDescriptionGeneration && <p>8方向説明を生成中...</p>}

        {descriptionGenerationResult && (
         <div className="resultBox">
          <h3>8方向説明生成結果</h3>
          <p>status: {descriptionGenerationResult.status}</p>
          <p>node_count: {descriptionGenerationResult.node_count}</p>
          <p>
            sector_description_count:{" "}
            {descriptionGenerationResult.sector_description_count}
          </p>
          <p className="smallText">
            descriptions_path: {descriptionGenerationResult.descriptions_path}
          </p>
        </div>
      )}

        {loadingJobStatus && <p>ジョブ状態を確認中...</p>}

        {jobStatus && (
          <div className="resultBox">
            <h3>ジョブ状態</h3>
            <p>status: {jobStatus.status}</p>
            <p>step: {jobStatus.step}</p>
            <p>filename: {jobStatus.filename}</p>
            <p>keyframe_count: {jobStatus.keyframe_count ?? "未設定"}</p>
            <p>node_count: {jobStatus.node_count ?? "未設定"}</p>
            <p>edge_count: {jobStatus.edge_count ?? "未設定"}</p>
            <p>updated_at: {jobStatus.updated_at}</p>
            {jobStatus.error_message && (
              <p>error_message: {jobStatus.error_message}</p>
            )}
          </div>
        )}
      </section>
    );
  }

function renderExplorePage() {
  const visibleNodes = mapData?.nodes.slice(0, 20) ?? [];
  const visibleEdges = mapData?.edges.slice(0, 20) ?? [];

  const currentNode =
    currentNodeId && mapData
      ? mapData.nodes.find((node) => node.node_id === currentNodeId) ?? null
      : null;

  const neighborNodeIds =
    currentNodeId && mapData
      ? getNeighborNodeIds(currentNodeId, mapData.edges)
      : [];

  return (
      <section className="card">
        <h2>探索</h2>
        <p>
          backend の <code>/projects/:id/map</code>{" "}
          から取得したノードグラフを表示します。
        </p>

        {selectedProjectId && (
          <button type="button" onClick={() => fetchMap(selectedProjectId)}>
            地図データを再読み込み
          </button>
        )}

        {loadingMap && <p>地図データを読み込み中...</p>}

        {mapData === null && !loadingMap && (
          <p>
            まだ地図データは読み込まれていません。プロジェクト一覧から地図データを読み込んでください。
          </p>
        )}

        {mapData && (
          <>
            <div className="resultBox">
              <h3>グラフ概要</h3>
              <p>project_id: {mapData.project_id}</p>
              <p>graph_type: {mapData.graph_type ?? "旧ダミーグラフ"}</p>
              <p>node_count: {mapData.nodes.length}</p>
              <p>edge_count: {mapData.edges.length}</p>
              <p className="muted">
                表示負荷を避けるため、この画面では先頭20件だけ表示します。
              </p>
            </div>
            {currentNode && (
              <div className="currentNodeBox">
                <h3>現在ノード</h3>
                <p>
                  <strong>{currentNode.node_id}</strong>:{" "}
                  {currentNode.name ?? "名称未設定"} /{" "}
                  {currentNode.floor_id ?? "floor未設定"}
                </p>

                <p>{currentNode.description_ja ?? "説明文は未設定です。"}</p>

                {currentNode.pose && (
                  <p className="smallText">
                    pose: x={currentNode.pose.x}, y={currentNode.pose.y}, z=
                    {currentNode.pose.z ?? 0}, yaw={currentNode.pose.yaw_deg ?? 0}
                  </p>
                )}

                {currentNode.media?.keyframe_image && (
                  <p className="smallText">
                    keyframe: {currentNode.media.keyframe_image}
                  </p>
                )}

                {buildMediaUrl(currentNode.media?.keyframe_url) && (
                  <div className="imagePreviewBox">
                    <img
                      src={buildMediaUrl(currentNode.media?.keyframe_url) ?? ""}
                      alt={`${currentNode.node_id} の代表フレーム`}
                      className="keyframePreview"
                    />
                  </div>
                )}

               <div className="buttonRow">
                  <button
                    type="button"
                    onClick={() => fetchNodeDescriptions(currentNode.node_id)}
                  >
                    このノードの8方向説明を表示
                  </button>

                  <button
                    type="button"
                    onClick={generateGeminiDescriptionsForCurrentNode}
                    disabled={loadingGeminiNodeGeneration}
                  >
                    {loadingGeminiNodeGeneration
                      ? "Gemini生成中..."
                      : "このノードの8方向をGemini生成"}
                  </button>
                </div>
                {geminiNodeGenerationResult && (
                  <div className="resultBox">
                    <h4>Gemini生成結果</h4>
                    <p>node_id: {geminiNodeGenerationResult.node_id}</p>
                    <p>updated_count: {geminiNodeGenerationResult.updated_count}</p>
                    <p>failed_count: {geminiNodeGenerationResult.failed_count}</p>

                    {geminiNodeGenerationResult.updated_description_ids.length > 0 && (
                      <>
                        <p>更新されたdescription:</p>
                        <ul>
                          {geminiNodeGenerationResult.updated_description_ids.map(
                            (descriptionId) => (
                              <li key={descriptionId}>{descriptionId}</li>
                            )
                          )}
                        </ul>
                      </>
                    )}

                    {geminiNodeGenerationResult.failed_sectors.length > 0 && (
                      <>
                        <p>失敗したsector:</p>
                        <ul>
                          {geminiNodeGenerationResult.failed_sectors.map((sector) => (
                            <li key={sector}>{sector}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}

                <h4>隣接ノードへ移動</h4>

                {neighborNodeIds.length === 0 && <p>隣接ノードがありません。</p>}

                {neighborNodeIds.length > 0 && (
                  <div className="neighborGrid">
                    {neighborNodeIds.map((neighborNodeId) => (
                      <button
                        key={neighborNodeId}
                        type="button"
                        onClick={() => moveToNode(neighborNodeId)}
                      >
                        {neighborNodeId} へ移動
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <h3>Nodes</h3>
            <ul className="compactList">
              {visibleNodes.map((node) => (
                <li key={node.node_id}>
                  <strong>{node.node_id}</strong>:{" "}
                  {node.name ?? "名称未設定"} / {node.floor_id ?? "floor未設定"}
                  <br />
                  {node.description_ja ?? "説明文は未設定です。"}
                  <br />
                  {node.pose && (
                    <span className="smallText">
                      pose: x={node.pose.x}, y={node.pose.y}, z=
                      {node.pose.z ?? 0}, yaw={node.pose.yaw_deg ?? 0}
                    </span>
                  )}
                  {!node.pose && node.x !== undefined && node.y !== undefined && (
                    <span className="smallText">
                      position: x={node.x}, y={node.y}
                    </span>
                  )}

                  {buildMediaUrl(node.media?.keyframe_url) && (
                    <div className="thumbnailBox">
                      <img
                        src={buildMediaUrl(node.media?.keyframe_url) ?? ""}
                        alt={`${node.node_id} の代表フレーム`}
                        className="keyframeThumbnail"
                      />
                    </div>
                  )}
                  {node.media?.keyframe_image && (
                    <>
                      <br />
                      <span className="smallText">
                        keyframe: {node.media.keyframe_image}
                      </span>
                    </>
                  )}
                  {node.confidence && (
                    <>
                      <br />
                      <span className="smallText">
                        confidence: pose={node.confidence.pose ?? "未設定"}, ocr=
                        {node.confidence.ocr ?? "未設定"}, description=
                        {node.confidence.description ?? "未設定"}
                      </span>
                    </>
                  )}
                  {node.review_required !== undefined && (
                    <>
                      <br />
                      <span className="smallText">
                        review_required: {String(node.review_required)}
                      </span>
                    </>
                  )}
                  <br />
                 <div className="buttonRow">
                    <button type="button" onClick={() => moveToNode(node.node_id)}>
                      このノードを現在地にする
                    </button>

                    <button type="button" onClick={() => fetchNodeDescriptions(node.node_id)}>
                      8方向説明を表示
                    </button>
                  </div>
                </li>
              ))}
            </ul>

            <h3>Edges</h3>
            <ul className="compactList">
              {visibleEdges.map((edge) => (
                <li key={edge.edge_id}>
                  <strong>{edge.edge_id}</strong>: {edge.from_node_id} →{" "}
                  {edge.to_node_id}
                  <br />
                  <span className="smallText">
                    type: {edge.edge_type ?? edge.direction ?? "未設定"} /
                    directionality: {edge.directionality ?? "未設定"}
                  </span>
                </li>
              ))}
            </ul>
            {loadingNodeDescriptions && <p>ノードの8方向説明を読み込み中...</p>}

            {selectedNodeId && nodeDescriptions.length > 0 && (
              <div className="resultBox">
                <h3>8方向説明: {selectedNodeId}</h3>

                <div className="sectorGrid">
                  {nodeDescriptions.map((description) => (
                    <button
                      key={description.sector}
                      type="button"
                      className={
                        selectedSector === description.sector ? "activeSector" : ""
                    }
                    onClick={() => setSelectedSector(description.sector)}
              >
                    {description.sector_label_ja}
                  </button>
            ))}
          </div>

          {loadingNodeSectorImages && <p>sector画像を読み込み中...</p>}

          {nodeDescriptions
            .filter((description) => description.sector === selectedSector)
            .map((description) => {
              const sectorImage = nodeSectorImages.find(
                (image) => image.sector === description.sector
              );

              const ocrResultsForSector = nodeOCRResults.filter(
                (ocrResult) => ocrResult.sector === description.sector
              );

              return (
                <div key={description.description_id} className="descriptionPanel">
                  <h4>
                    {description.sector_label_ja} / {description.sector_label_en}
                  </h4>

                  {sectorImage && (
                    <div className="sectorImageBox">
                      <img
                        src={buildMediaUrl(sectorImage.image_url) ?? ""}
                        alt={`${selectedNodeId} ${description.sector_label_ja}方向の画像`}
                        className="sectorImagePreview"
                      />
                      <p className="smallText">sector_image: {sectorImage.image_url}</p>
                    </div>
                  )}

                  {!sectorImage && !loadingNodeSectorImages && (
                    <p className="smallText">
                      この方向のsector画像はまだ生成されていません。
                    </p>
                  )}

                  {loadingNodeOCRResults && <p>OCR結果を読み込み中...</p>}

                  {ocrResultsForSector.length > 0 && (
                    <div className="ocrBox">
                      <h5>OCR結果</h5>
                      <ul>
                        {ocrResultsForSector.map((ocrResult) => (
                          <li key={ocrResult.ocr_id}>
                            <strong>{ocrResult.text}</strong>
                            <br />
                            <span className="smallText">
                              sector: {ocrResult.sector} / language:{" "}
                              {ocrResult.language_hint} / confidence:{" "}
                              {ocrResult.confidence}
                            </span>
                            <br />
                            <span className="smallText">
                              bbox: x={ocrResult.bbox.x}, y={ocrResult.bbox.y}, w=
                              {ocrResult.bbox.width}, h={ocrResult.bbox.height}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {!loadingNodeOCRResults && ocrResultsForSector.length === 0 && (
                    <p className="smallText">この方向のOCR結果はありません。</p>
                  )}

                  <h5>簡潔</h5>
                  <p>{description.ja.brief}</p>

                  <h5>詳細</h5>
                  <p>{description.ja.detailed}</p>

                  <h5>非常に詳細</h5>
                  <p>{description.ja.very_detailed}</p>

                  <p className="smallText">
                    confidence: {description.confidence} / review_required:{" "}
                    {String(description.review_required)}
                  </p>
                </div>
              );
            })}
        </div>
      )}
          </>
        )}
      </section>
    );
  }

  function renderSearchPage() {
    return (
      <section className="card">
        <h2>検索</h2>
        <p>
          生成済みgraph.jsonのノードID、仮ノード名、説明文を検索します。次以降で生成済みグラフ検索に差し替えます。
        </p>

        <div className="formRow">
          <label htmlFor="searchQuery">検索語</label>
          <input
            id="searchQuery"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="例: 受付"
          />
        </div>

        <button type="button" onClick={searchProject}>
          検索する
        </button>

        {loadingSearch && <p>検索中...</p>}

        {searchResults.length > 0 && (
          <div className="resultBox">
            <h3>検索結果</h3>
            <ul>
              {searchResults.map((result) => (
                <li key={result.node_id}>
                  <strong>{result.node_id}</strong>: {result.name}
                  <br />
                  {result.matched_text}
                </li>
              ))}
            </ul>
          </div>
        )}

        {!loadingSearch && searchResults.length === 0 && (
          <p>検索結果はまだありません。</p>
        )}
      </section>
    );
  }

  function renderRoutePage() {
    return (
      <section className="card">
        <h2>経路訓練</h2>
        <p>
          生成済みgraph.jsonのエッジを使って、出発ノードから目的ノードまでの経路を計算します。次以降で生成済みグラフのエッジを使う経路計算に差し替えます。
        </p>

        <div className="formRow">
          <label htmlFor="startNodeId">出発ノード</label>
          <input
            id="startNodeId"
            value={startNodeId}
            onChange={(event) => setStartNodeId(event.target.value)}
            placeholder="例: N0001"
          />
        </div>

        <div className="formRow">
          <label htmlFor="goalNodeId">目的ノード</label>
          <input
            id="goalNodeId"
            value={goalNodeId}
            onChange={(event) => setGoalNodeId(event.target.value)}
            placeholder="例: N0010"
          />
        </div>

        <button type="button" onClick={calculateRoute}>
          経路を計算する
        </button>

        {loadingRoute && <p>経路を計算中...</p>}

        {routeResult && (
          <div className="resultBox">
            <h3>経路結果</h3>
            <p>
              {routeResult.start_node_id} → {routeResult.goal_node_id} /{" "}
              {routeResult.mode}
            </p>

            <h4>Route</h4>
            <p>{routeResult.route.join(" → ")}</p>

            <h4>Instructions</h4>
            <ol>
              {routeResult.instructions_ja.map((instruction, index) => (
                <li key={`${instruction}-${index}`}>{instruction}</li>
              ))}
            </ol>
          </div>
        )}
      </section>
    );
  }

  function renderReviewPage() {
  return (
    <section className="card">
      <h2>レビュー</h2>
      <p>
        review_required=true の8方向説明だけを取得し、description単位で承認します。
      </p>

      <button type="button" onClick={fetchReviewTasks}>
        レビュー対象を読み込む
      </button>

      {loadingReviewTasks && <p>レビュー対象を読み込み中...</p>}

      {reviewMessage && (
        <div className="resultBox">
          <p>{reviewMessage}</p>
        </div>
      )}

      {!loadingReviewTasks && reviewTasks.length === 0 && (
        <p>レビュー対象はまだ読み込まれていません。</p>
      )}

      {reviewTasks.length > 0 && (
        <div className="resultBox">
          <h3>レビュー対象一覧</h3>
          <p>表示件数: {reviewTasks.length}</p>

          <ul className="compactList">
            {reviewTasks.map((task) => (
              <li key={task.description_id}>
                <strong>{task.description_id}</strong>
                <br />
                node: {task.node_id} / sector: {task.sector_label_ja} (
                {task.sector})
                <br />
                <span className="smallText">
                  confidence: {task.confidence} / review_required:{" "}
                  {String(task.review_required)} / version:{" "}
                  {task.version ?? 1}
                </span>

                <h4>簡潔説明</h4>
                <p>{task.ja.brief}</p>

                <h4>詳細説明</h4>
                <p>{task.ja.detailed}</p>

                <div className="buttonRow">
                  <button
                    type="button"
                    onClick={() =>
                      approveReviewDescription(task.description_id)
                    }
                    disabled={
                      updatingReviewDescriptionId === task.description_id
                    }
                  >
                    {updatingReviewDescriptionId === task.description_id
                      ? "承認中..."
                      : "承認する"}
                  </button>

                  <button
                    type="button"
                    onClick={() => fetchNodeDescriptions(task.node_id)}
                  >
                    探索用の8方向説明として確認
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
  function renderCurrentPage() {
    if (currentPage === "projects") return renderProjectPage();
    if (currentPage === "upload") return renderUploadPage();
    if (currentPage === "explore") return renderExplorePage();
    if (currentPage === "search") return renderSearchPage();
    if (currentPage === "route") return renderRoutePage();
    return renderReviewPage();
  }

  return (
    <main className="app">
      <header className="appHeader">
        <h1>Blind Map System MVP</h1>
        <p>
          360度動画から生成されるノードベース探索マップの研究用プロトタイプです。
        </p>
      </header>

      <nav className="navTabs" aria-label="画面切り替え">
        {(Object.keys(pageLabels) as PageName[]).map((pageName) => (
          <button
            key={pageName}
            type="button"
            className={currentPage === pageName ? "activeTab" : ""}
            onClick={() => setCurrentPage(pageName)}
          >
            {pageLabels[pageName]}
          </button>
        ))}
      </nav>

      {errorMessage && (
        <section className="errorBox">
          <h2>エラー</h2>
          <p>{errorMessage}</p>
        </section>
      )}

      {renderCurrentPage()}
    </main>
  );
}

export default App;