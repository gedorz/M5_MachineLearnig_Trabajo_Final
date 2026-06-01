import { useEffect, useMemo, useState } from "react";
import { type DatasetContext, useDatasetVersions } from "./hooks/useDatasetVersions";

type FeatureProfileItem = {
  name: string;
  dtype: string;
  null_count: number;
  null_ratio: number;
  unique_count: number;
  is_numeric: boolean;
  suggested_role: "target" | "candidate" | "exclude_leakage";
};

type FeatureProfileResponse = {
  dataset_id: number;
  version_id: number;
  row_count: number;
  target_candidates: string[];
  leakage_suggestions: string[];
  features: FeatureProfileItem[];
};

type DerivedFeatureInput = {
  id: string;
  name: string;
  expression: string;
  description: string;
};

type FeaturePlanCreateResponse = {
  plan_id: number;
  dataset_id: number;
  version_id: number;
  summary: {
    target_col: string;
    selected_features: string[];
    excluded_features: string[];
    derived_features: string[];
    leakage_columns_present: string[];
  };
};

type FeaturePlanGetResponse = {
  plan_id: number;
  plan: {
    target_col: string;
    include_features: string[];
    exclude_features: string[];
    derived_features: Array<{ name: string; expression: string; description?: string }>;
    justifications: Array<{ feature: string; reason: string }>;
    notes?: string;
  };
};

type FeaturePlanApplyResponse = {
  dataset_id: number;
  source_version_id: number;
  new_version_id: number;
  new_version_number: number;
};

type ApiErrorResponse = {
  detail?: string;
};

type SubmenuPageFeaturesProps = {
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

const createDerivedFeature = (): DerivedFeatureInput => ({
  id: crypto.randomUUID(),
  name: "",
  expression: "",
  description: "",
});

export default function SubmenuPageFeatures({ activeDataset, onDatasetVersionChange }: SubmenuPageFeaturesProps) {
  const [profile, setProfile] = useState<FeatureProfileResponse | null>(null);
  const [targetCol, setTargetCol] = useState("is_canceled");
  const [includeMap, setIncludeMap] = useState<Record<string, boolean>>({});
  const [excludeMap, setExcludeMap] = useState<Record<string, boolean>>({});
  const [justificationMap, setJustificationMap] = useState<Record<string, string>>({});
  const [derivedFeatures, setDerivedFeatures] = useState<DerivedFeatureInput[]>([]);
  const [notes, setNotes] = useState("");
  const [savedPlan, setSavedPlan] = useState<FeaturePlanCreateResponse | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const {
    versions,
    selectedVersionId,
    selectedVersion,
    isLoadingVersions,
    versionError,
    setSelectedVersionId,
    reloadVersions,
  } = useDatasetVersions(activeDataset, onDatasetVersionChange);

  const selectedFeaturesCount = useMemo(
    () => Object.entries(includeMap).filter(([feature, enabled]) => enabled && !excludeMap[feature]).length,
    [includeMap, excludeMap],
  );

  useEffect(() => {
    if (!activeDataset || !selectedVersionId) {
      setProfile(null);
      setIncludeMap({});
      setExcludeMap({});
      setJustificationMap({});
      setDerivedFeatures([]);
      setSavedPlan(null);
      setErrorMessage("");
      setSuccessMessage("");
      return;
    }

    const abortController = new AbortController();

    const loadProfileAndPlan = async () => {
      setIsLoadingProfile(true);
      setErrorMessage("");
      setSuccessMessage("");

      try {
        const profileResponse = await fetch(
          `/apim5/features/profile/${activeDataset.datasetId}/versions/${selectedVersionId}`,
          { signal: abortController.signal },
        );
        const profilePayload = await parseJsonSafely<FeatureProfileResponse & ApiErrorResponse>(profileResponse);

        if (!profileResponse.ok || !profilePayload) {
          throw new Error(profilePayload?.detail ?? "No se pudo cargar el perfil de features.");
        }

        setProfile(profilePayload);

        const defaultTarget =
          profilePayload.target_candidates.find((candidate) => candidate === "is_canceled") ??
          profilePayload.target_candidates[0] ??
          profilePayload.features[0]?.name ??
          "is_canceled";

        const nextIncludeMap: Record<string, boolean> = {};
        const nextExcludeMap: Record<string, boolean> = {};

        profilePayload.features.forEach((feature) => {
          if (feature.name === defaultTarget) {
            nextIncludeMap[feature.name] = false;
            nextExcludeMap[feature.name] = false;
            return;
          }

          if (feature.suggested_role === "exclude_leakage") {
            nextIncludeMap[feature.name] = false;
            nextExcludeMap[feature.name] = true;
          } else {
            nextIncludeMap[feature.name] = true;
            nextExcludeMap[feature.name] = false;
          }
        });

        setTargetCol(defaultTarget);
        setIncludeMap(nextIncludeMap);
        setExcludeMap(nextExcludeMap);
        setJustificationMap({});
        setDerivedFeatures([]);
        setNotes("");
        setSavedPlan(null);

        const latestPlanResponse = await fetch(
          `/apim5/features/plan/${activeDataset.datasetId}/versions/${selectedVersionId}/latest`,
          { signal: abortController.signal },
        );

        if (latestPlanResponse.ok) {
          const latestPlanPayload = await parseJsonSafely<FeaturePlanGetResponse>(latestPlanResponse);
          if (latestPlanPayload) {
            const plannedTarget = latestPlanPayload.plan.target_col;
            const includeSet = new Set(latestPlanPayload.plan.include_features);
            const excludeSet = new Set(latestPlanPayload.plan.exclude_features);

            const restoredIncludeMap: Record<string, boolean> = {};
            const restoredExcludeMap: Record<string, boolean> = {};
            profilePayload.features.forEach((feature) => {
              if (feature.name === plannedTarget) {
                restoredIncludeMap[feature.name] = false;
                restoredExcludeMap[feature.name] = false;
                return;
              }
              restoredIncludeMap[feature.name] = includeSet.has(feature.name);
              restoredExcludeMap[feature.name] = excludeSet.has(feature.name);
            });

            setTargetCol(plannedTarget);
            setIncludeMap(restoredIncludeMap);
            setExcludeMap(restoredExcludeMap);

            const restoredJustifications: Record<string, string> = {};
            latestPlanPayload.plan.justifications.forEach((item) => {
              restoredJustifications[item.feature] = item.reason;
            });
            setJustificationMap(restoredJustifications);

            const restoredDerived = latestPlanPayload.plan.derived_features.map((item) => ({
              id: crypto.randomUUID(),
              name: item.name,
              expression: item.expression,
              description: item.description ?? "",
            }));
            setDerivedFeatures(restoredDerived);
            setNotes(latestPlanPayload.plan.notes ?? "");
            setSuccessMessage("Se recuperó el último Feature Plan guardado para esta versión.");
          }
        }
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }
        const message = error instanceof Error ? error.message : "Error desconocido al cargar Definir features.";
        setErrorMessage(message);
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoadingProfile(false);
        }
      }
    };

    void loadProfileAndPlan();

    return () => abortController.abort();
  }, [activeDataset, selectedVersionId]);

  useEffect(() => {
    if (versionError) {
      setErrorMessage(versionError);
    }
  }, [versionError]);

  const buildPlanPayload = () => {
    if (!activeDataset || !selectedVersionId) {
      return null;
    }

    const include_features = Object.entries(includeMap)
      .filter(([feature, selected]) => selected && !excludeMap[feature] && feature !== targetCol)
      .map(([feature]) => feature);

    const exclude_features = Object.entries(excludeMap)
      .filter(([feature, excluded]) => excluded && feature !== targetCol)
      .map(([feature]) => feature);

    const justifications = Object.entries(justificationMap)
      .filter(([feature, reason]) => reason.trim().length > 0 && feature !== targetCol)
      .map(([feature, reason]) => ({ feature, reason: reason.trim() }));

    const normalizedDerived = derivedFeatures
      .filter((item) => item.name.trim().length > 0 && item.expression.trim().length > 0)
      .map((item) => ({
        name: item.name.trim(),
        expression: item.expression.trim(),
        description: item.description.trim() || undefined,
      }));

    return {
      dataset_id: activeDataset.datasetId,
      version_id: selectedVersionId,
      target_col: targetCol,
      include_features,
      exclude_features,
      derived_features: normalizedDerived,
      justifications,
      notes: notes.trim() || undefined,
    };
  };

  const handleSavePlan = async () => {
    const payload = buildPlanPayload();
    if (!payload) {
      setErrorMessage("No hay dataset/version activos para guardar el plan.");
      return;
    }
    // este es el equivalente a la funcion preprocess_dataset del scr/ model_trainer.py, se encarga de validar y transformar la información del plan antes de enviarla al backend
    setIsSaving(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response = await fetch("/apim5/features/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await parseJsonSafely<FeaturePlanCreateResponse & ApiErrorResponse>(response);

      if (!response.ok || !result) {
        throw new Error(result?.detail ?? "No se pudo guardar el Feature Plan.");
      }

      // El plan se guarda para que sea usado autoML al aplicar el plan, 
      // no es necesario cargarlo en el estado para mostrarlo en la UI,
      // pero se hace para mostrar un mensaje de éxito con el ID del plan guardado
      setSavedPlan(result);
      localStorage.setItem(
        FEATURE_PLAN_STORAGE_KEY,
        JSON.stringify({
          datasetId: payload.dataset_id,
          versionId: payload.version_id,
          planId: result.plan_id,
          targetCol: payload.target_col,
          savedAt: new Date().toISOString(),
        }),
      );
      setSuccessMessage(`Feature Plan guardado correctamente (plan #${result.plan_id}).`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error desconocido al guardar el plan.";
      setErrorMessage(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleApplyPlan = async () => {
    const payload = buildPlanPayload();
    if (!payload) {
      setErrorMessage("No hay dataset/version activos para aplicar el plan.");
      return;
    }

    setIsApplying(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response = await fetch("/apim5/features/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_id: payload.dataset_id,
          version_id: payload.version_id,
          plan: payload,
        }),
      });

      const result = await parseJsonSafely<FeaturePlanApplyResponse & ApiErrorResponse>(response);
      if (!response.ok || !result) {
        throw new Error(result?.detail ?? "No se pudo aplicar el Feature Plan.");
      }

      onDatasetVersionChange?.(result.dataset_id, result.new_version_id, result.new_version_number);
      await reloadVersions();
      setSelectedVersionId(result.new_version_id);
      setSuccessMessage(
        `Feature Plan aplicado. Nueva versión creada: v${result.new_version_number} (#${result.new_version_id}).`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error desconocido al aplicar el plan.";
      setErrorMessage(message);
    } finally {
      setIsApplying(false);
    }
  };

  const handleToggleInclude = (featureName: string, checked: boolean) => {
    setIncludeMap((current) => ({ ...current, [featureName]: checked }));
    if (checked) {
      setExcludeMap((current) => ({ ...current, [featureName]: false }));
    }
  };

  const handleToggleExclude = (featureName: string, checked: boolean) => {
    setExcludeMap((current) => ({ ...current, [featureName]: checked }));
    if (checked) {
      setIncludeMap((current) => ({ ...current, [featureName]: false }));
    }
  };

  if (!activeDataset) {
    return (
      <section className="submenu-page csv-upload-page" aria-labelledby="features-title">
        <div className="submenu-page-header">
          <span className="submenu-page-parent">Menu: Entrenar modelo</span>
          <h2 id="features-title">Definir features</h2>
          <p>Primero carga un dataset en Importar CSV/Excel para habilitar esta vista.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="submenu-page csv-upload-page" aria-labelledby="features-title">
      <div className="submenu-page-header">
        <span className="submenu-page-parent">Menu: Entrenar modelo</span>
        <h2 id="features-title">Definir features</h2>
        <p>Selecciona variables, excluye fuga de información y documenta la justificación del Feature Plan.</p>
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
          </div>

          {errorMessage && <div className="csv-alert csv-alert--error">{errorMessage}</div>}
          {successMessage && <div className="csv-alert csv-alert--success">{successMessage}</div>}
        </div>

        {isLoadingProfile ? (
          <section className="csv-info-card">
            <div className="csv-loading-state" role="status" aria-live="polite" aria-busy="true">
              <span className="csv-loading-spinner" aria-hidden="true" />
              <p>Cargando perfil de features...</p>
            </div>
          </section>
        ) : profile ? (
          <>
            <section className="csv-info-card">
              <h3>Configuración general del plan</h3>
              <div className="feature-plan-grid">
                <label className="csv-file-picker">
                  <span>Variable objetivo</span>
                  <select className="csv-version-select" value={targetCol} onChange={(event) => setTargetCol(event.target.value)}>
                    {profile.features.map((feature) => (
                      <option key={feature.name} value={feature.name}>
                        {feature.name}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="feature-plan-kpis">
                  <p>
                    <strong>Filas:</strong> {profile.row_count}
                  </p>
                  <p>
                    <strong>Features seleccionadas:</strong> {selectedFeaturesCount}
                  </p>
                  <p>
                    <strong>Sugeridas por fuga:</strong> {profile.leakage_suggestions.join(", ") || "Ninguna"}
                  </p>
                </div>
              </div>
            </section>

            <section className="csv-info-card">
              <h3>Matriz de features</h3>
              <div className="csv-table-wrap">
                <table className="csv-table feature-matrix-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Tipo</th>
                      <th>Nulos</th>
                      <th>Únicos</th>
                      <th>Rol sugerido</th>
                      <th>Usar</th>
                      <th>Excluir</th>
                      <th>Justificación</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.features.map((feature) => {
                      const isTarget = feature.name === targetCol;
                      const nullPercent = `${(feature.null_ratio * 100).toFixed(2)}%`;
                      return (
                        <tr key={feature.name}>
                          <td>{feature.name}</td>
                          <td>{feature.dtype}</td>
                          <td>
                            {feature.null_count} ({nullPercent})
                          </td>
                          <td>{feature.unique_count}</td>
                          <td>{feature.suggested_role}</td>
                          <td>
                            <input
                              type="checkbox"
                              checked={Boolean(includeMap[feature.name])}
                              disabled={isTarget}
                              onChange={(event) => handleToggleInclude(feature.name, event.target.checked)}
                            />
                          </td>
                          <td>
                            <input
                              type="checkbox"
                              checked={Boolean(excludeMap[feature.name])}
                              disabled={isTarget}
                              onChange={(event) => handleToggleExclude(feature.name, event.target.checked)}
                            />
                          </td>
                          <td>
                            <input
                              type="text"
                              value={justificationMap[feature.name] ?? ""}
                              disabled={isTarget}
                              onChange={(event) =>
                                setJustificationMap((current) => ({ ...current, [feature.name]: event.target.value }))
                              }
                              placeholder={isTarget ? "Variable objetivo" : "Motivo de inclusión/exclusión"}
                              className="feature-justification-input"
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="csv-info-card">
              <h3>Variables derivadas</h3>
              <div className="feature-derived-list">
                {derivedFeatures.map((item) => (
                  <div key={item.id} className="feature-derived-item">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(event) =>
                        setDerivedFeatures((current) =>
                          current.map((entry) =>
                            entry.id === item.id ? { ...entry, name: event.target.value } : entry,
                          ),
                        )
                      }
                      placeholder="nombre_feature"
                    />
                    <input
                      type="text"
                      value={item.expression}
                      onChange={(event) =>
                        setDerivedFeatures((current) =>
                          current.map((entry) =>
                            entry.id === item.id ? { ...entry, expression: event.target.value } : entry,
                          ),
                        )
                      }
                      placeholder="expresión (ej: stays_in_weekend_nights + stays_in_week_nights)"
                    />
                    <input
                      type="text"
                      value={item.description}
                      onChange={(event) =>
                        setDerivedFeatures((current) =>
                          current.map((entry) =>
                            entry.id === item.id ? { ...entry, description: event.target.value } : entry,
                          ),
                        )
                      }
                      placeholder="descripción opcional"
                    />
                    <button
                      type="button"
                      className="csv-tab-button"
                      onClick={() =>
                        setDerivedFeatures((current) => current.filter((entry) => entry.id !== item.id))
                      }
                    >
                      Quitar
                    </button>
                  </div>
                ))}
              </div>
              <button type="button" className="csv-tab-button" onClick={() => setDerivedFeatures((current) => [...current, createDerivedFeature()])}>
                Agregar variable derivada
              </button>
            </section>

            <section className="csv-info-card">
              <h3>Notas del plan</h3>
              <textarea
                className="feature-notes-textarea"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Documenta criterios de negocio, supuestos y consideraciones del experimento."
              />
            </section>

            <section className="csv-info-card feature-actions-card">
              <button type="button" className="csv-upload-button" onClick={handleSavePlan} disabled={isSaving || isApplying}>
                {isSaving ? "Guardando plan..." : "Guardar Feature Plan"}
              </button>
              <button
                type="button"
                className="csv-tab-button"
                onClick={handleApplyPlan}
                disabled={isApplying || isSaving}
              >
                {isApplying ? "Aplicando plan..." : "Aplicar plan y crear nueva versión"}
              </button>
              {savedPlan && (
                <p>
                  Plan actual: <strong>#{savedPlan.plan_id}</strong> | target: <strong>{savedPlan.summary.target_col}</strong>
                </p>
              )}
            </section>
          </>
        ) : (
          <section className="csv-info-card">
            <p>No hay perfil disponible para la versión seleccionada.</p>
          </section>
        )}
      </article>
    </section>
  );
}
