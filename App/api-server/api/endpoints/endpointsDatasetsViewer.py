import base64
import io
import math
import logging
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
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


def _build_plot_response(dataset_id: int, version: dict[str, Any], figure: plt.Figure) -> dict[str, Any]:
	return {
		"dataset_id": dataset_id,
		"version": version,
		"plot": _figure_to_base64_png(figure),
	}


def _create_bar_countplot(df_reservas: pd.DataFrame, column_name: str, title: str) -> plt.Figure:
	if column_name not in df_reservas.columns:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"La columna '{column_name}' no existe en esta versión del dataset.",
		)

	column_name_formatted = column_name.replace("_", " ").title()
	figure, axis = plt.subplots(figsize=(8, 4.2))
	sns.countplot(data=df_reservas, x=column_name, ax=axis)
	axis.set_title(title)
	axis.set_xlabel(column_name_formatted)
	axis.set_ylabel("Frecuencia")
	return figure


def _create_numeric_histograms_figure(df_reservas: pd.DataFrame) -> plt.Figure:
	#num_cols = df_reservas.select_dtypes(include=["number"]).columns
	num_cols = df_reservas.select_dtypes(include=['int64', 'float64']).columns
	
	if len(num_cols) == 0:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="No hay columnas numéricas disponibles para generar histogramas.",
		)

	n_columns = 4 # Número de columnas para organizar los histogramas
	n_rows = math.ceil(len(num_cols) / n_columns)
	figure, axes = plt.subplots(n_rows, n_columns, figsize=(5 * n_columns, 4 * n_rows))
	axes_list = list(axes.flatten()) if hasattr(axes, "flatten") else [axes]

	for axis, column_name in zip(axes_list, num_cols):
		column_name_formatted = column_name.replace("_", " ").title()
		series = pd.to_numeric(df_reservas[column_name], errors="coerce").dropna()
		axis.hist(series, bins=30, color="steelblue", alpha=0.85)
		axis.set_title(column_name_formatted)
		axis.set_xlabel(column_name_formatted)
		axis.set_ylabel("Frecuencia")

	for axis in axes_list[len(num_cols):]:
		axis.set_axis_off()

	figure.tight_layout()
	return figure


def _prepare_boxplot_columns(df_reservas: pd.DataFrame, columns: list[str]) -> list[str]:
	missing_columns = [column for column in columns if column not in df_reservas.columns]
	# Solo se generan boxplots para las columnas que existen en el dataframe, pero se informa si alguna falta
	if missing_columns:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"Faltan columnas requeridas para boxplot: {', '.join(missing_columns)}.",
		)
	return columns


def _create_outliers_boxplots_figure(df_reservas: pd.DataFrame, columns: list[str]) -> plt.Figure:
	figure, axes = plt.subplots(len(columns), 1, figsize=(10, 4 * len(columns)))
	axes_list = [axes] if len(columns) == 1 else list(axes)

	for axis, column_name in zip(axes_list, columns):
		series = pd.to_numeric(df_reservas[column_name], errors="coerce").dropna()
		column_name_formatted = column_name.replace("_", " ").title()
		if series.empty:
			axis.text(0.5, 0.5, f"Sin datos numéricos válidos en '{column_name_formatted}'", ha="center", va="center")
			axis.set_title(f"Boxplot de {column_name_formatted}")
			axis.set_axis_off()
			continue

		q01 = series.quantile(0.01)
		q99 = series.quantile(0.99)
		if pd.notna(q01) and pd.notna(q99) and q01 < q99:
			plot_series = series[(series >= q01) & (series <= q99)]
		else:
			plot_series = series

		sns.boxplot(x=plot_series, ax=axis, showfliers=False)
		axis.set_title(f"Boxplot de {column_name_formatted} (rango p1-p99)")
		axis.set_xlabel(column_name_formatted)

	return figure


def _load_dataset_dataframe_or_404(manager: DatasetServicesManager, dataset_id: int, version_id: int):
	try:
		return manager.get_dataframe_by_version(dataset_id, version_id)
	except ValueError as exc:
		logger.warning(
			"event=datasets_viewer_plots_not_found dataset_id=%s version_id=%s detail=%s",
			dataset_id,
			version_id,
			str(exc),
		)
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _prepare_pairplot_dataframe(df_reservas):
	"""Reduce el dataframe para evitar timeouts en pairplot con datasets grandes."""
	numeric_df = df_reservas.select_dtypes(include=["number"]).copy()
	if numeric_df.empty:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="No hay columnas numéricas disponibles para generar el pairplot.",
		)

	max_columns = 6
	if "adr" in numeric_df.columns:
		selected_columns = ["adr", *[col for col in numeric_df.columns if col != "adr"][: max_columns - 1]]
	else:
		selected_columns = list(numeric_df.columns[:max_columns])

	reduced_df = numeric_df[selected_columns]
	max_rows = 2000
	if len(reduced_df) > max_rows:
		reduced_df = reduced_df.sample(n=max_rows, random_state=42)

	return reduced_df


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
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)

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


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/distribution-cancelaciones")
def dataset_distribution_cancelaciones(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_distribution_cancelaciones_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)
	figure = _create_bar_countplot(df_reservas, "is_canceled", "Distribución de Cancelaciones (0=No, 1=Sí)")
	return _build_plot_response(dataset_id, version, figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/histogramas-numericos")
def dataset_histogramas_numericos(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_histogramas_numericos_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)
	figure = _create_numeric_histograms_figure(df_reservas)
	figure.suptitle("Seleccionar numéricas Histogramas")
	return _build_plot_response(dataset_id, version, figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/boxplots-outliers")
def dataset_boxplots_outliers(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_boxplots_outliers_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)
	
	# Boxplots para detectar outliers
	columns = _prepare_boxplot_columns(df_reservas, ["lead_time", "adr", "booking_changes"])
	figure = _create_outliers_boxplots_figure(df_reservas, columns)

	return _build_plot_response(dataset_id, version, figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/histplot-adr")
def dataset_histplot_adr(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_histplot_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)

	if "adr" not in df_reservas.columns:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="La columna 'adr' no existe en esta versión del dataset.",
		)

	hist_figure, hist_axis = plt.subplots(figsize=(8, 4.2))
	sns.histplot(df_reservas, x="adr", ax=hist_axis)
	hist_axis.set_title("Visualización de la distribución de variables usando seaborn")

	return _build_plot_response(dataset_id, version, hist_figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/histplot-adr-kde")
def dataset_histplot_adr_kde(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_histplot_kde_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)

	if "adr" not in df_reservas.columns:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="La columna 'adr' no existe en esta versión del dataset.",
		)

	kde_figure, kde_axis = plt.subplots(figsize=(8, 4.2))
	sns.histplot(df_reservas, x="adr", kde=True, ax=kde_axis)
	kde_axis.set_title("Visualización de la distribución con función de densidad")

	return _build_plot_response(dataset_id, version, kde_figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/pairplot")
def dataset_pairplot(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_pairplot_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)

	try:
		pairplot_df = _prepare_pairplot_dataframe(df_reservas)
		pair_grid = sns.pairplot(pairplot_df)
		pair_grid.figure.suptitle("Visualización de como se relacionan las variables", y=1.02)
		pair_grid.figure.set_size_inches(10, 10)
	except Exception as exc:
		logger.exception(
			"event=datasets_viewer_pairplot_error dataset_id=%s version_id=%s",
			dataset_id,
			version_id,
		)
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"No se pudo generar el pairplot: {str(exc)}",
		)

	return _build_plot_response(dataset_id, version, pair_grid.figure)


@router.get("/datasets-viewer/{dataset_id}/versions/{version_id}/plots/nulls-heatmap")
def dataset_nulls_heatmap(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=datasets_viewer_nulls_heatmap_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	df_reservas, version = _load_dataset_dataframe_or_404(manager, dataset_id, version_id)

	nulls_figure, nulls_axis = plt.subplots(figsize=(12, 6))
	sns.heatmap(df_reservas.isnull(), yticklabels=False, cbar=False, cmap="viridis", ax=nulls_axis)
	nulls_axis.set_title("Mapa de valores nulos")

	return _build_plot_response(dataset_id, version, nulls_figure)
