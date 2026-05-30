import base64
import io
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from fastapi import APIRouter, Depends, HTTPException, status

from dataBaseManagement.dbConectionPostgres import get_db_tasks
from .endpointsDatasets import DatasetServicesManager

router = APIRouter()
logger = logging.getLogger("api.endpointsDatasetsViewer")


def _figure_to_base64_png(figure: plt.Figure) -> str:
	buffer = io.BytesIO()
	figure.tight_layout()
	figure.savefig(buffer, format="png", dpi=120)
	plt.close(figure)
	return base64.b64encode(buffer.getvalue()).decode("utf-8")


@router.get("/datasets-viewer/{dataset_id}/versions")
def list_dataset_versions(dataset_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_versions_start dataset_id=%s", dataset_id)
	manager = DatasetServicesManager(db)
	try:
		versions = manager.get_versions(dataset_id)
		return {
			"dataset_id": dataset_id,
			"versions": versions,
		}
	except ValueError as exc:
		logger.warning("event=datasets_viewer_versions_not_found dataset_id=%s detail=%s", dataset_id, str(exc))
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/data-info")
def dataset_data_info(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_data_info_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	try:
		return manager.get_version_data_info(dataset_id, version_id)
	except ValueError as exc:
		logger.warning(
			"event=datasets_viewer_data_info_not_found dataset_id=%s version_id=%s detail=%s",
			dataset_id,
			version_id,
			str(exc),
		)
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	except Exception as exc:
		logger.exception(
			"event=datasets_viewer_data_info_error dataset_id=%s version_id=%s",
			dataset_id,
			version_id,
		)
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"No se pudo obtener data-info: {str(exc)}",
		)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/distribution")
def dataset_distribution_plots(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_plots_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)

	try:
		df_reservas, version = manager.get_dataframe_by_version(dataset_id, version_id)
	except ValueError as exc:
		logger.warning(
			"event=datasets_viewer_plots_not_found dataset_id=%s version_id=%s detail=%s",
			dataset_id,
			version_id,
			str(exc),
		)
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

	if "adr" not in df_reservas.columns:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="La columna 'adr' no existe en esta versión del dataset.",
		)

	hist_figure, hist_axis = plt.subplots(figsize=(8, 4.2))
	sns.histplot(df_reservas, x="adr", ax=hist_axis)
	hist_axis.set_title("Visualización de la distribución de variables usando seaborn")

	kde_figure, kde_axis = plt.subplots(figsize=(8, 4.2))
	sns.histplot(df_reservas, x="adr", kde=True, ax=kde_axis)
	kde_axis.set_title("Visualización de la distribución con función de densidad")

	return {
		"dataset_id": dataset_id,
		"version": version,
		"plots": {
			"histplot_adr": _figure_to_base64_png(hist_figure),
			"histplot_adr_kde": _figure_to_base64_png(kde_figure),
		},
	}
