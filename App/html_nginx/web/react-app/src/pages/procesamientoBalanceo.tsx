import React, { useState } from "react";
import { type DatasetContext, useDatasetVersions } from "./hooks/useDatasetVersions";

type NullSummaryResponse = {
	dataset_id: number;
	version: {
		id: number;
		version_number: number;
	};
	nulls: Record<string, number>;
	row_count: number;
};

type LowercaseResponse = {
	dataset_id: number;
	version: {
		id: number;
		version_number: number;
	};
	source_version: {
		id: number;
		version_number: number;
	};
	columns: string[];
};

type ProcesamientoBalanceoProps = {
	activeDataset: DatasetContext | null;
	onDatasetVersionChange?: (datasetId: number, versionId: number, versionNumber: number) => void;
};

export default function ProcesamientoBalanceoPage({ activeDataset, onDatasetVersionChange }: ProcesamientoBalanceoProps) {
	const [isRunning, setIsRunning] = useState(false);
	const [errorMessage, setErrorMessage] = useState("");
	const [nullSummary, setNullSummary] = useState<NullSummaryResponse | null>(null);
	const [lowercaseResult, setLowercaseResult] = useState<LowercaseResponse | null>(null);

	const {
		versions,
		selectedVersionId,
		selectedVersion,
		isLoadingVersions,
		versionError,
		setSelectedVersionId,
		reloadVersions,
	} = useDatasetVersions(activeDataset, onDatasetVersionChange);

	const hasDataset = Boolean(activeDataset);
    const hasSelectedVersion = Boolean(selectedVersionId);

	const effectiveError = errorMessage || versionError;

	const handleRun = async () => {
		if (!activeDataset || !selectedVersionId) {
			setErrorMessage("Primero carga un dataset en Importar CSV/Excel.");
			return;
		}

		setIsRunning(true);
		setErrorMessage("");
		setNullSummary(null);
		setLowercaseResult(null);

		try {
			const nullSummaryResponse = await fetch(
				`/apim5/datasets/${activeDataset.datasetId}/versions/${selectedVersionId}/null-summary`
			);
			const nullSummaryPayload = (await nullSummaryResponse.json()) as NullSummaryResponse & { detail?: string };

			if (!nullSummaryResponse.ok) {
				throw new Error(nullSummaryPayload.detail ?? "No se pudo calcular el resumen de nulos.");
			}

			setNullSummary(nullSummaryPayload);

			const lowercaseResponse = await fetch(
				`/apim5/datasets/${activeDataset.datasetId}/versions/${selectedVersionId}/lowercase-columns`,
				{ method: "POST" }
			);
			const lowercasePayload = (await lowercaseResponse.json()) as LowercaseResponse & { detail?: string };

			if (!lowercaseResponse.ok) {
				throw new Error(lowercasePayload.detail ?? "No se pudieron normalizar las columnas.");
			}

			setLowercaseResult(lowercasePayload);
			onDatasetVersionChange?.(
				lowercasePayload.dataset_id,
				lowercasePayload.version.id,
				lowercasePayload.version.version_number
			);
			await reloadVersions();
			setSelectedVersionId(lowercasePayload.version.id);
		} catch (error) {
			const message = error instanceof Error ? error.message : "Error desconocido al procesar el dataset.";
			setErrorMessage(message);
		} finally {
			setIsRunning(false);
		}
	};

	return (
		<section className="submenu-page csv-upload-page" aria-labelledby="balance-title">
			<div className="submenu-page-header">
				<span className="submenu-page-parent">Menu: Cargar data</span>
				<h2 id="balance-title">Preprocesamiento y balanceo</h2>
				<p>
					Ejecuta el resumen de nulos y la normalización de cabeceras sobre el dataset activo para preparar el siguiente paso.
				</p>
			</div>

			<article className="submenu-page-body csv-upload-body">
				<div className="csv-upload-panel">
					<div className="csv-upload-meta">
						<p>
							<strong>Dataset activo:</strong> {activeDataset ? `#${activeDataset.datasetId} (${activeDataset.filename})` : "Ninguno"}
						</p>
						<p>
							<strong>Archivo:</strong> {activeDataset?.filename ?? "Sin archivo cargado"}
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

					<button type="button" className="csv-upload-button" onClick={handleRun} disabled={isRunning || !hasDataset || !hasSelectedVersion}>
						{isRunning ? "Procesando..." : "Ejecutar nulos + lowercase"}
					</button>

					{effectiveError && <div className="csv-alert csv-alert--error">{effectiveError}</div>}
				</div>

				<div className="csv-results">
					<section className="csv-info-card">
						<h3>Resumen de nulos</h3>
						{nullSummary ? (
							<pre className="csv-info-pre">{JSON.stringify(nullSummary.nulls, null, 2)}</pre>
						) : (
							<p>Ejecuta el botón para calcular `isna().sum()` sobre la versión activa.</p>
						)}
					</section>

					<section className="csv-info-card">
						<h3>Versión normalizada</h3>
						{lowercaseResult ? (
							<div>
								<p>
									Nueva versión: <strong>v{lowercaseResult.version.version_number}</strong>
								</p>
								<p>Columnas: {lowercaseResult.columns.join(", ")}</p>
							</div>
						) : (
							<p>Ejecuta el botón para aplicar `df_reservas.columns = df_reservas.columns.str.lower()`.</p>
						)}
					</section>
				</div>
			</article>
		</section>
	);
}
