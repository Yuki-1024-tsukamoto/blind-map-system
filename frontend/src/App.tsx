import { useEffect, useState } from "react";
import "./App.css";

type Project = {
  project_id: string;
  title: string;
  facility_type: string;
  status: string;
};

type Node = {
  node_id: string;
  name: string;
  floor_id: string;
  x: number;
  y: number;
  description_ja: string;
  description_en: string;
};

type Edge = {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  direction: string;
};

type MapResponse = {
  project_id: string;
  nodes: Node[];
  edges: Edge[];
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

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [mapData, setMapData] = useState<MapResponse | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>("受付");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const [startNodeId, setStartNodeId] = useState<string>("N001");
  const [goalNodeId, setGoalNodeId] = useState<string>("N003");
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);

  const [loadingProjects, setLoadingProjects] = useState<boolean>(false);
  const [loadingMap, setLoadingMap] = useState<boolean>(false);
  const [loadingSearch, setLoadingSearch] = useState<boolean>(false);
  const [loadingRoute, setLoadingRoute] = useState<boolean>(false);
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

  function handleProjectChange(projectId: string) {
    setSelectedProjectId(projectId);
    setMapData(null);
    setSearchResults([]);
    setRouteResult(null);
  }

  return (
    <main className="app">
      <header className="appHeader">
        <h1>Blind Map System MVP</h1>
        <p>
          360度動画から生成されるノードベース探索マップの研究用プロトタイプです。
        </p>
      </header>

      <section className="card">
        <h2>1. プロジェクト一覧</h2>

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
            地図データを読み込む
          </button>
        )}
      </section>

      <section className="card">
        <h2>2. 地図データ</h2>

        {loadingMap && <p>地図データを読み込み中...</p>}

        {mapData === null && !loadingMap && (
          <p>まだ地図データは読み込まれていません。</p>
        )}

        {mapData && (
          <>
            <h3>Nodes</h3>
            <ul>
              {mapData.nodes.map((node) => (
                <li key={node.node_id}>
                  <strong>{node.node_id}</strong>: {node.name} / {node.floor_id}
                  <br />
                  {node.description_ja}
                </li>
              ))}
            </ul>

            <h3>Edges</h3>
            <ul>
              {mapData.edges.map((edge) => (
                <li key={edge.edge_id}>
                  <strong>{edge.edge_id}</strong>: {edge.from_node_id} →{" "}
                  {edge.to_node_id} / {edge.direction}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="card">
        <h2>3. 検索</h2>
        <p>説明文やノード名に含まれる語を検索します。</p>

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

      <section className="card">
        <h2>4. 経路訓練</h2>
        <p>出発ノードと目的ノードを指定して、ダミールートを表示します。</p>

        <div className="formRow">
          <label htmlFor="startNodeId">出発ノード</label>
          <input
            id="startNodeId"
            value={startNodeId}
            onChange={(event) => setStartNodeId(event.target.value)}
            placeholder="例: N001"
          />
        </div>

        <div className="formRow">
          <label htmlFor="goalNodeId">目的ノード</label>
          <input
            id="goalNodeId"
            value={goalNodeId}
            onChange={(event) => setGoalNodeId(event.target.value)}
            placeholder="例: N003"
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

      {errorMessage && (
        <section className="errorBox">
          <h2>エラー</h2>
          <p>{errorMessage}</p>
        </section>
      )}
    </main>
  );
}

export default App;