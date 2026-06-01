import { useEffect, useState } from "react";
import { type DatasetContext, useDatasetVersions } from "./hooks/useDatasetVersions";

type TrainWithPlanResponse = {
  dataset_id: number;
  version_id: number;
  plan_id: number | null;
  feature_summary: {
    target_col: string;
    selected_features: string[];
    excluded_features: string[];
    derived_features: string[];
  };
  train_results: {
    best_model?: {
      name: string;
      score: number;
      path: string;
      note?: string;
    };
    models?: Record<string, unknown>;
  };
};

type ApiErrorResponse = {
  detail?: string;
};

type SubmenuPageAutoMLProps = {
  activeDataset: DatasetContext | null;
  onDatasetVersionChange?: (datasetId: number, versionId: number, versionNumber: number) => void;
};

const FEATURE_PLAN_STORAGE_KEY = "m5_feature_plan";

const parseJsonSafely = async <T,>(response: Response): Promise<T | null> => {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
};

export default function SubmenuPageAutoML({ activeDataset, onDatasetVersionChange }: SubmenuPageAutoMLProps) {
  const [testSize, setTestSize] = useState(0.2);
  const [randomState, setRandomState] = useState(42);
  const [primaryMetric, setPrimaryMetric] = useState("roc_auc");
  const [optimizeHyperparams, setOptimizeHyperparams] = useState(true);
  const [storedPlanId, setStoredPlanId] = useState<number | null>(null);
  const [manualPlanId, setManualPlanId] = useState("");
  const [isTraining, setIsTraining] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [trainResponse, setTrainResponse] = useState<TrainWithPlanResponse | null>(null);

  const {
    versions,
    selectedVersionId,
    selectedVersion,
    isLoadingVersions,
    versionError,
    setSelectedVersionId,
  } = useDatasetVersions(activeDataset, onDatasetVersionChange);

  useEffect(() => {
    if (!activeDataset || !selectedVersionId) {
      setStoredPlanId(null);
      return;
    }

    const raw = localStorage.getItem(FEATURE_PLAN_STORAGE_KEY);
    if (!raw) {
      setStoredPlanId(null);
      return;
    }

    try {
      const parsed = JSON.parse(raw) as {
        datasetId: number;
        versionId: number;
        planId: number;
      };

      if (parsed.datasetId === activeDataset.datasetId && parsed.versionId === selectedVersionId) {
        setStoredPlanId(parsed.planId);
        setManualPlanId(String(parsed.planId));
      } else {
        setStoredPlanId(null);
      }
    } catch {
      setStoredPlanId(null);
    }
  }, [activeDataset, selectedVersionId]);

  useEffect(() => {
    if (versionError) {
      setErrorMessage(versionError);
    }
  }, [versionError]);

  const runTrain = async () => {
    if (!activeDataset || !selectedVersionId) {
      setErrorMessage("Primero selecciona un dataset y versión válidos.");
      return;
    }

    const numericPlanId = Number(manualPlanId);
    if (!manualPlanId || Number.isNaN(numericPlanId) || numericPlanId <= 0) {
      setErrorMessage("Debes indicar un plan_id válido guardado en Definir features.");
      return;
    }

    setIsTraining(true);
    setErrorMessage("");
    setSuccessMessage("");
    setTrainResponse(null);

    try {
      const response = await fetch("/apim5/features/automl/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_id: activeDataset.datasetId,
          version_id: selectedVersionId,
          plan_id: numericPlanId,
          test_size: testSize,
          random_state: randomState,
          primary_metric: primaryMetric,
          optimize_hyperparams: optimizeHyperparams,
        }),
      });

      const payload = await parseJsonSafely<TrainWithPlanResponse & ApiErrorResponse>(response);
      if (!response.ok || !payload) {
        throw new Error(payload?.detail ?? "No se pudo ejecutar el entrenamiento AutoML.");
      }

      setTrainResponse(payload);
      setSuccessMessage("Entrenamiento ejecutado correctamente con Feature Plan.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error desconocido durante el entrenamiento.";
      setErrorMessage(message);
    } finally {
      setIsTraining(false);
    }
  };

  if (!activeDataset) {
    return (
      <section className="submenu-page csv-upload-page" aria-labelledby="automl-title">
        <div className="submenu-page-header">
          <span className="submenu-page-parent">Menu: Entrenar modelo</span>
          <h2 id="automl-title">Lanzar AutoML</h2>
          <p>Primero carga un dataset y define features para habilitar esta vista.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="submenu-page csv-upload-page" aria-labelledby="automl-title">
      <div className="submenu-page-header">
        <span className="submenu-page-parent">Menu: Entrenar modelo</span>
        <h2 id="automl-title">Lanzar AutoML</h2>
        <p>Ejecuta entrenamiento de modelos usando el Feature Plan guardado en la subpágina Definir features.</p>
      </div>

      <article className="submenu-page-body csv-upload-body">
        <div className="csv-upload-panel">
          <div className="csv-upload-meta">
            <p>
              <strong>Dataset activo:</strong> #{activeDataset.datasetId} ({activeDataset.filename})
            </p>
            <label className="csv-file-picker">
              <span>Versión del dataset</span>
              <select
                className="csv-version-select"
                value={selectedVersionId ?? ""}
                onChange={(event) => {
                  const nextVersionId = Number(event.target.value);
                  setSelectedVersionId(Number.isNaN(nextVersionId) ? null : nextVersionId);
                }}
                disabled={isLoadingVersions || versions.length === 0}
              >
                {versions.map((version) => (
                  <option key={version.id} value={version.id}>
                    v{version.version_number} - filas: {version.row_count ?? "?"}, columnas: {version.column_count ?? "?"}
                  </option>
                ))}
              </select>
            </label>
            <p>
              <strong>Versión seleccionada:</strong> {selectedVersion ? `v${selectedVersion.version_number}` : "Ninguna"}
            </p>
            <p>
              <strong>Plan guardado (local):</strong> {storedPlanId ? `#${storedPlanId}` : "No detectado"}
            </p>
          </div>

          <div className="feature-plan-grid">
            <label className="csv-file-picker">
              <span>Plan ID</span>
              <input
                type="number"
                min={1}
                value={manualPlanId}
                onChange={(event) => setManualPlanId(event.target.value)}
                placeholder="Ej: 123"
              />
            </label>

            <label className="csv-file-picker">
              <span>Test size</span>
              <input
                type="number"
                min={0.05}
                max={0.5}
                step={0.01}
                value={testSize}
                onChange={(event) => setTestSize(Number(event.target.value))}
              />
            </label>

            <label className="csv-file-picker">
              <span>Random state</span>
              <input
                type="number"
                value={randomState}
                onChange={(event) => setRandomState(Number(event.target.value))}
              />
            </label>

            <label className="csv-file-picker">
              <span>Métrica principal</span>
              <select className="csv-version-select" value={primaryMetric} onChange={(event) => setPrimaryMetric(event.target.value)}>
                <option value="roc_auc">roc_auc</option>
                <option value="f1">f1</option>
                <option value="accuracy">accuracy</option>
                <option value="precision">precision</option>
                <option value="recall">recall</option>
              </select>
            </label>

            <label className="feature-inline-check">
              <input
                type="checkbox"
                checked={optimizeHyperparams}
                onChange={(event) => setOptimizeHyperparams(event.target.checked)}
              />
              Optimizar hiperparámetros
            </label>
          </div>

          <button type="button" className="csv-upload-button" onClick={runTrain} disabled={isTraining}>
            {isTraining ? "Entrenando..." : "Ejecutar AutoML con Feature Plan"}
          </button>

          {errorMessage && <div className="csv-alert csv-alert--error">{errorMessage}</div>}
          {successMessage && <div className="csv-alert csv-alert--success">{successMessage}</div>}
        </div>

        <section className="csv-info-card">
          <h3>Resultado de entrenamiento</h3>
          {trainResponse ? (
            <>
              <p>
                <strong>Plan aplicado:</strong> {trainResponse.plan_id ? `#${trainResponse.plan_id}` : "inline"}
              </p>
              <p>
                <strong>Target:</strong> {trainResponse.feature_summary.target_col}
              </p>
              <p>
                <strong>Features usadas:</strong> {trainResponse.feature_summary.selected_features.length}
              </p>
              {trainResponse.train_results.best_model && (
                <p>
                  <strong>Mejor modelo:</strong> {trainResponse.train_results.best_model.name} ({primaryMetric}={" "}
                  {trainResponse.train_results.best_model.score.toFixed(4)})
                </p>
              )}
              <pre className="csv-info-pre">{JSON.stringify(trainResponse, null, 2)}</pre>
            </>
          ) : (
            <p>Aquí aparecerán métricas y artefactos del AutoML cuando ejecutes el entrenamiento.</p>
          )}
        </section>
      </article>
    </section>
  );
}
