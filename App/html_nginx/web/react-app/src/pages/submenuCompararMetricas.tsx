import { useEffect, useMemo, useState } from "react";
import { type DatasetContext, useDatasetVersions } from "./hooks/useDatasetVersions";

type CompareModelEntry = {
	model: string;
	rank: number;
	ranking_metric: number | null;
	metrics: Record<string, number>;
	precision_recall_by_class: Array<{
		class: number;
		precision: number;
		recall: number;
		f1: number;
		support: number;
	}>;
	stability: {
		fold_scores: number[];
		mean: number | null;
		std: number | null;
		folds: number;
	};
	notes: string[];
};

type CompareMetricasResponse = {
	dataset_id: number;
	version_id: number;
	plan_id: number | null;
	operation_id: number;
	primary_metric: string;
	models_ranked: CompareModelEntry[];
	checklist: {
		ordered_by_primary_metric: boolean;
		precision_recall_by_class: boolean;
		stability_between_folds: boolean;
	};
};

type ApiErrorResponse = {
	detail?: string;
};

type SubmenuCompararMetricasProps = {
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

const formatMetric = (value: number | null | undefined): string => {
	if (value === null || value === undefined || Number.isNaN(value)) {
		return "N/A";
	}
	return value.toFixed(4);
};

export default function SubmenuCompararMetricas({
	activeDataset,
	onDatasetVersionChange,
}: SubmenuCompararMetricasProps) {
	const [primaryMetric, setPrimaryMetric] = useState("roc_auc");
	const [storedPlanId, setStoredPlanId] = useState<number | null>(null);
	const [manualPlanId, setManualPlanId] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [errorMessage, setErrorMessage] = useState("");
	const [successMessage, setSuccessMessage] = useState("");
	const [comparison, setComparison] = useState<CompareMetricasResponse | null>(null);

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

	const checklistSummary = useMemo(() => {
		if (!comparison) {
			return null;
		}

		return [
			{
				label: "Ordenar modelos por métrica objetivo",
				ok: comparison.checklist.ordered_by_primary_metric,
			},
			{
				label: "Revisar precisión y recall por clase",
				ok: comparison.checklist.precision_recall_by_class,
			},
			{
				label: "Validar estabilidad entre folds",
				ok: comparison.checklist.stability_between_folds,
			},
		];
	}, [comparison]);

	const runComparison = async () => {
		if (!activeDataset || !selectedVersionId) {
			setErrorMessage("Primero selecciona un dataset y versión válidos.");
			return;
		}

		const maybePlan = manualPlanId.trim();
		const parsedPlan = maybePlan ? Number(maybePlan) : null;
		if (maybePlan && (parsedPlan === null || Number.isNaN(parsedPlan) || parsedPlan <= 0)) {
			setErrorMessage("Si indicas plan_id debe ser un entero positivo.");
			return;
		}

		setIsLoading(true);
		setErrorMessage("");
		setSuccessMessage("");
		setComparison(null);

		try {
			const query = new URLSearchParams({ primary_metric: primaryMetric });
			if (parsedPlan) {
				query.set("plan_id", String(parsedPlan));
			}

			const response = await fetch(
				`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/comparar-metricas?${query.toString()}`,
			);
			const payload = await parseJsonSafely<CompareMetricasResponse & ApiErrorResponse>(response);

			if (!response.ok || !payload) {
				throw new Error(
					payload?.detail ??
						"No se pudo comparar métricas. Verifica que exista entrenamiento AutoML exitoso con Feature Plan.",
				);
			}

			setComparison(payload);
			setSuccessMessage("Comparación de métricas generada correctamente.");
		} catch (error) {
			const message =
				error instanceof Error ? error.message : "Error desconocido al comparar métricas de modelos.";
			setErrorMessage(message);
		} finally {
			setIsLoading(false);
		}
	};

	if (!activeDataset) {
		return (
			<section className="submenu-page csv-upload-page" aria-labelledby="comparar-title">
				<div className="submenu-page-header">
					<span className="submenu-page-parent">Menu: Entrenar modelo</span>
					<h2 id="comparar-title">Comparar métricas</h2>
					<p>Primero carga un dataset, define features y ejecuta AutoML para habilitar esta vista.</p>
				</div>
			</section>
		);
	}

	return (
		<section className="submenu-page csv-upload-page" aria-labelledby="comparar-title">
			<div className="submenu-page-header">
				<span className="submenu-page-parent">Menu: Entrenar modelo</span>
				<h2 id="comparar-title">Comparar métricas</h2>
				<p>
					Compara modelos del último entrenamiento AutoML (por versión y Feature Plan), ordenados por la
					métrica objetivo.
				</p>
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
							<span>Métrica principal</span>
							<select
								className="csv-version-select"
								value={primaryMetric}
								onChange={(event) => setPrimaryMetric(event.target.value)}
							>
								<option value="roc_auc">ROC-AUC: Capacidad global de separar clases</option>
								<option value="f1">F1-score: Balance entre Precision y Recall.</option>
								<option value="accuracy">Accuracy:  % de aciertos totales</option>
								<option value="precision">Precision: Calidad de los positivos detectados</option>
								<option value="recall">Recall: Cantidad de positivos encontrados</option>
							</select>
						</label>

						<label className="csv-file-picker">
							<span>Plan ID (opcional)</span>
							<input
								type="number"
								min={1}
								value={manualPlanId}
								onChange={(event) => setManualPlanId(event.target.value)}
								placeholder="Ej: 123"
							/>
						</label>
					</div>

					<button type="button" className="csv-upload-button" onClick={runComparison} disabled={isLoading}>
						{isLoading ? "Comparando..." : "Comparar métricas"}
					</button>

					{errorMessage && <div className="csv-alert csv-alert--error">{errorMessage}</div>}
					{successMessage && <div className="csv-alert csv-alert--success">{successMessage}</div>}
				</div>

				<section className="csv-info-card">
					<h3>Checklist operativo</h3>
					{checklistSummary ? (
						<ul>
							{checklistSummary.map((item) => (
								<li key={item.label}>
									{item.label}: <strong>{item.ok ? "OK" : "Pendiente"}</strong>
								</li>
							))}
						</ul>
					) : (
						<p>Ejecuta la comparación para validar checklist por dataset/versión/plan.</p>
					)}
				</section>

				<section className="csv-info-card">
					<h3>Ranking de modelos</h3>
					{comparison && comparison.models_ranked.length > 0 ? (
						<div className="csv-table-wrap">
							<table className="csv-table">
								<thead>
									<tr>
										<th title="La posición del modelo">Rank</th>
										<th title="Algoritmo evaluado">Modelo</th>
										<th title="Métrica principal">{comparison.primary_metric}</th>
										<th title="Precision de la clase 0">Precision class 0</th>
										<th title="De todos los casos que el modelo predijo como clase 0, qué proporción realmente era clase 0">Recall class 0</th>
										<th title="De todas las predicciones hechas como clase 1, cuántas fueron correctas">Precision class 1</th>
										<th title="De todos los casos reales de clase 1, cuántos encontró el modelo">Recall class 1</th>
										<th title="Media de la validación cruzada">CV mean</th>
										<th title="Desviación estándar de la validación cruzada">CV std</th>
									</tr>
								</thead>
								<tbody>
									{comparison.models_ranked.map((model) => {
										const class0 = model.precision_recall_by_class.find((item) => item.class === 0);
										const class1 = model.precision_recall_by_class.find((item) => item.class === 1);

										return (
											<tr key={model.model}>
												<td>{model.rank}</td>
												<td>{model.model}</td>
												<td>{formatMetric(model.ranking_metric)}</td>
												<td>{formatMetric(class0?.precision)}</td>
												<td>{formatMetric(class0?.recall)}</td>
												<td>{formatMetric(class1?.precision)}</td>
												<td>{formatMetric(class1?.recall)}</td>
												<td>{formatMetric(model.stability.mean)}</td>
												<td>{formatMetric(model.stability.std)}</td>
											</tr>
										);
									})}
								</tbody>
							</table>
						</div>
					) : (
						<p>No hay modelos comparables todavía para esta versión.</p>
					)}
				</section>

				<section className="csv-info-card">
					<h3>Detalle técnico</h3>
					{comparison ? (
						<pre className="csv-info-pre">{JSON.stringify(comparison, null, 2)}</pre>
					) : (
						<p>Aquí aparecerá el JSON completo para trazabilidad de la comparación.</p>
					)}
				</section>
			</article>
		</section>
	);
}
