from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import importlib
import warnings

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb

from dataBaseManagement.dbConectionPostgres import get_db_tasks
from .endpointContratos import FeaturePlanAutoMLRequest, FeaturePlanCreateRequest, FeaturePlanSummary
from .endPointFeatures import _apply_plan_in_memory, _normalize_plan, _resolve_latest_plan, _resolve_version
from .endpointsDatasets import DatasetServicesManager

router = APIRouter()
logger = logging.getLogger("api.endPointEntrenarAutoML")
warnings.filterwarnings("ignore")

MODELS_DIR = Path(__file__).resolve().parents[1] / "data" / "models"

# Intentar cargar TensorFlow/Keras opcionalmente sin romper análisis estático.
try:
	importlib.import_module("tensorflow")
	TENSORFLOW_AVAILABLE = True
except ImportError:
	TENSORFLOW_AVAILABLE = False


def _validate_dataset_columns(
	df: pd.DataFrame,
	target_col: str,
	required_columns: Optional[list[str]] = None,
) -> None:
	required = required_columns or [target_col]
	missing = [col for col in required if col not in df.columns]
	if missing:
		raise ValueError(
			f"Faltan columnas obligatorias en el dataset: {missing}. "
			"Revisa el Feature Plan aplicado y las columnas del dataset de entrenamiento."
		)

	if target_col not in df.columns:
		raise ValueError(f"La columna objetivo '{target_col}' no existe en el dataset.")


def preprocess_dataset(df: pd.DataFrame, leakage_columns: Optional[list[str]] = None) -> pd.DataFrame:
	df = df.copy()
	leakage_columns_list = leakage_columns or []

	for col in leakage_columns_list:
		if col in df.columns:
			df = df.drop(columns=[col])

	df.columns = df.columns.astype(str).str.lower().str.strip()
	for col in df.select_dtypes(include=["object"]).columns:
		df[col] = df[col].astype(str).str.strip()

	for col in df.select_dtypes(include=["number"]).columns:
		df[col] = df[col].fillna(df[col].median())

	for col in df.select_dtypes(include=["object"]).columns:
		df[col] = df[col].replace({"nan": None, "None": None})
		df[col] = df[col].fillna("missing")

	return df


def _get_feature_columns(df: pd.DataFrame, target_col: str) -> Tuple[list, list]:
	"""Identifica columnas numéricas y categóricas."""
	numeric = df.select_dtypes(include=[np.number]).columns.tolist()
	if target_col in numeric:
		numeric.remove(target_col)
	categorical = [c for c in df.columns if c not in numeric and c != target_col]
	return numeric, categorical


def _build_preprocessor(numeric_cols: list, categorical_cols: list) -> ColumnTransformer:
	"""Construye el preprocesador para columnas numéricas y categóricas."""
	num_pipe = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
	cat_pipe = Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
			("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
		]
	)
	return ColumnTransformer(
		transformers=[("num", num_pipe, numeric_cols), ("cat", cat_pipe, categorical_cols)],
		remainder="drop",
	)


def _create_keras_model(input_dim: int) -> Any:
	"""Crea la red neuronal con arquitectura base."""
	if not TENSORFLOW_AVAILABLE:
		raise ImportError("TensorFlow no instalado")

	keras_layers = importlib.import_module("tensorflow.keras.layers")
	keras_models = importlib.import_module("tensorflow.keras.models")
	Dense = keras_layers.Dense
	Dropout = keras_layers.Dropout
	BatchNormalization = keras_layers.BatchNormalization
	Sequential = keras_models.Sequential

	model = Sequential(
		[
			Dense(128, activation="relu", input_dim=input_dim),
			BatchNormalization(),
			Dropout(0.3),
			Dense(64, activation="relu"),
			BatchNormalization(),
			Dropout(0.3),
			Dense(32, activation="relu"),
			Dense(1, activation="sigmoid"),
		]
	)
	model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy", "auc"])
	return model


def _train_keras_model(
	X_train: np.ndarray,
	y_train: np.ndarray,
	X_val: np.ndarray,
	y_val: np.ndarray,
	class_weight: Optional[Dict] = None,
) -> Any:
	"""Entrena la red neuronal con early stopping."""
	keras_callbacks = importlib.import_module("tensorflow.keras.callbacks")
	EarlyStopping = keras_callbacks.EarlyStopping

	model = _create_keras_model(X_train.shape[1])
	early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

	model.fit(
		X_train,
		y_train,
		validation_data=(X_val, y_val),
		epochs=50,
		batch_size=256,
		callbacks=[early_stop],
		class_weight=class_weight,
		verbose=0,
	)
	return model


def _score_model(estimator: Any, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
	"""Calcula métricas de evaluación del modelo."""
	y_pred = estimator.predict(X_val)

	try:
		y_proba = estimator.predict_proba(X_val)[:, 1]
	except Exception:
		try:
			y_proba = estimator.decision_function(X_val)
		except Exception:
			y_proba = np.zeros(len(y_val))

	return {
		"accuracy": float(accuracy_score(y_val, y_pred)),
		"precision": float(precision_score(y_val, y_pred, zero_division=0)),
		"recall": float(recall_score(y_val, y_pred, zero_division=0)),
		"f1": float(f1_score(y_val, y_pred, zero_division=0)),
		"roc_auc": float(roc_auc_score(y_val, y_proba)) if len(np.unique(y_val)) > 1 else 0.0,
	}


def train_models(
	df: pd.DataFrame,
	target_col: str = "is_canceled",
	test_size: float = 0.2,
	random_state: int = 42,
	primary_metric: str = "roc_auc",
	optimize_hyperparams: bool = True,
	required_columns: Optional[list[str]] = None,
	leakage_columns: Optional[list[str]] = None,
) -> Dict[str, Any]:
	"""Entrena modelos de clasificación y retorna métricas/artefactos."""
	df_proc = preprocess_dataset(df, leakage_columns=leakage_columns)
	
	_validate_dataset_columns(df_proc, 
						   target_col=target_col, 
						   required_columns=required_columns)

	X = df_proc.drop(columns=[target_col])
	y = df_proc[target_col]

	numeric_cols, categorical_cols = _get_feature_columns(df_proc, target_col)
	preprocessor = _build_preprocessor(numeric_cols, categorical_cols)

	X_train, X_val, y_train, y_val = train_test_split(
		X,
		y,
		test_size=test_size,
		random_state=random_state,
		stratify=y if len(np.unique(y)) > 1 else None,
	)

	X_train_proc = preprocessor.fit_transform(X_train)
	X_val_proc = preprocessor.transform(X_val)

	n_neg = sum(y_train == 0)
	n_pos = sum(y_train == 1)
	ratio = n_neg / n_pos if n_pos > 0 else 1.0

	models: dict[str, Any] = {}
	models["LogisticRegression"] = Pipeline(
		[("pre", preprocessor), ("model", LogisticRegression(max_iter=1000, random_state=random_state, class_weight="balanced"))]
	)
	models["DecisionTree"] = Pipeline(
		[("pre", preprocessor), ("model", DecisionTreeClassifier(random_state=random_state, class_weight="balanced", max_depth=10))]
	)
	models["RandomForest"] = Pipeline(
		[
			("pre", preprocessor),
			("model", RandomForestClassifier(n_estimators=200, random_state=random_state, class_weight="balanced", n_jobs=-1)),
		]
	)
	models["XGBoost"] = Pipeline(
		[
			("pre", preprocessor),
			(
				"model",
				xgb.XGBClassifier(
					scale_pos_weight=ratio,
					random_state=random_state,
					eval_metric="logloss",
					n_estimators=200,
					max_depth=6,
					learning_rate=0.1,
					verbosity=0,
				),
			),
		]
	)

	if TENSORFLOW_AVAILABLE:
		from sklearn.utils.class_weight import compute_class_weight

		class_weights = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
		weight_dict = {0: class_weights[0], 1: class_weights[1]}

		keras_model = _train_keras_model(
			X_train_proc,
			y_train.values,
			X_val_proc,
			y_val.values,
			class_weight=weight_dict,
		)

		keras_path = MODELS_DIR / "NeuralNetwork.keras"
		keras_model.save(keras_path)

		y_proba = keras_model.predict(X_val_proc).flatten()
		y_pred = (y_proba > 0.5).astype(int)
		metrics = {
			"accuracy": accuracy_score(y_val, y_pred),
			"precision": precision_score(y_val, y_pred, zero_division=0),
			"recall": recall_score(y_val, y_pred, zero_division=0),
			"f1": f1_score(y_val, y_pred, zero_division=0),
			"roc_auc": roc_auc_score(y_val, y_proba),
		}

		models_keras = {
			"NeuralNetwork": {
				"metrics": {k: float(v) for k, v in metrics.items()},
				"path": str(keras_path),
			}
		}
	else:
		models_keras = {}

	results: Dict[str, Any] = {"models": {}, "best_model": None}
	best_score = -float("inf")
	best_name = None

	for name, pipeline in models.items():
		pipeline.fit(X_train, y_train)
		metrics = _score_model(pipeline, X_val, y_val)

		model_path = MODELS_DIR / f"{name}.pkl"
		joblib.dump(pipeline, model_path)

		results["models"][name] = {"metrics": metrics, "path": str(model_path)}

		score = metrics.get(primary_metric, 0.0)
		if score > best_score:
			best_score = score
			best_name = name

	results["models"].update(models_keras)

	if TENSORFLOW_AVAILABLE and models_keras:
		keras_auc = models_keras["NeuralNetwork"]["metrics"]["roc_auc"]
		if keras_auc > best_score:
			best_score = keras_auc
			best_name = "NeuralNetwork"
			results["best_model"] = {
				"name": "NeuralNetwork",
				"path": str(MODELS_DIR / "NeuralNetwork.keras"),
				"score": best_score,
				"note": "Modelo Keras - cargar con tensorflow.keras.models.load_model()",
			}

	if best_name and best_name in results["models"] and best_name != "NeuralNetwork":
		best_path = MODELS_DIR / "best_model.pkl"
		joblib.dump(joblib.load(MODELS_DIR / f"{best_name}.pkl"), best_path)
		results["best_model"] = {"name": best_name, "path": str(best_path), "score": best_score}

	if optimize_hyperparams and best_name and best_name != "NeuralNetwork":
		best_model_path = MODELS_DIR / f"{best_name}.pkl"
		best_pipeline = joblib.load(best_model_path)

		if best_name == "XGBoost":
			param_grid = {
				"model__n_estimators": [100, 200, 300],
				"model__max_depth": [3, 6, 9],
				"model__learning_rate": [0.01, 0.05, 0.1],
			}

			search = RandomizedSearchCV(
				best_pipeline,
				param_grid,
				n_iter=10,
				cv=3,
				scoring="roc_auc",
				random_state=random_state,
				n_jobs=-1,
			)
			search.fit(X_train, y_train)

			best_optimized_path = MODELS_DIR / f"{best_name}_optimized.pkl"
			joblib.dump(search.best_estimator_, best_optimized_path)
			results["optimized_model"] = {
				"name": best_name,
				"path": str(best_optimized_path),
				"best_params": search.best_params_,
				"score": search.best_score_,
			}

	return results


def _ensure_storage_dirs() -> None:
	MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _load_train_models_function():
	# Retorna la referencia a la función para invocarla más adelante.
	return train_models


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
		_ensure_storage_dirs()
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

		plan_required_columns = [plan.target_col, *summary.selected_features]
		train_models = _load_train_models_function()
		results = train_models(
			train_df,
			target_col=plan.target_col,
			test_size=request.test_size,
			random_state=request.random_state,
			primary_metric=request.primary_metric,
			optimize_hyperparams=request.optimize_hyperparams,
			required_columns=plan_required_columns,
			leakage_columns=summary.leakage_columns_present,
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
