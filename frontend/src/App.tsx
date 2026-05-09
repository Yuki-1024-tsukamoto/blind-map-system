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

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [mapData, setMapData] = useState<MapResponse | null>(null);
  const [loadingProjects, setLoadingProjects] = useState<boolean>(false);
  const [loadingMap, setLoadingMap] = useState<boolean>(false);
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

  function handleProjectChange(projectId: string) {
    setSelectedProjectId(projectId);
    setMapData(null);
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