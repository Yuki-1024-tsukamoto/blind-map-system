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

const API_BASE_URL = "http://127.0.0.1:8000";

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

  const [loadingProjects, setLoadingProjects] = useState<boolean>(false);
  const [loadingMap, setLoadingMap] = useState<boolean>(false);
  const [loadingSearch, setLoadingSearch] = useState<boolean>(false);
  const [loadingRoute, setLoadingRoute] = useState<boolean>(false);
  const [loadingUpload, setLoadingUpload] = useState<boolean>(false);
  const [loadingJobStatus, setLoadingJobStatus] = useState<boolean>(false);
  const [loadingPreprocess, setLoadingPreprocess] = useState<boolean>(false);
  const [loadingGraphGeneration, setLoadingGraphGeneration] =
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

  function handleProjectChange(projectId: string) {
    setSelectedProjectId(projectId);
    setMapData(null);
    setSearchResults([]);
    setRouteResult(null);
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
            <p className="smallText">
              graph_path: {graphGenerationResult.graph_path}
            </p>

            {selectedProjectId && (
              <button type="button" onClick={() => fetchMap(selectedProjectId)}>
                生成済みグラフを探索画面で表示
              </button>
            )}
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
          ここには、後で低信頼の説明文だけを確認・修正するレビューUIを追加します。
        </p>

        <div className="placeholderBox">
          <p>予定する機能</p>
          <ul>
            <li>低信頼descriptionの一覧表示</li>
            <li>画像・OCR結果・説明文の同時確認</li>
            <li>承認 / 編集 / 差し戻し</li>
          </ul>
        </div>
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