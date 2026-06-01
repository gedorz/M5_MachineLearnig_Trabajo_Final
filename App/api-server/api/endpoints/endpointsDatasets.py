import io
import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import joblib
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from psycopg2.extras import Json

from dataBaseManagement.dbConectionPostgres import get_db_tasks
from dataBaseManagement.dbManagement import (
    get_record_by_id_Generic,
    get_rows_by_condition_Generic,
    insert_record_Generic,
)

router = APIRouter()
logger = logging.getLogger("api.endpointsDatasets")

DATASET_TABLE = "datasets"
DATASET_VERSION_TABLE = "dataset_versions"
DATASET_OPERATION_TABLE = "dataset_operations"
MAX_TRANSPOSE_PREVIEW_ROWS = 200 # Limita el número de filas para el preview de la tabla transpuesta, evitando respuestas gigantes en datasets grandes.

# Ruta raíz para almacenar los archivos CSV originales y las versiones procesadas de los datasets. 
# Cada dataset tendrá su propia carpeta identificada por su dataset_id dentro de esta ruta raíz,
#  y cada versión del dataset se almacenará como un archivo CSV separado dentro de esa carpeta.
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

    def _serialize_table(
        self,
        dataframe: pd.DataFrame,
        include_index: bool = False,
        index_column_name: str = "index",
    ) -> dict[str, Any]:
        cleaned_df = dataframe.replace([float("inf"), float("-inf")], None)
        if include_index:
            cleaned_df = cleaned_df.reset_index().rename(columns={"index": index_column_name})

        return {
            "columns": [str(column) for column in cleaned_df.columns.tolist()],
            "rows": json.loads(cleaned_df.to_json(orient="records")),
        }

    def _get_dataframe(self, version: dict[str, Any]) -> pd.DataFrame:
        return pd.read_csv(Path(version["storage_path"]))

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

    def get_versions(self, dataset_id: int) -> list[dict[str, Any]]:
        self._get_dataset(dataset_id)
        return self._get_versions(dataset_id)

    def get_dataframe_by_version(
        self,
        dataset_id: int,
        version_id: int | None = None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        version = self._get_latest_version(dataset_id) if version_id is None else self._get_version(dataset_id, version_id)
        return self._get_dataframe(version), version

    def get_version_data_info(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        df_reservas, version = self.get_dataframe_by_version(dataset_id, version_id)

        info_buffer = io.StringIO()
        df_reservas.info(buf=info_buffer)

        # Compatibilidad entre versiones de pandas: datetime_is_numeric no existe en todas.
        try:
            describe_df = df_reservas.describe(include="all", datetime_is_numeric=True)
        except TypeError:
            describe_df = df_reservas.describe(include="all")

        describe_df = describe_df.replace([float("inf"), float("-inf")], None)
        describe_transpose_df = describe_df.transpose()

        # Evita respuestas gigantes: transpose completo en datasets grandes puede colgar Swagger/UI.
        transpose_source = df_reservas.iloc[:MAX_TRANSPOSE_PREVIEW_ROWS]
        transpose_df = transpose_source.transpose()

        return {
            "dataset_id": dataset_id,
            "version": version,
            "shape": [int(df_reservas.shape[0]), int(df_reservas.shape[1])],
            "columns": [str(column) for column in df_reservas.columns.tolist()],
            "info": info_buffer.getvalue(),
            "head": self._serialize_table(df_reservas.head(), include_index=True, index_column_name="Index"),
            "tail": self._serialize_table(df_reservas.tail(), include_index=True, index_column_name="Index"),
            "transpose": self._serialize_table(transpose_df, include_index=True, index_column_name="Column"),
            "transpose_preview_rows": int(transpose_source.shape[0]),
            "transpose_total_rows": int(df_reservas.shape[0]),
            "describe": self._serialize_table(describe_df, include_index=True, index_column_name="stadistic"),
            "describe_transpose": self._serialize_table(describe_transpose_df, include_index=True, index_column_name="Column"),
        }

    def create_dataset_from_csv(self, filename: str, content: bytes) -> dict[str, Any]:
        self._ensure_storage_dirs()

        # Carga el CSV en un DataFrame de pandas
        df_reservas = pd.read_csv(io.BytesIO(content))
        storage_key = uuid4().hex

        # Lo Registra en base de datos y lo guarda en el sistema de archivos, creando la versión inicial del dataset (v1)
        # Inserta el registro del dataset y la versión en la base de datos, 
        # y guarda el archivo en el sistema de archivos
        dataset_row = insert_record_Generic(
            DATASET_TABLE,
            {
                "original_filename": filename,
                "storage_key": storage_key,
                "storage_root": str(DATASET_STORAGE_ROOT),
            },
            connection=self.db,
        )

        # Guarda el archivo CSV original en la carpeta de almacenamiento raw 
        # con un nombre único basado en el dataset_id y storage_key para evitar colisiones.
        dataset_id = int(dataset_row["id"])
        raw_path = DATASET_STORAGE_ROOT / "raw" / f"dataset_{dataset_id}_{storage_key}.csv"
        raw_path.write_bytes(content)

        version_path = self._build_version_path(dataset_id, 1)
        df_reservas.to_csv(version_path, index=False)

        # Registra la versión del dataset en la base de datos, incluyendo metadata 
        # como el número de filas, columnas y los nombres de las columnas.
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

        # Registra la operación de carga del CSV en la base de datos, asociándola con la versión del dataset.
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
        df_reservas, version = self.get_dataframe_by_version(dataset_id, version_id)
        return {
            "dataset_id": dataset_id,
            "version": version,
            **self._preview_dataframe(df_reservas),
        }

    def null_summary(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        df_reservas, version = self.get_dataframe_by_version(dataset_id, version_id)
        summary = df_reservas.isna().sum().to_dict()
        return {
            "dataset_id": dataset_id,
            "version": version,
            "nulls": summary,
            "row_count": int(df_reservas.shape[0]),
        }

    def lowercase_columns(self, dataset_id: int, version_id: int | None = None) -> dict[str, Any]:
        df_reservas, base_version = self.get_dataframe_by_version(dataset_id, version_id)
        df_reservas.columns = df_reservas.columns.astype(str).str.lower()

        next_version_number = int(base_version["version_number"]) + 1
        new_version_path = self._build_version_path(dataset_id, next_version_number)
        df_reservas.to_csv(new_version_path, index=False)

        # Guarda la nueva versión del dataset con las columnas en minúscula, 
        # registrando la operación en la base de datos y asociándola con la versión original 
        # como su "parent_version_id" para mantener el historial de transformaciones.
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

        # Registra la operación de transformación (lowercase_columns) en la base de datos, 
        # asociándola con la nueva versión del dataset y con la versión original como su padre.
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


class TrainRequest(BaseModel):
    dataset_id: int
    version_id: int | None = None
    test_size: float = Field(default=0.2, ge=0.05, le=0.5)
    random_state: int = 42
    primary_metric: str = Field(default="roc_auc")


@router.post("/train")
def train_dataset(request: TrainRequest, db=Depends(get_db_tasks)):
    logger.info(
        "event=train_start dataset_id=%s version_id=%s test_size=%s random_state=%s primary_metric=%s",
        request.dataset_id,
        request.version_id,
        request.test_size,
        request.random_state,
        request.primary_metric,
    )

    try:
        manager = DatasetServicesManager(db)
        version = (
            manager._get_latest_version(request.dataset_id)
            if request.version_id is None
            else manager._get_version(request.dataset_id, request.version_id)
        )

        dataset_path = Path(version["storage_path"])
        if not dataset_path.exists():
            raise FileNotFoundError(f"El archivo del dataset no existe: {dataset_path}")

        df_reservas = pd.read_csv(dataset_path)

        ## En contenedor: /src está montado con los módulos Python
        ## sys.path.insert lo hace disponible para importación
        if "/src" not in sys.path:
            sys.path.insert(0, "/src")

        ###from model_trainer import train_models

        sys.path.insert(0, '/')  # Agrega la raíz al path

        from src.model_trainer import train_models

        results = train_models(
            df_reservas,
            test_size=request.test_size,
            random_state=request.random_state,
            primary_metric=request.primary_metric,
        )

        return {
            "dataset_id": request.dataset_id,
            "version_id": version["id"],
            "storage_path": str(dataset_path),
            "train_results": results,
        }
    except ValueError as exc:
        logger.warning(
            "event=train_dataset_not_found dataset_id=%s version_id=%s detail=%s",
            request.dataset_id,
            request.version_id,
            str(exc),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("event=train_dataset_file_not_found detail=%s", str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("event=train_error dataset_id=%s version_id=%s", request.dataset_id, request.version_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


class PredictRequest(BaseModel):
    """Request para predicción.

    Puede enviar `dataset_id`/`version_id` para predecir sobre un dataset cargado,
    o `records` con una lista de objetos (filas) con las columnas de features.
    """
    dataset_id: int | None = None
    version_id: int | None = None
    records: list[dict] | None = None
    model_name: str | None = None
    limit: int | None = None


@router.post("/predict")
def predict_endpoint(request: PredictRequest, db=Depends(get_db_tasks)):
    logger.info("event=predict_start dataset_id=%s version_id=%s model=%s limit=%s",
                request.dataset_id, request.version_id, request.model_name, request.limit)

    try:
        # Obtener datos desde DB o usar registros enviados
        if request.dataset_id is not None:
            manager = DatasetServicesManager(db)
            version = (
                manager._get_latest_version(request.dataset_id)
                if request.version_id is None
                else manager._get_version(request.dataset_id, request.version_id)
            )

            dataset_path = Path(version["storage_path"])
            if not dataset_path.exists():
                raise FileNotFoundError(f"El archivo del dataset no existe: {dataset_path}")

            df = pd.read_csv(dataset_path)
            # Si viene la columna objetivo, la removemos antes de predecir
            if "is_canceled" in df.columns:
                X = df.drop(columns=["is_canceled"])
            else:
                X = df

            if request.limit:
                X = X.head(request.limit)

        elif request.records:
            X = pd.DataFrame(request.records)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Debe proporcionar 'dataset_id' o 'records' en el body")

        # Asegurar availability de /src
        if "/src" not in sys.path:
            sys.path.insert(0, "/src")
        if "/" not in sys.path:
            sys.path.insert(0, "/")

        from src.predictor import load_model_by_name, predict_from_dataframe

        model, model_type, model_identifier = load_model_by_name(request.model_name)

        predictions = predict_from_dataframe(X, model, model_type)

        return {"model": model_identifier, "predictions": predictions, "n": len(predictions)}

    except FileNotFoundError as exc:
        logger.warning("event=predict_file_not_found detail=%s", str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("event=predict_error dataset_id=%s version_id=%s", request.dataset_id, request.version_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

class EvaluateRequest(BaseModel):
    """Request para evaluación de modelos."""
    dataset_id: int = Field(..., description="ID del dataset a evaluar")
    version_id: int = Field(None, description="Versión específica (opcional, usa última si no se especifica)")
    model_name: str = Field(None, description="Nombre del modelo específico a evaluar (ej: XGBoost, RandomForest). Si es None, evalúa todos")
    test_size: float = Field(0.2, description="Proporción para test", ge=0.1, le=0.5)
    random_state: int = Field(42, description="Semilla aleatoria")
    primary_metric: str = Field("roc_auc", description="Métrica principal para ordenar resultados")


class EvaluateResponse(BaseModel):
    """Respuesta de evaluación."""
    dataset_id: int
    version_id: int
    storage_path: str
    evaluation_results: dict[str, Any]
    best_model: str
    best_score: float
    plots_path: str

@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_models(
    request: EvaluateRequest,
    db=Depends(get_db_tasks)
):
    """
    Evalúa modelos entrenados contra un dataset.
    
    - Si se especifica model_name, evalúa solo ese modelo
    - Si no, evalúa todos los modelos disponibles
    - Genera métricas completas y gráficos comparativos
    """
    logger.info(
        "event=evaluate_start dataset_id=%s version_id=%s model_name=%s test_size=%s",
        request.dataset_id,
        request.version_id,
        request.model_name,
        request.test_size,
    )

    try:
        # 1. Obtener el dataset
        manager = DatasetServicesManager(db)
        version = (
            manager._get_latest_version(request.dataset_id)
            if request.version_id is None
            else manager._get_version(request.dataset_id, request.version_id)
        )

        dataset_path = Path(version["storage_path"])
        if not dataset_path.exists():
            raise FileNotFoundError(f"El archivo del dataset no existe: {dataset_path}")

        # 2. Cargar datos
        df = pd.read_csv(dataset_path)
        
        # 3. Configurar path de módulos
        if "/src" not in sys.path:
            sys.path.insert(0, "/src")
        if "/" not in sys.path:
            sys.path.insert(0, "/")
        
        # 4. Importar módulos necesarios
        from src.model_trainer import _get_feature_columns, _build_preprocessor
        from src.evaluator import ModelEvaluator
        from src.config import MODELS_DIR
        
        # 5. Verificar que existan modelos entrenados
        if not MODELS_DIR.exists():
            raise FileNotFoundError(f"No hay modelos entrenados en {MODELS_DIR}")
        
        # 6. Preparar datos para evaluación (mismo preprocesamiento que en entrenamiento)
        target_col = "is_canceled"
        
        # Verificar que el target existe
        if target_col not in df.columns:
            raise ValueError(f"La columna objetivo '{target_col}' no existe en el dataset")
        
        X = df.drop(columns=[target_col])
        y = df[target_col]

        # Columnas a excluir (target o metadata)
        EXCLUDED_COLUMNS = ['reservation_status', 'reservation_status_date']

        # Seleccionar solo las características
        feature_columns = [col for col in X.columns if col not in EXCLUDED_COLUMNS]
        X_features = X[feature_columns]

        logger.info(f"Columnas de características ({len(feature_columns)}): {feature_columns}")
        # Debería mostrar 29 o 28 columnas

        logger.info(f"Forma de X: {X.shape}")
        logger.info(f"Columnas: {X.columns.tolist()}")
        logger.info(f"Número de características esperadas: 29")
        
        # Identificar columnas y construir preprocesador
        numeric_cols, categorical_cols = _get_feature_columns(df, target_col)
        preprocessor = _build_preprocessor(numeric_cols, categorical_cols)
        
        # Dividir datos (misma semilla que en entrenamiento para consistencia)
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=request.test_size, 
            random_state=request.random_state,
            stratify=y
        )
        
        # Preprocesar datos de test
        preprocessor.fit(X_train)  # Fit en train
        X_test_proc = preprocessor.transform(X_test)
        
        # 7. Cargar modelos a evaluar
        models_dict = {}
        
        if request.model_name:
            # Evaluar solo un modelo específico
            model_path = MODELS_DIR / f"{request.model_name}.pkl"
            if not model_path.exists():
                model_path = MODELS_DIR / f"{request.model_name}.keras"
            if not model_path.exists():
                raise FileNotFoundError(f"Modelo {request.model_name} no encontrado")
            
            model = joblib.load(model_path) if model_path.suffix == '.pkl' else _load_keras_model(model_path)
            models_dict[request.model_name] = model
        else:
            # Evaluar todos los modelos
            for pkl_path in MODELS_DIR.glob("*.pkl"):
                if "best_model" not in pkl_path.stem:
                    models_dict[pkl_path.stem] = joblib.load(pkl_path)
            
            # También buscar modelos Keras
            for keras_path in MODELS_DIR.glob("*.keras"):
                if "best_model" not in keras_path.stem:
                    models_dict[keras_path.stem] = _load_keras_model(keras_path)
        
        if not models_dict:
            raise FileNotFoundError(f"No se encontraron modelos para evaluar en {MODELS_DIR}")
        
        logger.info(f"Evaluando {len(models_dict)} modelos: {list(models_dict.keys())}")
        
        # 8. Ejecutar evaluación
        evaluator = ModelEvaluator(output_dir=MODELS_DIR / "evaluation_reports")
        
        # Generar reporte completo
        report = evaluator.generate_report(
            models_dict, 
            X_test_proc, 
            y_test,
            feature_names=numeric_cols + categorical_cols,
            save=True
        )
        
        # 9. Determinar mejor modelo
        df_comparison = pd.DataFrame(report["comparison"])
        if "roc_auc" in df_comparison.columns:
            best_idx = df_comparison["roc_auc"].idxmax()
            best_model = df_comparison.loc[best_idx, "model"]
            best_score = float(df_comparison.loc[best_idx, "roc_auc"])
        else:
            best_model = None
            best_score = None
        
        # 10. Guardar reporte en JSON
        report_path = MODELS_DIR / "evaluation_reports" / f"dataset_{request.dataset_id}_v{version['id']}_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # Convertir a serializable
            serializable_report = {
                "dataset_id": request.dataset_id,
                "version_id": version["id"],
                "test_size": request.test_size,
                "random_state": request.random_state,
                "models": {
                    name: {
                        k: v for k, v in metrics.items() 
                        if not k.startswith('_')
                    }
                    for name, metrics in report["models"].items()
                },
                "comparison": report["comparison"],
                "best_model": best_model,
                "best_score": best_score
            }
            json.dump(serializable_report, f, indent=2, default=str)
        
        logger.info(
            "event=evaluate_success dataset_id=%s version_id=%s models_evaluated=%d best_model=%s best_score=%.4f",
            request.dataset_id,
            version["id"],
            len(models_dict),
            best_model,
            best_score or 0
        )
        
        return EvaluateResponse(
            dataset_id=request.dataset_id,
            version_id=version["id"],
            storage_path=str(dataset_path),
            evaluation_results={
                "models": {
                    name: {
                        k: v for k, v in metrics.items() 
                        if not k.startswith('_')
                    }
                    for name, metrics in report["models"].items()
                },
                "comparison_table": report["comparison"],
                "plots": report["plots"]
            },
            best_model=best_model,
            best_score=best_score,
            plots_path=str(MODELS_DIR / "evaluation_reports")
        )
        
    except FileNotFoundError as exc:
        logger.warning("event=evaluate_file_not_found detail=%s", str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        logger.warning("event=evaluate_value_error detail=%s", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("event=evaluate_error dataset_id=%s version_id=%s", request.dataset_id, request.version_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _load_keras_model(path: Path):
    """Helper para cargar modelos Keras."""
    try:
        from tensorflow.keras.models import load_model
        return load_model(path)
    except ImportError:
        raise ImportError("TensorFlow necesario para cargar modelos .keras")

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