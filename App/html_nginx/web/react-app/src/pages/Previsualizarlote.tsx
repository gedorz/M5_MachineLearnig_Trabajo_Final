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
	const [visualizations, setVisualizations] = useState<VisualizationsResponse | null>(null);
	const [errorMessage, setErrorMessage] = useState("");
	const [isLoadingData, setIsLoadingData] = useState(false);

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
			setVisualizations(null);
			return;
		}

		const loadSelectedVersionData = async () => {
			setIsLoadingData(true);
			setErrorMessage("");

			try {
				const warnings: string[] = [];
				const [
					infoResponse,
					histResponse,
					kdeResponse,
					pairplotResponse,
					nullsResponse,
					cancelationsResponse,
					numericHistogramsResponse,
					boxplotsResponse,
					cancelationsByHotelResponse,
					cancelationsByMonthResponse,
					leadTimeDistributionResponse,
					adrByHotelAndCancellationResponse,
					correlationWithTargetResponse,
				] = await Promise.all([
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/data-info`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/histplot-adr`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/histplot-adr-kde`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/pairplot`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/nulls-heatmap`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/distribution-cancelaciones`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/histogramas-numericos`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/boxplots-outliers`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/cancelaciones-por-hotel`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/cancelaciones-por-mes`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/lead-time-distribution`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/adr-por-hotel-cancelacion`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/correlacion-variable-objetivo`),
				]);

				const [
					infoPayload,
					histPayload,
					kdePayload,
					pairplotPayload,
					nullsPayload,
					cancelationsPayload,
					numericHistogramsPayload,
					boxplotsPayload,
					cancelationsByHotelPayload,
					cancelationsByMonthPayload,
					leadTimeDistributionPayload,
					adrByHotelAndCancellationPayload,
					correlationWithTargetPayload,
				] = await Promise.all([
					parseJsonSafely<DataInfoResponse & ApiErrorResponse>(infoResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(histResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(kdeResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(pairplotResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(nullsResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(cancelationsResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(numericHistogramsResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(boxplotsResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(cancelationsByHotelResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(cancelationsByMonthResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(leadTimeDistributionResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(adrByHotelAndCancellationResponse),
					parseJsonSafely<SinglePlotResponse & ApiErrorResponse>(correlationWithTargetResponse),
				]);

				if (!infoResponse.ok) {
					throw new Error(
						infoPayload?.detail ?? `No se pudo cargar la información del dataset (HTTP ${infoResponse.status}).`
					);
				}

				if (!infoPayload) {
					throw new Error("La API devolvió una respuesta inválida para la información principal del dataset.");
				}

				if (!histResponse.ok) {
					warnings.push(histPayload?.detail ?? `No se pudo cargar la gráfica Histograma ADR (HTTP ${histResponse.status}).`);
				}

				if (!kdeResponse.ok) {
					warnings.push(kdePayload?.detail ?? `No se pudo cargar la gráfica Histograma ADR con KDE (HTTP ${kdeResponse.status}).`);
				}

				if (!pairplotResponse.ok) {
					warnings.push(
						pairplotPayload?.detail ??
							`No se pudo cargar la gráfica Visualización de como se relacionan las variables (HTTP ${pairplotResponse.status}).`
					);
				}

				if (!nullsResponse.ok) {
					warnings.push(nullsPayload?.detail ?? `No se pudo cargar la gráfica Visualizar nulos (HTTP ${nullsResponse.status}).`);
				}

				if (!cancelationsResponse.ok) {
					warnings.push(
						cancelationsPayload?.detail ??
							`No se pudo cargar la gráfica Distribución de cancelaciones (HTTP ${cancelationsResponse.status}).`
					);
				}

				if (!numericHistogramsResponse.ok) {
					warnings.push(
						numericHistogramsPayload?.detail ??
							`No se pudo cargar la gráfica Seleccionar numéricas Histogramas (HTTP ${numericHistogramsResponse.status}).`
					);
				}

				if (!boxplotsResponse.ok) {
					warnings.push(
						boxplotsPayload?.detail ??
							`No se pudo cargar la gráfica Boxplots para detectar outliers (HTTP ${boxplotsResponse.status}).`
					);
				}

				if (!cancelationsByHotelResponse.ok) {
					warnings.push(
						cancelationsByHotelPayload?.detail ??
							`No se pudo cargar la gráfica Comparar cancelados vs no cancelados por tipo de hotel (HTTP ${cancelationsByHotelResponse.status}).`
					);
				}

				if (!cancelationsByMonthResponse.ok) {
					warnings.push(
						cancelationsByMonthPayload?.detail ??
							`No se pudo cargar la gráfica Cancelaciones por mes (HTTP ${cancelationsByMonthResponse.status}).`
					);
				}

				if (!leadTimeDistributionResponse.ok) {
					warnings.push(
						leadTimeDistributionPayload?.detail ??
							`No se pudo cargar la gráfica Distribución de lead time (HTTP ${leadTimeDistributionResponse.status}).`
					);
				}

				if (!adrByHotelAndCancellationResponse.ok) {
					warnings.push(
						adrByHotelAndCancellationPayload?.detail ??
							`No se pudo cargar la gráfica ADR por tipo de hotel y cancelación (HTTP ${adrByHotelAndCancellationResponse.status}).`
					);
				}

				if (!correlationWithTargetResponse.ok) {
					warnings.push(
						correlationWithTargetPayload?.detail ??
							`No se pudo cargar la gráfica Correlación con variable objetivo (HTTP ${correlationWithTargetResponse.status}).`
					);
				}

				setDataInfo(infoPayload);
				setVisualizations({
					histplotAdr: histResponse.ok && histPayload?.plot ? histPayload.plot : "",
					histplotAdrKde: kdeResponse.ok && kdePayload?.plot ? kdePayload.plot : "",
					pairplot: pairplotResponse.ok && pairplotPayload?.plot ? pairplotPayload.plot : "",
					nullsHeatmap: nullsResponse.ok && nullsPayload?.plot ? nullsPayload.plot : "",
					cancelationsDistribution: cancelationsResponse.ok && cancelationsPayload?.plot ? cancelationsPayload.plot : "",
					numericHistograms: numericHistogramsResponse.ok && numericHistogramsPayload?.plot ? numericHistogramsPayload.plot : "",
					outlierBoxplots: boxplotsResponse.ok && boxplotsPayload?.plot ? boxplotsPayload.plot : "",
					cancelationsByHotel:
						cancelationsByHotelResponse.ok && cancelationsByHotelPayload?.plot ? cancelationsByHotelPayload.plot : "",
					cancelationsByMonth:
						cancelationsByMonthResponse.ok && cancelationsByMonthPayload?.plot ? cancelationsByMonthPayload.plot : "",
					leadTimeDistribution:
						leadTimeDistributionResponse.ok && leadTimeDistributionPayload?.plot ? leadTimeDistributionPayload.plot : "",
					adrByHotelAndCancellation:
						adrByHotelAndCancellationResponse.ok && adrByHotelAndCancellationPayload?.plot
							? adrByHotelAndCancellationPayload.plot
							: "",
					correlationWithTarget:
						correlationWithTargetResponse.ok && correlationWithTargetPayload?.plot
							? correlationWithTargetPayload.plot
							: "",
				});
				setErrorMessage(warnings.join(" "));

				if (infoPayload.version.id !== activeDataset.versionId) {
					onDatasetVersionChange?.(
						activeDataset.datasetId,
						infoPayload.version.id,
						infoPayload.version.version_number
					);
				}
			} catch (error) {
				const message = error instanceof Error ? error.message : "Error desconocido al cargar la previsualización.";
				setErrorMessage(message);
				setVisualizations(null);
			} finally {
				setIsLoadingData(false);
			}
		};

		void loadSelectedVersionData();
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

				{isLoadingData ? (
					<section className="csv-info-card">
						<div className="csv-loading-state" role="status" aria-live="polite" aria-busy="true">
							<span className="csv-loading-spinner" aria-hidden="true" />
							<p>Cargando datos de la versión seleccionada...</p>
						</div>
					</section>
				) : selectedTab === "data-info" ? (
					<div className="csv-results">
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

						{dataInfo && <CsvTable title="df_reservas.describe()" rows={dataInfo.describe.rows} columns={dataInfo.describe.columns} />}
						{dataInfo && (
							<CsvTable
								title="df_reservas.describe().transpose()"
								rows={dataInfo.describe_transpose.rows}
								columns={dataInfo.describe_transpose.columns}
							/>
						)}
					</div>
				) : (
					<div className="csv-results">
						<section className="csv-info-card">
							<h3>Visualización de la distribución de variables usando seaborn</h3>
							{visualizations?.histplotAdr ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.histplotAdr}`}
									alt="Histograma ADR"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Visualización de la distribución con función de densidad</h3>
							{visualizations?.histplotAdrKde ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.histplotAdrKde}`}
									alt="Histograma ADR con KDE"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Visualización de como se relacionan las variables</h3>
							{visualizations?.pairplot ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.pairplot}`}
									alt="Pairplot de variables"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Comparar cancelados vs no cancelados por tipo de hotel</h3>
							{visualizations?.cancelationsByHotel ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.cancelationsByHotel}`}
									alt="Cancelaciones por tipo de hotel"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Cancelaciones por mes</h3>
							{visualizations?.cancelationsByMonth ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.cancelationsByMonth}`}
									alt="Cancelaciones por mes"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Distribución de lead time</h3>
							{visualizations?.leadTimeDistribution ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.leadTimeDistribution}`}
									alt="Distribución de lead time"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Visualizar nulos</h3>
							{visualizations?.nullsHeatmap ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.nullsHeatmap}`}
									alt="Mapa de valores nulos"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>
						
						<section className="csv-info-card">
							<h3>Distribución de cancelaciones</h3>
							{visualizations?.cancelationsDistribution ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.cancelationsDistribution}`}
									alt="Distribución de cancelaciones"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Seleccionar numéricas Histogramas</h3>
							{visualizations?.numericHistograms ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.numericHistograms}`}
									alt="Histogramas de variables numéricas"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Boxplots para detectar outliers</h3>
							{visualizations?.outlierBoxplots ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.outlierBoxplots}`}
									alt="Boxplots para detectar outliers"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>ADR por tipo de hotel y cancelación</h3>
							{visualizations?.adrByHotelAndCancellation ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.adrByHotelAndCancellation}`}
									alt="ADR por tipo de hotel y cancelación"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Correlación con variable objetivo</h3>
							{visualizations?.correlationWithTarget ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${visualizations.correlationWithTarget}`}
									alt="Matriz de correlación con variable objetivo"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>


					</div>
				)}
			</article>
		</section>
	);
}
