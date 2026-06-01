import React, { useState } from "react";
import type { ChangeEvent } from "react";
import CsvTable from "./components/CsvTable";

type CsvRow = Record<string, unknown>;

type DatasetVersion = {
	id: number;
	dataset_id: number;
	version_number: number;
	storage_path: string;
};

type DatasetRecord = {
	id: number;
	original_filename: string;
};

type CsvResponse = {
	dataset: DatasetRecord;
	version: DatasetVersion;
	head: CsvRow[];
	tail: CsvRow[];
	columns: string[];
	info: string;
};

type ImportarDatosPageProps = {
	onDatasetLoaded?: (dataset: {
		datasetId: number;
		versionId: number;
		versionNumber: number;
		filename: string;
	}) => void;
};

const API_URL = "/apim5/datasets/upload";

export default function ImportarDatosPage({ onDatasetLoaded }: ImportarDatosPageProps) {
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [errorMessage, setErrorMessage] = useState("");
	const [responseData, setResponseData] = useState<CsvResponse | null>(null);

	const hasData = Boolean(responseData && responseData.columns.length > 0);

	const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0] ?? null;
		setSelectedFile(file);
		setErrorMessage("");
		setResponseData(null);
	};

	const handleUpload = async () => {
		if (!selectedFile) {
			setErrorMessage("Selecciona un archivo CSV antes de cargarlo.");
			return;
		}

		setIsLoading(true);
		setErrorMessage("");
		setResponseData(null);

		try {
			const formData = new FormData();
			formData.append("file", selectedFile);

			const response = await fetch(API_URL, {
				method: "POST",
				body: formData
			});

			const payload = (await response.json()) as CsvResponse & { detail?: string };

			if (!response.ok) {
				throw new Error(payload.detail ?? "No se pudo cargar el CSV.");
			}

			setResponseData(payload);
			onDatasetLoaded?.({
				datasetId: payload.dataset.id,
				versionId: payload.version.id,
				versionNumber: payload.version.version_number,
				filename: payload.dataset.original_filename
			});
		} catch (error) {
			const message = error instanceof Error ? error.message : "Error desconocido al cargar el CSV.";
			setErrorMessage(message);
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<section className="submenu-page csv-upload-page" aria-labelledby="csv-upload-title">
			<div className="submenu-page-header">
				<span className="submenu-page-parent">Menu: Cargar data</span>
				<h2 id="csv-upload-title">Importar CSV / Excel</h2>
				<p>
					Carga un archivo CSV al endpoint <strong>/datasets/upload</strong> y revisa la respuesta JSON con vista previa.
				</p>
			</div>

			<article className="submenu-page-body csv-upload-body">
				<div className="csv-upload-panel">
					<div className="csv-upload-panel__controls">
						<label className="csv-file-picker">
							<span>Archivo CSV</span>
							<input type="file" accept=".csv,text/csv" onChange={handleFileChange} />
						</label>

						<button type="button" className="csv-upload-button" onClick={handleUpload} disabled={isLoading}>
							{isLoading ? "Cargando..." : "Cargar datos"}
						</button>
					</div>

					<div className="csv-upload-meta">
						<p>
							<strong>Archivo seleccionado:</strong> {selectedFile?.name ?? "Ninguno"}
						</p>
						<p>
							<strong>Endpoint:</strong> {API_URL}
						</p>
						{responseData && (
							<p>
								<strong>Dataset activo:</strong> #{responseData.dataset.id} v{responseData.version.version_number}
							</p>
						)}
					</div>

					{errorMessage && <div className="csv-alert csv-alert--error">{errorMessage}</div>}

					{responseData && (
						<div className="csv-alert csv-alert--success">
							Archivo procesado correctamente: {responseData.dataset.original_filename}
						</div>
					)}
				</div>

				{hasData ? (
					<div className="csv-results">
						<section className="csv-info-card">
							<h3>Columnas detectadas</h3>
							<div className="csv-columns-list">
								{responseData!.columns.map((column) => (
									<span key={column} className="csv-column-pill">
										{column}
									</span>
								))}
							</div>
						</section>

						<CsvTable title="Vista head" rows={responseData!.head} columns={responseData!.columns} />
						<CsvTable title="Vista tail" rows={responseData!.tail} columns={responseData!.columns} />

						<section className="csv-info-card">
							<h3>Info del DataFrame</h3>
							<pre className="csv-info-pre">{responseData!.info}</pre>
						</section>
					</div>
				) : (
					<div className="csv-empty-state">
						<h3>Vista previa vacía</h3>
						<p>Sube un CSV para mostrar aquí la tabla head, la tabla tail y las cabeceras devueltas por el API.</p>
					</div>
				)}
			</article>
		</section>
	);
}
