import io
import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from psycopg2.extras import Json

from DataBaseManagement.dbConectionPostgres import get_db_tasks
from DataBaseManagement.dbManagement import (
    get_record_by_id_Generic,
    get_rows_by_condition_Generic,
    insert_record_Generic,
)

router = APIRouter()
logger = logging.getLogger("api.endpointsDatasets")

DATASET_TABLE = "datasets"
DATASET_VERSION_TABLE = "dataset_versions"
DATASET_OPERATION_TABLE = "dataset_operations"
DATASET_STORAGE_ROOT = Path(__file__).resolve().parents[1] / "data" / "datasets"


class DatasetServicesManager:
    def __init__(self, db: Any = None):
        self.db = db

    def _ensure_storage_dirs(self) -> None:
        (DATASET_STORAGE_ROOT / "raw").mkdir(parents=True, exist_ok=True)
        (DATASET_STORAGE_ROOT / "versions").mkdir(parents=True, exist_ok=True)

    def _dataset_version_dir(self, dataset_id: int) -> Path:
        return DATASET_STORAGE_ROOT / "versions" / f"dataset_{dataset_id}"

    def _build_version_path(self, dataset_id: int, version_number: int) -> Path:
        version_dir = self._dataset_version_dir(dataset_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        return version_dir / f"v{version_number:04d}.csv"

    def _preview_dataframe(self, df_reservas: pd.DataFrame) -> dict[str, Any]:
        head_data = json.loads(df_reservas.head().replace([float("inf"), float("-inf")], None).to_json(orient="records"))
        tail_data = json.loads(df_reservas.tail().replace([float("inf"), float("-inf")], None).to_json(orient="records"))

        info_buffer = io.StringIO()
        df_reservas.info(buf=info_buffer)

        return {
            "head": head_data,
            "tail": tail_data,
            "columns": df_reservas.columns.tolist(),
            "info": info_buffer.getvalue(),
        }

    def _get_dataset(self, dataset_id: int) -> dict[str, Any]:
        dataset = get_record_by_id_Generic(DATASET_TABLE, dataset_id, connection=self.db)
        if not dataset:
            raise ValueError(f"Dataset con ID {dataset_id} no encontrado")
        return dataset

    def _get_version(self, dataset_id: int, version_id: int) -> dict[str, Any]:
        version = get_record_by_id_Generic(DATASET_VERSION_TABLE, version_id, connection=self.db)
        if not version or version.get("dataset_id") != dataset_id:
            raise ValueError(f"Version {version_id} del dataset {dataset_id} no encontrada")
        return version

    def _get_latest_version(self, dataset_id: int) -> dict[str, Any]:
        rows = get_rows_by_condition_Generic(
            DATASET_VERSION_TABLE,
            "dataset_id = %s ORDER BY version_number DESC LIMIT 1",
            [dataset_id],
            connection=self.db,
        )
        if not rows:
            raise ValueError(f"Dataset con ID {dataset_id} no tiene versiones cargadas")
        return rows[0]

    def _get_versions(self, dataset_id: int) -> list[dict[str, Any]]:
        return get_rows_by_condition_Generic(
            DATASET_VERSION_TABLE,
            "dataset_id = %s ORDER BY version_number DESC",
            [dataset_id],
            connection=self.db,
        )

    def create_dataset_from_csv(self, filename: str, content: bytes) -> dict[str, Any]:
        self._ensure_storage_dirs()

        df_reservas = pd.read_csv(io.BytesIO(content))
        storage_key = uuid4().hex

        dataset_row = insert_record_Generic(
            DATASET_TABLE,
            {
                "original_filename": filename,
                "storage_key": storage_key,
                "storage_root": str(DATASET_STORAGE_ROOT),
            },
            connection=self.db,
        )

        dataset_id = int(dataset_row["id"])
        raw_path = DATASET_STORAGE_ROOT / "raw" / f"dataset_{dataset_id}_{storage_key}.csv"
        raw_path.write_bytes(content)

        version_path = self._build_version_path(dataset_id, 1)
        df_reservas.to_csv(version_path, index=False)

        version_row = insert_record_Generic(
            DATASET_VERSION_TABLE,
            {
                "dataset_id": dataset_id,
                "version_number": 1,
                "parent_version_id": None,
                "storage_path": str(version_path),
                "row_count": int(df_reservas.shape[0]),
                "column_count": int(df_reservas.shape[1]),
                "columns_json": Json(df_reservas.columns.tolist()),
            },
            connection=self.db,
        )

        insert_record_Generic(
            DATASET_OPERATION_TABLE,
            {
                "dataset_id": dataset_id,
                "dataset_version_id": version_row["id"],
                "operation_name": "upload_csv",
                "parameters_json": Json({"filename": filename}),
            },
            connection=self.db,
        )

        logger.info(
            "event=dataset_upload_success dataset_id=%s version_id=%s filename=%s rows=%s cols=%s",
            dataset_id,
            version_row["id"],
            filename,
            len(df_reservas),
            len(df_reservas.columns),
        )

        return {
            "dataset": dataset_row,
            "version": version_row,
            **self._preview_dataframe(df_reservas),
        }

    def get_dataset_details(self, dataset_id: int) -> dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        versions = self._get_versions(dataset_id)
        return {
            "dataset": dataset,
            "versions": versions,
            "latest_version": versions[0] if versions else None,
        }

    def preview_version(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        version = self._get_latest_version(dataset_id) if version_id is None else self._get_version(dataset_id, version_id)
        df_reservas = pd.read_csv(Path(version["storage_path"]))
        return {
            "dataset_id": dataset_id,
            "version": version,
            **self._preview_dataframe(df_reservas),
        }

    def null_summary(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        version = self._get_latest_version(dataset_id) if version_id is None else self._get_version(dataset_id, version_id)
        df_reservas = pd.read_csv(Path(version["storage_path"]))
        summary = df_reservas.isna().sum().to_dict()
        return {
            "dataset_id": dataset_id,
            "version": version,
            "nulls": summary,
            "row_count": int(df_reservas.shape[0]),
        }

    def lowercase_columns(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        base_version = self._get_latest_version(dataset_id) if version_id is None else self._get_version(dataset_id, version_id)
        df_reservas = pd.read_csv(Path(base_version["storage_path"]))
        df_reservas.columns = df_reservas.columns.astype(str).str.lower()

        next_version_number = int(base_version["version_number"]) + 1
        new_version_path = self._build_version_path(dataset_id, next_version_number)
        df_reservas.to_csv(new_version_path, index=False)

        version_row = insert_record_Generic(
            DATASET_VERSION_TABLE,
            {
                "dataset_id": dataset_id,
                "version_number": next_version_number,
                "parent_version_id": base_version["id"],
                "storage_path": str(new_version_path),
                "row_count": int(df_reservas.shape[0]),
                "column_count": int(df_reservas.shape[1]),
                "columns_json": Json(df_reservas.columns.tolist()),
            },
            connection=self.db,
        )

        insert_record_Generic(
            DATASET_OPERATION_TABLE,
            {
                "dataset_id": dataset_id,
                "dataset_version_id": version_row["id"],
                "operation_name": "lowercase_columns",
                "parameters_json": Json({"source_version_id": base_version["id"]}),
            },
            connection=self.db,
        )

        logger.info(
            "event=dataset_lowercase_columns_success dataset_id=%s source_version_id=%s version_id=%s",
            dataset_id,
            base_version["id"],
            version_row["id"],
        )

        return {
            "dataset_id": dataset_id,
            "source_version": base_version,
            "version": version_row,
            **self._preview_dataframe(df_reservas),
        }


@router.post("/datasets/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...), db=Depends(get_db_tasks)):
    logger.info("event=dataset_upload_start filename=%s", file.filename)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener extensión .csv",
        )

    try:
        content = await file.read()
        manager = DatasetServicesManager(db)
        return manager.create_dataset_from_csv(file.filename, content)
    except Exception as exc:
        logger.exception("event=dataset_upload_error filename=%s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo procesar el CSV: {str(exc)}",
        )


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_get_start dataset_id=%s", dataset_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.get_dataset_details(dataset_id)
    except ValueError as exc:
        logger.warning("event=dataset_get_not_found dataset_id=%s detail=%s", dataset_id, str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/datasets/{dataset_id}/preview")
def preview_latest_dataset_version(dataset_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_preview_latest_start dataset_id=%s", dataset_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.preview_version(dataset_id)
    except ValueError as exc:
        logger.warning("event=dataset_preview_latest_not_found dataset_id=%s detail=%s", dataset_id, str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/datasets/{dataset_id}/versions/{version_id}/preview")
def preview_dataset_version(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_preview_version_start dataset_id=%s version_id=%s", dataset_id, version_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.preview_version(dataset_id, version_id)
    except ValueError as exc:
        logger.warning(
            "event=dataset_preview_version_not_found dataset_id=%s version_id=%s detail=%s",
            dataset_id,
            version_id,
            str(exc),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/datasets/{dataset_id}/null-summary")
def null_summary_latest_dataset_version(dataset_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_null_summary_latest_start dataset_id=%s", dataset_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.null_summary(dataset_id)
    except ValueError as exc:
        logger.warning("event=dataset_null_summary_latest_not_found dataset_id=%s detail=%s", dataset_id, str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/datasets/{dataset_id}/versions/{version_id}/null-summary")
def null_summary_dataset_version(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_null_summary_version_start dataset_id=%s version_id=%s", dataset_id, version_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.null_summary(dataset_id, version_id)
    except ValueError as exc:
        logger.warning(
            "event=dataset_null_summary_version_not_found dataset_id=%s version_id=%s detail=%s",
            dataset_id,
            version_id,
            str(exc),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/datasets/{dataset_id}/versions/{version_id}/lowercase-columns", status_code=status.HTTP_201_CREATED)
def lowercase_dataset_columns(dataset_id: int, version_id: int, db=Depends(get_db_tasks)):
    logger.info("event=dataset_lowercase_columns_start dataset_id=%s version_id=%s", dataset_id, version_id)
    manager = DatasetServicesManager(db)
    try:
        return manager.lowercase_columns(dataset_id, version_id)
    except ValueError as exc:
        logger.warning(
            "event=dataset_lowercase_columns_not_found dataset_id=%s version_id=%s detail=%s",
            dataset_id,
            version_id,
            str(exc),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))