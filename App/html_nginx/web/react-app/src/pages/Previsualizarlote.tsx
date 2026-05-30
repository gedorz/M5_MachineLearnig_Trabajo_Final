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

type DistributionResponse = {
	plots: {
		histplot_adr: string;
		histplot_adr_kde: string;
	};
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
	const [distribution, setDistribution] = useState<DistributionResponse | null>(null);
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
			setDistribution(null);
			return;
		}

		const loadSelectedVersionData = async () => {
			setIsLoadingData(true);
			setErrorMessage("");

			try {
				const [infoResponse, plotsResponse] = await Promise.all([
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/data-info`),
					fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions/${selectedVersionId}/plots/distribution`),
				]);

				const [infoPayload, plotsPayload] = await Promise.all([
					parseJsonSafely<DataInfoResponse & ApiErrorResponse>(infoResponse),
					parseJsonSafely<DistributionResponse & ApiErrorResponse>(plotsResponse),
				]);

				if (!infoResponse.ok) {
					throw new Error(
						infoPayload?.detail ?? `No se pudo cargar la información del dataset (HTTP ${infoResponse.status}).`
					);
				}

				if (!plotsResponse.ok) {
					throw new Error(
						plotsPayload?.detail ?? `No se pudieron cargar las gráficas de distribución (HTTP ${plotsResponse.status}).`
					);
				}

				if (!infoPayload || !plotsPayload) {
					throw new Error("La API devolvió una respuesta inválida para la versión seleccionada.");
				}

				setDataInfo(infoPayload);
				setDistribution(plotsPayload);

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
						<p>Cargando datos de la versión seleccionada...</p>
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
							{distribution?.plots.histplot_adr ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${distribution.plots.histplot_adr}`}
									alt="Histograma ADR"
								/>
							) : (
								<p>No hay gráfica disponible para esta versión.</p>
							)}
						</section>

						<section className="csv-info-card">
							<h3>Visualización de la distribución con función de densidad</h3>
							{distribution?.plots.histplot_adr_kde ? (
								<img
									className="csv-plot-image"
									src={`data:image/png;base64,${distribution.plots.histplot_adr_kde}`}
									alt="Histograma ADR con KDE"
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
