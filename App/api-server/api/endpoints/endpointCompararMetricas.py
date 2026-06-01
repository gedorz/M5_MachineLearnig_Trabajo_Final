from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import cross_val_score, train_test_split

from dataBaseManagement.dbConectionPostgres import get_db_tasks
from dataBaseManagement.dbManagement import get_rows_by_condition_Generic
from .endPointFeatures import _apply_plan_in_memory
from .endpointContratos import FeaturePlanCreateRequest
from .endpointsDatasets import DATASET_OPERATION_TABLE, DatasetServicesManager

router = APIRouter()
logger = logging.getLogger("api.endpointCompararMetricas")

FEATURE_PLAN_OPERATION = "feature_plan_v1"
AUTO_ML_OPERATION = "automl_train_feature_plan_v1"


def _load_latest_automl_operation(db: Any, dataset_id: int, version_id: int, plan_id: int | None) -> dict[str, Any]:
	rows = get_rows_by_condition_Generic(
		DATASET_OPERATION_TABLE,
		"dataset_id = %s AND dataset_version_id = %s AND operation_name = %s ORDER BY created_at DESC LIMIT 50",
		[dataset_id, version_id, AUTO_ML_OPERATION],
		connection=db,
	)

	if not rows:
		raise ValueError(
			"No hay entrenamiento AutoML guardado para el dataset/versión seleccionados. "
			"Ejecuta 'Lanzar AutoML' con un Feature Plan primero."
		)

	if plan_id is None:
		return rows[0]

	for row in rows:
		params = row.get("parameters_json") or {}
		if params.get("plan_id") == plan_id:
			return row

	raise ValueError(
		f"No se encontró entrenamiento AutoML guardado para el plan_id={plan_id} en la versión seleccionada."
	)


def _load_feature_plan(db: Any, dataset_id: int, version_id: int, plan_id: int | None) -> FeaturePlanCreateRequest:
	if plan_id is None:
		raise ValueError(
			"El entrenamiento seleccionado no tiene plan_id guardado. "
			"Ejecuta AutoML usando un Feature Plan persistido."
		)

	rows = get_rows_by_condition_Generic(
		DATASET_OPERATION_TABLE,
		"id = %s AND dataset_id = %s AND dataset_version_id = %s AND operation_name = %s",
		[plan_id, dataset_id, version_id, FEATURE_PLAN_OPERATION],
		connection=db,
	)

	if not rows:
		raise ValueError(
			f"No se encontró Feature Plan con id={plan_id} para el dataset/versión seleccionados."
		)

	parameters = rows[0].get("parameters_json") or {}
	plan_dict = parameters.get("plan") or {}
	if not plan_dict:
		raise ValueError("El Feature Plan guardado no contiene configuración de plan.")

	return FeaturePlanCreateRequest(**plan_dict)


def _extract_models(train_results: dict[str, Any]) -> dict[str, dict[str, Any]]:
	models = train_results.get("models")
	if not isinstance(models, dict) or not models:
		raise ValueError("El entrenamiento guardado no contiene modelos para comparar.")
	return models


def _safe_float(value: Any) -> float | None:
	try:
		if value is None:
			return None
		return float(value)
	except (TypeError, ValueError):
		return None


def _score_model_diagnostics(
	model: Any,
	X_train: pd.DataFrame,
	y_train: pd.Series,
	X_val: pd.DataFrame,
	y_val: pd.Series,
	primary_metric: str,
) -> dict[str, Any]:
	y_pred = model.predict(X_val)
	precision, recall, f1, support = precision_recall_fscore_support(
		y_val,
		y_pred,
		labels=[0, 1],
		zero_division=0,
	)

	fold_scores: list[float] = []
	try:
		scores = cross_val_score(
			model,
			X_train,
			y_train,
			cv=3,
			scoring=primary_metric,
			n_jobs=1,
		)
		fold_scores = [float(value) for value in scores.tolist()]
	except Exception as exc:
		logger.warning("event=comparar_metricas_cv_warning metric=%s detail=%s", primary_metric, str(exc))

	stability = {
		"fold_scores": fold_scores,
		"mean": float(np.mean(fold_scores)) if fold_scores else None,
		"std": float(np.std(fold_scores)) if fold_scores else None,
		"folds": len(fold_scores),
	}

	return {
		"precision_recall_by_class": [
			{
				"class": 0,
				"precision": float(precision[0]),
				"recall": float(recall[0]),
				"f1": float(f1[0]),
				"support": int(support[0]),
			},
			{
				"class": 1,
				"precision": float(precision[1]),
				"recall": float(recall[1]),
				"f1": float(f1[1]),
				"support": int(support[1]),
			},
		],
		"stability": stability,
	}


def build_comparar_metricas_result(
	*,
	db: Any,
	dataset_id: int,
	version_id: int,
	primary_metric: str | None,
	plan_id: int | None,
) -> dict[str, Any]:
	manager = DatasetServicesManager(db)
	version = manager._get_version(dataset_id, version_id)
	automl_op = _load_latest_automl_operation(db, dataset_id, version_id, plan_id)

	params = automl_op.get("parameters_json") or {}
	train_results = params.get("train_results") or {}
	request_params = params.get("request") or {}
	resolved_plan_id = params.get("plan_id")

	metric_to_sort = primary_metric or request_params.get("primary_metric") or "roc_auc"
	feature_plan = _load_feature_plan(db, dataset_id, version_id, resolved_plan_id)

	df_source = pd.read_csv(Path(version["storage_path"]))
	train_df, summary = _apply_plan_in_memory(df_source, feature_plan)

	X = train_df.drop(columns=[feature_plan.target_col])
	y = train_df[feature_plan.target_col]
	test_size = float(request_params.get("test_size", 0.2))
	random_state = int(request_params.get("random_state", 42))

	X_train, X_val, y_train, y_val = train_test_split(
		X,
		y,
		test_size=test_size,
		random_state=random_state,
		stratify=y if len(np.unique(y)) > 1 else None,
	)

	model_entries: list[dict[str, Any]] = []
	models = _extract_models(train_results)

	for model_name, model_info in models.items():
		path_value = model_info.get("path")
		metrics = model_info.get("metrics") or {}

		entry: dict[str, Any] = {
			"model": model_name,
			"path": path_value,
			"metrics": metrics,
			"ranking_metric": _safe_float(metrics.get(metric_to_sort)),
			"precision_recall_by_class": [],
			"stability": {
				"fold_scores": [],
				"mean": None,
				"std": None,
				"folds": 0,
			},
			"notes": [],
		}

		if not isinstance(path_value, str) or not path_value:
			entry["notes"].append("Sin ruta de modelo guardada.")
			model_entries.append(entry)
			continue

		model_path = Path(path_value)
		if not model_path.exists():
			entry["notes"].append(f"No se encontró archivo del modelo en ruta: {model_path}")
			model_entries.append(entry)
			continue

		if model_path.suffix == ".keras":
			entry["notes"].append("Diagnóstico por clase/folds no disponible para modelos .keras en esta vista.")
			model_entries.append(entry)
			continue

		try:
			loaded_model = joblib.load(model_path)
			diagnostics = _score_model_diagnostics(
				loaded_model,
				X_train,
				y_train,
				X_val,
				y_val,
				metric_to_sort,
			)
			entry.update(diagnostics)
			if entry["ranking_metric"] is None:
				entry["ranking_metric"] = diagnostics["stability"]["mean"]
		except Exception as exc:
			entry["notes"].append(f"No se pudo calcular diagnóstico del modelo: {str(exc)}")

		model_entries.append(entry)

	ranked = sorted(
		model_entries,
		key=lambda item: item.get("ranking_metric") if item.get("ranking_metric") is not None else float("-inf"),
		reverse=True,
	)

	for index, item in enumerate(ranked, start=1):
		item["rank"] = index

	return {
		"dataset_id": dataset_id,
		"version_id": version_id,
		"plan_id": resolved_plan_id,
		"operation_id": int(automl_op["id"]),
		"primary_metric": metric_to_sort,
		"feature_summary": summary.dict(),
		"models_ranked": ranked,
		"checklist": {
			"ordered_by_primary_metric": len(ranked) > 0,
			"precision_recall_by_class": any(len(model["precision_recall_by_class"]) == 2 for model in ranked),
			"stability_between_folds": any(model["stability"].get("folds", 0) > 1 for model in ranked),
		},
	}


@router.get("/comparar-metricas/{dataset_id}/versions/{version_id}")
def comparar_metricas(
	dataset_id: int,
	version_id: int,
	primary_metric: str | None = Query(default=None),
	plan_id: int | None = Query(default=None),
	db=Depends(get_db_tasks),
):
	logger.info(
		"event=comparar_metricas_start dataset_id=%s version_id=%s primary_metric=%s plan_id=%s",
		dataset_id,
		version_id,
		primary_metric,
		plan_id,
	)
	try:
		return build_comparar_metricas_result(
			db=db,
			dataset_id=dataset_id,
			version_id=version_id,
			primary_metric=primary_metric,
			plan_id=plan_id,
		)
	except ValueError as exc:
		logger.warning("event=comparar_metricas_invalid detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
	except FileNotFoundError as exc:
		logger.warning("event=comparar_metricas_file_not_found detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	except Exception as exc:
		logger.exception("event=comparar_metricas_error dataset_id=%s version_id=%s", dataset_id, version_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
