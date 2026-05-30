import { useEffect, useMemo, useState } from "react";

export type DatasetContext = {
	datasetId: number;
	versionId: number;
	versionNumber: number;
	filename: string;
};

export type DatasetVersion = {
	id: number;
	version_number: number;
	created_at?: string;
	row_count?: number;
	column_count?: number;
};

type UseDatasetVersionsResult = {
	versions: DatasetVersion[];
	selectedVersionId: number | null;
	selectedVersion: DatasetVersion | null;
	isLoadingVersions: boolean;
	versionError: string;
	setSelectedVersionId: (versionId: number | null) => void;
	reloadVersions: () => Promise<void>;
};

export function useDatasetVersions(
	activeDataset: DatasetContext | null,
	onDatasetVersionChange?: (datasetId: number, versionId: number, versionNumber: number) => void,
): UseDatasetVersionsResult {
	const [versions, setVersions] = useState<DatasetVersion[]>([]);
	const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
	const [isLoadingVersions, setIsLoadingVersions] = useState(false);
	const [versionError, setVersionError] = useState("");

	const selectedVersion = useMemo(
		() => versions.find((version) => version.id === selectedVersionId) ?? null,
		[versions, selectedVersionId],
	);

	const reloadVersions = async () => {
		if (!activeDataset) {
			setVersions([]);
			setSelectedVersionId(null);
			setVersionError("");
			return;
		}

		setIsLoadingVersions(true);
		setVersionError("");

		try {
			const response = await fetch(`/apim5/datasets-viewer/${activeDataset.datasetId}/versions`);
			const payload = (await response.json()) as { versions: DatasetVersion[]; detail?: string };

			if (!response.ok) {
				throw new Error(payload.detail ?? "No se pudo cargar la lista de versiones.");
			}

			const sortedVersions = [...payload.versions].sort((a, b) => b.version_number - a.version_number);
			setVersions(sortedVersions);

			const requestedVersion = sortedVersions.find((version) => version.id === activeDataset.versionId);
			const currentSelection = sortedVersions.find((version) => version.id === selectedVersionId);
			const defaultVersion = currentSelection ?? requestedVersion ?? sortedVersions[0] ?? null;

			setSelectedVersionId(defaultVersion?.id ?? null);

			if (defaultVersion && defaultVersion.id !== activeDataset.versionId) {
				onDatasetVersionChange?.(activeDataset.datasetId, defaultVersion.id, defaultVersion.version_number);
			}
		} catch (error) {
			const message = error instanceof Error ? error.message : "Error desconocido al cargar versiones.";
			setVersionError(message);
		} finally {
			setIsLoadingVersions(false);
		}
	};

	useEffect(() => {
		void reloadVersions();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [activeDataset?.datasetId]);

	return {
		versions,
		selectedVersionId,
		selectedVersion,
		isLoadingVersions,
		versionError,
		setSelectedVersionId,
		reloadVersions,
	};
}