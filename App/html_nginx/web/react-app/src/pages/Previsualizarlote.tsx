import { useEffect, useState } from "react";
import CsvTable from "./components/CsvTable";
import { type DatasetContext, useDatasetVersions } from "./hooks/useDatasetVersions";

type TablePayload = {
	columns: string[];
	rows: Record<string, unknown>[];
};

type DataInfoResponse = {
	dataset_id: number;
	version: {
		id: number;
		version_number: number;
	};
	shape: [number, number];
	columns: string[];
	info: string;
	head: TablePayload;
	tail: TablePayload;
	transpose: TablePayload;
	describe: TablePayload;
	describe_transpose: TablePayload;
};

type SinglePlotResponse = {
	plot: string;
};

type VisualizationsResponse = {
	histplotAdr: string;
	histplotAdrKde: string;
	pairplot: string;
	nullsHeatmap: string;
	cancelationsDistribution: string;
	numericHistograms: string;
	outlierBoxplots: string;
	cancelationsByHotel: string;
	cancelationsByMonth: string;
	leadTimeDistribution: string;
	adrByHotelAndCancellation: string;
	correlationWithTarget: string;
};

type VisualizationKey = keyof VisualizationsResponse;

const createEmptyVisualizations = (): VisualizationsResponse => ({
	histplotAdr: "",
	histplotAdrKde: "",
	pairplot: "",
	nullsHeatmap: "",
	cancelationsDistribution: "",
	numericHistograms: "",
	outlierBoxplots: "",
	cancelationsByHotel: "",
	cancelationsByMonth: "",
	leadTimeDistribution: "",
	adrByHotelAndCancellation: "",
	correlationWithTarget: "",
});

const createPlotLoadingState = (isLoading: boolean): Record<VisualizationKey, boolean> => ({
	histplotAdr: isLoading,
	histplotAdrKde: isLoading,
	pairplot: isLoading,
	nullsHeatmap: isLoading,
	cancelationsDistribution: isLoading,
	numericHistograms: isLoading,
	outlierBoxplots: isLoading,
	cancelationsByHotel: isLoading,
	cancelationsByMonth: isLoading,
	leadTimeDistribution: isLoading,
	adrByHotelAndCancellation: isLoading,
	correlationWithTarget: isLoading,
});

type ApiErrorResponse = {
	detail?: string;
};

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

type PrevisualizarLoteProps = {
	activeDataset: DatasetContext | null;
	onDatasetVersionChange?: (datasetId: number, versionId: number, versionNumber: number) => void;
};

export default function PrevisualizarLotePage({ activeDataset, onDatasetVersionChange }: PrevisualizarLoteProps) {
	const [selectedTab, setSelectedTab] = useState<"data-info" | "visualizacion">("data-info");
	const [dataInfo, setDataInfo] = useState<DataInfoResponse | null>(null);
	const [visualizations, setVisualizations] = useState<VisualizationsResponse>(createEmptyVisualizations);
	const [errorMessage, setErrorMessage] = useState("");
	const [isLoadingDataInfo, setIsLoadingDataInfo] = useState(false);
	const [isLoadingVisualizations, setIsLoadingVisualizations] = useState(false);
	const [loadingPlots, setLoadingPlots] = useState<Record<VisualizationKey, boolean>>(createPlotLoadingState(false));

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
			setDataInfo(null);
			setVisualizations(createEmptyVisualizations());
			setIsLoadingDataInfo(false);
			setIsLoadingVisualizations(false);
			setLoadingPlots(createPlotLoadingState(false));
			return;
		}

		const abortController = new AbortController();
		const { signal } = abortController;
		let isDisposed = false;

		setErrorMessage("");
		setDataInfo(null);
		setVisualizations(createEmptyVisualizations());
		setIsLoadingDataInfo(true);
		setIsLoadingVisualizations(true);
		setLoadingPlots(createPlotLoadingState(true));

		const appendWarning = (message: string) => {
			setErrorMessage((previous) => (previous ? `${previous} ${message}` : message));
		};

		const datasetId = activeDataset.datasetId;
		const activeVersionId = activeDataset.versionId;

		const loadDataInfo = async () => {
			try {
				const infoResponse = await fetch(
					`/apim5/datasets-viewer/${datasetId}/versions/${selectedVersionId}/data-info`,
					{ signal }
				);
				const infoPayload = await parseJsonSafely<DataInfoResponse & ApiErrorResponse>(infoResponse);

				if (!infoResponse.ok) {
					throw new Error(
						infoPayload?.detail ?? `No se pudo cargar la información del dataset (HTTP ${infoResponse.status}).`
					);
				}

				if (!infoPayload) {
					throw new Error("La API devolvió una respuesta inválida para la información principal del dataset.");
				}

				if (isDisposed) {
					return;
				}

				setDataInfo(infoPayload);

				if (infoPayload.version.id !== activeVersionId) {
					onDatasetVersionChange?.(datasetId, infoPayload.version.id, infoPayload.version.version_number);
				}
			} catch (error) {
				if (signal.aborted || isDisposed) {
					return;
				}

				const message = error instanceof Error ? error.message : "Error desconocido al cargar la previsualización.";
				setErrorMessage(message);
			} finally {
				if (!isDisposed) {
					setIsLoadingDataInfo(false);
				}
			}
		};

		const plotRequests: Array<{
			key: VisualizationKey;
			path: string;
			errorLabel: string;
		}> = [
			{ key: "histplotAdr", path: "histplot-adr", errorLabel: "Histograma ADR" },
			{ key: "histplotAdrKde", path: "histplot-adr-kde", errorLabel: "Histograma ADR con KDE" },
			{ key: "pairplot", path: "pairplot", errorLabel: "Visualización de como se relacionan las variables" },
			{ key: "nullsHeatmap", path: "nulls-heatmap", errorLabel: "Visualizar nulos" },
			{ key: "cancelationsDistribution", path: "distribution-cancelaciones", errorLabel: "Distribución de cancelaciones" },
			{ key: "numericHistograms", path: "histogramas-numericos", errorLabel: "Seleccionar numéricas Histogramas" },
			{ key: "outlierBoxplots", path: "boxplots-outliers", errorLabel: "Boxplots para detectar outliers" },
			{ key: "cancelationsByHotel", path: "cancelaciones-por-hotel", errorLabel: "Comparar cancelados vs no cancelados por tipo de hotel" },
			{ key: "cancelationsByMonth", path: "cancelaciones-por-mes", errorLabel: "Cancelaciones por mes" },
			{ key: "leadTimeDistribution", path: "lead-time-distribution", errorLabel: "Distribución de lead time" },
			{ key: "adrByHotelAndCancellation", path: "adr-por-hotel-cancelacion", errorLabel: "ADR por tipo de hotel y cancelación" },
			{ key: "correlationWithTarget", path: "correlacion-variable-objetivo", errorLabel: "Correlación con variable objetivo" },
		];

		let pendingPlots = plotRequests.length;

		const completePlot = (key: VisualizationKey) => {
			if (isDisposed) {
				return;
			}

			setLoadingPlots((previous) => ({ ...previous, [key]: false }));
			pendingPlots -= 1;

			if (pendingPlots <= 0) {
				setIsLoadingVisualizations(false);
			}
		};

		const loadPlot = async (request: { key: VisualizationKey; path: string; errorLabel: string }) => {
			try {
				const response = await fetch(
					`/apim5/datasets-viewer/${datasetId}/versions/${selectedVersionId}/plots/${request.path}`,
					{ signal }
				);
				const payload = await parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(response);

				if (isDisposed) {
					return;
				}

				if (!response.ok) {
					appendWarning(payload?.detail ?? `No se pudo cargar la gráfica ${request.errorLabel} (HTTP ${response.status}).`);
					setVisualizations((previous) => ({ ...previous, [request.key]: "" }));
					return;
				}

				setVisualizations((previous) => ({
					...previous,
					[request.key]: payload?.plot ?? "",
				}));
			} catch (error) {
				if (signal.aborted || isDisposed) {
					return;
				}

				const message =
					error instanceof Error
						? `No se pudo cargar la gráfica ${request.errorLabel}: ${error.message}`
						: `No se pudo cargar la gráfica ${request.errorLabel}.`;
				appendWarning(message);
				setVisualizations((previous) => ({ ...previous, [request.key]: "" }));
			} finally {
				completePlot(request.key);
			}
		};

		void loadDataInfo();
		plotRequests.forEach((request) => {
			void loadPlot(request);
		});

		return () => {
			isDisposed = true;
			abortController.abort();
		};
	}, [activeDataset, selectedVersionId, onDatasetVersionChange]);

	useEffect(() => {
		if (versionError) {
			setErrorMessage(versionError);
		}
	}, [versionError]);

	const handleVersionChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
		const nextVersionId = Number(event.target.value);
		setSelectedVersionId(Number.isNaN(nextVersionId) ? null : nextVersionId);
	};

	const renderVisualizationCard = (title: string, key: VisualizationKey, alt: string) => (
		<section className="csv-info-card" key={key}>
			<h3>{title}</h3>
			{visualizations[key] ? (
				<img className="csv-plot-image" src={`data:image/png;base64,${visualizations[key]}`} alt={alt} />
			) : loadingPlots[key] ? (
				<p>Cargando gráfica...</p>
			) : (
				<p>No hay gráfica disponible para esta versión.</p>
			)}
		</section>
	);

	if (!activeDataset) {
		return (
			<section className="submenu-page csv-upload-page" aria-labelledby="previsualizar-lote-title">
				<div className="submenu-page-header">
					<span className="submenu-page-parent">Menu: Cargar data</span>
					<h2 id="previsualizar-lote-title">Previsualizar lote</h2>
					<p>Primero carga un dataset en el menú Importar CSV/Excel para habilitar esta vista.</p>
				</div>
			</section>
		);
	}

	return (
		<section className="submenu-page csv-upload-page" aria-labelledby="previsualizar-lote-title">
			<div className="submenu-page-header">
				<span className="submenu-page-parent">Menu: Cargar data</span>
				<h2 id="previsualizar-lote-title">Previsualizar lote</h2>
				<p>Explora versiones del dataset y revisa información tabular y distribuciones antes de entrenar.</p>
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
								onChange={handleVersionChange}
								disabled={isLoadingVersions || versions.length === 0}
							>
								{versions.map((version) => (
									<option key={version.id} value={version.id}>
										v{version.version_number} - filas: {version.row_count ?? "?"}, columnas: {version.column_count ?? "?"}
									</option>
								))}
							</select>
						</label>
					</div>

					<div className="csv-tabs" role="tablist" aria-label="Pestañas de previsualización">
						<button
							type="button"
							className={`csv-tab-button ${selectedTab === "data-info" ? "is-active" : ""}`}
							onClick={() => setSelectedTab("data-info")}
						>
							Data set Info
						</button>
						<button
							type="button"
							className={`csv-tab-button ${selectedTab === "visualizacion" ? "is-active" : ""}`}
							onClick={() => setSelectedTab("visualizacion")}
						>
							Visualización
						</button>
					</div>

					{errorMessage && <div className="csv-alert csv-alert--error">{errorMessage}</div>}
				</div>

				{selectedTab === "data-info" ? (
					<div className="csv-results">
						{isLoadingDataInfo && !dataInfo ? (
							<section className="csv-info-card">
								<div className="csv-loading-state" role="status" aria-live="polite" aria-busy="true">
									<span className="csv-loading-spinner" aria-hidden="true" />
									<p>Cargando datos de la versión seleccionada...</p>
								</div>
							</section>
						) : (
							<>
								<section className="csv-info-card">
									<h3>Resumen general</h3>
									<p>
										<strong>Versión seleccionada:</strong> {selectedVersion ? `v${selectedVersion.version_number}` : "-"}
									</p>
									<p>
										<strong>Shape:</strong> {dataInfo ? `${dataInfo.shape[0]} filas x ${dataInfo.shape[1]} columnas` : "-"}
									</p>
									<p>
										<strong>Columnas:</strong> {dataInfo?.columns.join(", ") ?? "-"}
									</p>
								</section>

								{dataInfo && <CsvTable title="df_reservas.head()" rows={dataInfo.head.rows} columns={dataInfo.head.columns} />}
								{dataInfo && <CsvTable title="df_reservas.tail()" rows={dataInfo.tail.rows} columns={dataInfo.tail.columns} />}

								<section className="csv-info-card">
									<h3>df_reservas.info()</h3>
									<pre className="csv-info-pre">{dataInfo?.info ?? "Sin información"}</pre>
								</section>

								{dataInfo && (
									<CsvTable
										title="df_reservas.transpose()"
										rows={dataInfo.transpose.rows}
										columns={dataInfo.transpose.columns}
									/>
								)}

								{dataInfo && (
									<CsvTable title="df_reservas.describe()" rows={dataInfo.describe.rows} columns={dataInfo.describe.columns} />
								)}
								{dataInfo && (
									<CsvTable
										title="df_reservas.describe().transpose()"
										rows={dataInfo.describe_transpose.rows}
										columns={dataInfo.describe_transpose.columns}
									/>
								)}
							</>
						)}
					</div>
				) : (
					<div className="csv-results">
						{isLoadingVisualizations && (
							<section className="csv-info-card">
								<div className="csv-loading-state" role="status" aria-live="polite" aria-busy="true">
									<span className="csv-loading-spinner" aria-hidden="true" />
									<p>Cargando visualizaciones de la versión seleccionada...</p>
								</div>
							</section>
						)}

						{renderVisualizationCard(
							"Visualización de la distribución de variables usando seaborn",
							"histplotAdr",
							"Histograma ADR"
						)}
						{renderVisualizationCard(
							"Visualización de la distribución con función de densidad",
							"histplotAdrKde",
							"Histograma ADR con KDE"
						)}
						{renderVisualizationCard(
							"Visualización de como se relacionan las variables",
							"pairplot",
							"Pairplot de variables"
						)}
						{renderVisualizationCard(
							"Comparar cancelados vs no cancelados por tipo de hotel",
							"cancelationsByHotel",
							"Cancelaciones por tipo de hotel"
						)}
						{renderVisualizationCard("Cancelaciones por mes", "cancelationsByMonth", "Cancelaciones por mes")}
						{renderVisualizationCard(
							"Distribución de lead time",
							"leadTimeDistribution",
							"Distribución de lead time"
						)}
						{renderVisualizationCard("Visualizar nulos", "nullsHeatmap", "Mapa de valores nulos")}
						{renderVisualizationCard(
							"Distribución de cancelaciones",
							"cancelationsDistribution",
							"Distribución de cancelaciones"
						)}
						{renderVisualizationCard(
							"Seleccionar numéricas Histogramas",
							"numericHistograms",
							"Histogramas de variables numéricas"
						)}
						{renderVisualizationCard(
							"Boxplots para detectar outliers",
							"outlierBoxplots",
							"Boxplots para detectar outliers"
						)}
						{renderVisualizationCard(
							"ADR por tipo de hotel y cancelación",
							"adrByHotelAndCancellation",
							"ADR por tipo de hotel y cancelación"
						)}
						{renderVisualizationCard(
							"Correlación con variable objetivo",
							"correlationWithTarget",
							"Matriz de correlación con variable objetivo"
						)}
					</div>
				)}
			</article>
		</section>
	);
}
