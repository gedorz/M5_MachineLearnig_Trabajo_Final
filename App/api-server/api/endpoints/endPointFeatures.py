from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extras import Json

from dataBaseManagement.dbConectionPostgres import get_db_tasks
from dataBaseManagement.dbManagement import get_rows_by_condition_Generic, insert_record_Generic
from .endpointContratos import (
	FeaturePlanApplyRequest,
	FeaturePlanApplyResponse,
	FeaturePlanAutoMLRequest,
	FeaturePlanCreateRequest,
	FeaturePlanCreateResponse,
	FeaturePlanGetResponse,
	FeaturePlanSummary,
	FeatureProfileItem,
	FeatureProfileResponse,
)
from .endpointsDatasets import DATASET_OPERATION_TABLE, DATASET_VERSION_TABLE, DatasetServicesManager

router = APIRouter()
logger = logging.getLogger("api.endPointFeatures")

DEFAULT_TARGET_COLUMN = "is_canceled"
DEFAULT_LEAKAGE_COLUMNS = ["reservation_status", "reservation_status_date"]
FEATURE_PLAN_OPERATION = "feature_plan_v1"
APPLY_FEATURE_PLAN_OPERATION = "apply_feature_plan_v1"


def _resolve_version(manager: DatasetServicesManager, dataset_id: int, version_id: int | None) -> dict[str, Any]:
	return manager._get_latest_version(dataset_id) if version_id is None else manager._get_version(dataset_id, version_id)


def _feature_summary_from_dataframe(
	df: pd.DataFrame,
	target_col: str,
	include_features: list[str],
	exclude_features: list[str],
	derived_features: list[str],
) -> FeaturePlanSummary:
	available_cols = set(df.columns.tolist())

	if include_features:
		selected = [feature for feature in include_features if feature in available_cols and feature != target_col]
	else:
		selected = [feature for feature in df.columns.tolist() if feature != target_col]

	selected = [feature for feature in selected if feature not in set(exclude_features)]

	return FeaturePlanSummary(
		target_col=target_col,
		selected_features=selected,
		excluded_features=sorted(set(exclude_features)),
		derived_features=sorted(set(derived_features)),
		leakage_columns_present=[col for col in DEFAULT_LEAKAGE_COLUMNS if col in df.columns],
	)


def _build_profile(dataset_id: int, version_id: int, df: pd.DataFrame) -> FeatureProfileResponse:
	features: list[FeatureProfileItem] = []

	for col in df.columns.tolist():
		series = df[col]
		is_numeric = bool(pd.api.types.is_numeric_dtype(series))
		suggested_role = "candidate"
		if col == DEFAULT_TARGET_COLUMN:
			suggested_role = "target"
		elif col in DEFAULT_LEAKAGE_COLUMNS:
			suggested_role = "exclude_leakage"

		features.append(
			FeatureProfileItem(
				name=col,
				dtype=str(series.dtype),
				null_count=int(series.isna().sum()),
				null_ratio=float(series.isna().mean()),
				unique_count=int(series.nunique(dropna=True)),
				is_numeric=is_numeric,
				suggested_role=suggested_role,
			)
		)

	return FeatureProfileResponse(
		dataset_id=dataset_id,
		version_id=version_id,
		row_count=int(df.shape[0]),
		target_candidates=[DEFAULT_TARGET_COLUMN] if DEFAULT_TARGET_COLUMN in df.columns else [],
		leakage_suggestions=[col for col in DEFAULT_LEAKAGE_COLUMNS if col in df.columns],
		features=features,
	)


def _resolve_latest_plan(
	db: Any,
	dataset_id: int,
	version_id: int,
	plan_id: int | None = None,
) -> dict[str, Any] | None:
	if plan_id is not None:
		rows = get_rows_by_condition_Generic(
			DATASET_OPERATION_TABLE,
			"id = %s AND operation_name = %s",
			[plan_id, FEATURE_PLAN_OPERATION],
			connection=db,
		)
		return rows[0] if rows else None

	rows = get_rows_by_condition_Generic(
		DATASET_OPERATION_TABLE,
		"dataset_id = %s AND dataset_version_id = %s AND operation_name = %s ORDER BY created_at DESC LIMIT 1",
		[dataset_id, version_id, FEATURE_PLAN_OPERATION],
		connection=db,
	)
	return rows[0] if rows else None


def _normalize_plan(dataset_id: int, version_id: int, plan: FeaturePlanCreateRequest) -> FeaturePlanCreateRequest:
	normalized_data = plan.dict()
	normalized_data["dataset_id"] = dataset_id
	normalized_data["version_id"] = version_id
	return FeaturePlanCreateRequest(**normalized_data)


def _apply_plan_in_memory(df: pd.DataFrame, plan: FeaturePlanCreateRequest) -> tuple[pd.DataFrame, FeaturePlanSummary]:
	if plan.target_col not in df.columns:
		raise ValueError(f"La columna objetivo '{plan.target_col}' no existe en esta versión del dataset")

	work_df = df.copy()

	# 1) derivadas
	derived_names: list[str] = []
	for derived in plan.derived_features:
		if derived.name == plan.target_col:
			raise ValueError("Una variable derivada no puede llamarse igual que la variable objetivo")
		try:
			work_df[derived.name] = work_df.eval(derived.expression, engine="python")
		except Exception as exc:
			raise ValueError(
				f"No se pudo crear la variable derivada '{derived.name}' con expresión '{derived.expression}': {str(exc)}"
			)
		derived_names.append(derived.name)

	# 2) selección base
	if plan.include_features:
		selected = [col for col in plan.include_features if col in work_df.columns and col != plan.target_col]
	else:
		selected = [col for col in work_df.columns if col != plan.target_col]

	# 3) exclusión explícita
	selected = [col for col in selected if col not in set(plan.exclude_features)]

	# 4) garantizar derivadas incluidas si no fueron excluidas
	for derived_name in derived_names:
		if derived_name not in selected and derived_name not in set(plan.exclude_features):
			selected.append(derived_name)

	if not selected:
		raise ValueError("El Feature Plan dejó cero variables predictoras. Ajusta include/exclude/derived.")

	final_columns = [*selected, plan.target_col]
	final_df = work_df.loc[:, final_columns].copy()

	summary = _feature_summary_from_dataframe(
		work_df,
		target_col=plan.target_col,
		include_features=selected,
		exclude_features=plan.exclude_features,
		derived_features=derived_names,
	)
	return final_df, summary


def _load_train_models_function():
	if "/src" not in sys.path:
		sys.path.insert(0, "/src")
	if "/" not in sys.path:
		sys.path.insert(0, "/")

	repo_root = Path(__file__).resolve().parents[4]
	if str(repo_root) not in sys.path:
		sys.path.insert(0, str(repo_root))

	from src.model_trainer import train_models  # noqa: WPS433

	return train_models


@router.get("/features/profile/{dataset_id}/versions/{version_id}", response_model=FeatureProfileResponse)
def feature_profile(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=feature_profile_start dataset_id=%s version_id=%s", dataset_id, version_id)
	manager = DatasetServicesManager(db)
	try:
		df, _version = manager.get_dataframe_by_version(dataset_id, version_id)
		return _build_profile(dataset_id, version_id, df)
	except ValueError as exc:
		logger.warning("event=feature_profile_not_found dataset_id=%s version_id=%s detail=%s", dataset_id, version_id, str(exc))
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	except Exception as exc:
		logger.exception("event=feature_profile_error dataset_id=%s version_id=%s", dataset_id, version_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/features/plan", response_model=FeaturePlanCreateResponse, status_code=status.HTTP_201_CREATED)
def create_feature_plan(request: FeaturePlanCreateRequest, db=Depends(get_db_tasks)):
	logger.info("event=feature_plan_create_start dataset_id=%s version_id=%s", request.dataset_id, request.version_id)
	manager = DatasetServicesManager(db)
	try:
		version = _resolve_version(manager, request.dataset_id, request.version_id)
		df = pd.read_csv(Path(version["storage_path"]))
		normalized = _normalize_plan(request.dataset_id, int(version["id"]), request)

		if normalized.target_col not in df.columns:
			raise ValueError(f"La columna objetivo '{normalized.target_col}' no existe en el dataset")

		# valida aplicación en memoria (incluye derivadas y selección)
		_, summary = _apply_plan_in_memory(df, normalized)

		op_row = insert_record_Generic(
			DATASET_OPERATION_TABLE,
			{
				"dataset_id": request.dataset_id,
				"dataset_version_id": int(version["id"]),
				"operation_name": FEATURE_PLAN_OPERATION,
				"parameters_json": Json({"plan": normalized.dict(), "summary": summary.dict()}),
			},
			connection=db,
		)

		logger.info(
			"event=feature_plan_create_success dataset_id=%s version_id=%s plan_id=%s",
			request.dataset_id,
			version["id"],
			op_row["id"],
		)

		return FeaturePlanCreateResponse(
			plan_id=int(op_row["id"]),
			operation_name=FEATURE_PLAN_OPERATION,
			dataset_id=request.dataset_id,
			version_id=int(version["id"]),
			summary=summary,
		)
	except ValueError as exc:
		logger.warning("event=feature_plan_create_invalid detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
	except Exception as exc:
		logger.exception("event=feature_plan_create_error dataset_id=%s", request.dataset_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/features/plan/{dataset_id}/versions/{version_id}/latest", response_model=FeaturePlanGetResponse)
def get_latest_feature_plan(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
	logger.info("event=feature_plan_latest_start dataset_id=%s version_id=%s", dataset_id, version_id)
	try:
		row = _resolve_latest_plan(db, dataset_id, version_id, plan_id=None)
		if not row:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="No existe Feature Plan para el dataset/version solicitados",
			)

		parameters = row.get("parameters_json") or {}
		plan_dict = parameters.get("plan") or {}
		summary_dict = parameters.get("summary") or {}

		return FeaturePlanGetResponse(
			plan_id=int(row["id"]),
			dataset_id=int(row["dataset_id"]),
			version_id=int(row["dataset_version_id"]),
			created_at=str(row.get("created_at")),
			plan=FeaturePlanCreateRequest(**plan_dict),
			summary=FeaturePlanSummary(**summary_dict),
		)
	except HTTPException:
		raise
	except Exception as exc:
		logger.exception("event=feature_plan_latest_error dataset_id=%s version_id=%s", dataset_id, version_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/features/apply", response_model=FeaturePlanApplyResponse, status_code=status.HTTP_201_CREATED)
def apply_feature_plan(request: FeaturePlanApplyRequest, db=Depends(get_db_tasks)):
	logger.info("event=feature_plan_apply_start dataset_id=%s version_id=%s", request.dataset_id, request.version_id)
	manager = DatasetServicesManager(db)
	try:
		base_version = _resolve_version(manager, request.dataset_id, request.version_id)
		df = pd.read_csv(Path(base_version["storage_path"]))

		if request.plan is not None:
			plan = _normalize_plan(request.dataset_id, int(base_version["id"]), request.plan)
			plan_id_for_metadata = None
		else:
			stored_plan_row = _resolve_latest_plan(db, request.dataset_id, int(base_version["id"]), plan_id=request.plan_id)
			if not stored_plan_row:
				raise ValueError("No se encontró Feature Plan para aplicar. Proporciona plan_id válido o plan inline.")

			parameters = stored_plan_row.get("parameters_json") or {}
			plan_dict = parameters.get("plan") or {}
			plan = FeaturePlanCreateRequest(**plan_dict)
			plan_id_for_metadata = int(stored_plan_row["id"])

		transformed_df, summary = _apply_plan_in_memory(df, plan)

		next_version_number = int(base_version["version_number"]) + 1
		new_version_path = manager._build_version_path(request.dataset_id, next_version_number)
		transformed_df.to_csv(new_version_path, index=False)

		version_row = insert_record_Generic(
			DATASET_VERSION_TABLE,
			{
				"dataset_id": request.dataset_id,
				"version_number": next_version_number,
				"parent_version_id": int(base_version["id"]),
				"storage_path": str(new_version_path),
				"row_count": int(transformed_df.shape[0]),
				"column_count": int(transformed_df.shape[1]),
				"columns_json": Json(transformed_df.columns.tolist()),
			},
			connection=db,
		)

		insert_record_Generic(
			DATASET_OPERATION_TABLE,
			{
				"dataset_id": request.dataset_id,
				"dataset_version_id": int(version_row["id"]),
				"operation_name": APPLY_FEATURE_PLAN_OPERATION,
				"parameters_json": Json(
					{
						"source_version_id": int(base_version["id"]),
						"plan_id": plan_id_for_metadata,
						"plan": plan.dict(),
						"summary": summary.dict(),
					}
				),
			},
			connection=db,
		)

		return FeaturePlanApplyResponse(
			dataset_id=request.dataset_id,
			source_version_id=int(base_version["id"]),
			new_version_id=int(version_row["id"]),
			new_version_number=int(version_row["version_number"]),
			storage_path=str(new_version_path),
			summary=summary,
		)
	except ValueError as exc:
		logger.warning("event=feature_plan_apply_invalid detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
	except Exception as exc:
		logger.exception("event=feature_plan_apply_error dataset_id=%s", request.dataset_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/features/automl/train")
def train_with_feature_plan(request: FeaturePlanAutoMLRequest, db=Depends(get_db_tasks)):
	logger.info(
		"event=feature_automl_train_start dataset_id=%s version_id=%s plan_id=%s",
		request.dataset_id,
		request.version_id,
		request.plan_id,
	)
	manager = DatasetServicesManager(db)
	try:
		version = _resolve_version(manager, request.dataset_id, request.version_id)
		df = pd.read_csv(Path(version["storage_path"]))

		if request.plan is not None:
			plan = _normalize_plan(request.dataset_id, int(version["id"]), request.plan)
			resolved_plan_id = None
		else:
			stored_plan_row = _resolve_latest_plan(db, request.dataset_id, int(version["id"]), plan_id=request.plan_id)
			if not stored_plan_row:
				raise ValueError("No se encontró Feature Plan para entrenar. Guarda un plan primero o envía plan inline.")
			parameters = stored_plan_row.get("parameters_json") or {}
			plan = FeaturePlanCreateRequest(**(parameters.get("plan") or {}))
			resolved_plan_id = int(stored_plan_row["id"])

		train_df, summary = _apply_plan_in_memory(df, plan)

		train_models = _load_train_models_function()
		results = train_models(
			train_df,
			target_col=plan.target_col,
			test_size=request.test_size,
			random_state=request.random_state,
			primary_metric=request.primary_metric,
			optimize_hyperparams=request.optimize_hyperparams,
		)

		return {
			"dataset_id": request.dataset_id,
			"version_id": int(version["id"]),
			"plan_id": resolved_plan_id,
			"feature_summary": summary.dict(),
			"train_results": results,
		}
	except ValueError as exc:
		logger.warning("event=feature_automl_train_invalid detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
	except FileNotFoundError as exc:
		logger.warning("event=feature_automl_train_file_not_found detail=%s", str(exc))
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	except Exception as exc:
		logger.exception("event=feature_automl_train_error dataset_id=%s", request.dataset_id)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

