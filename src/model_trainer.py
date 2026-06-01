from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score, 
                             recall_score, roc_auc_score, confusion_matrix)
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb

# Intentar importar TensorFlow/Keras opcionalmente
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print(" TensorFlow no instalado. La red neuronal no estará disponible.")

from config import MODELS_DIR
from data_loader import preprocess_dataset, _validate_dataset_columns

# Configurar directorio de modelos
try:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    alt = Path("/app/data/models")
    alt.mkdir(parents=True, exist_ok=True)
    MODELS_DIR = alt


def _get_feature_columns(df: pd.DataFrame, target_col: str) -> Tuple[list, list]:
    """Identifica columnas numéricas y categóricas."""
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    if target_col in numeric:
        numeric.remove(target_col)
    categorical = [c for c in df.columns if c not in numeric and c != target_col]
    return numeric, categorical


def _build_preprocessor(numeric_cols: list, categorical_cols: list) -> ColumnTransformer:
    """Construye el preprocesador (igual al del notebook)."""
    num_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    cat_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    return ColumnTransformer(
        transformers=[
            ("num", num_pipe, numeric_cols),
            ("cat", cat_pipe, categorical_cols)
        ],
        remainder="drop"
    )


def _create_keras_model(input_dim: int) -> Any:
    """Crea la red neuronal con la misma arquitectura del notebook."""
    if not TENSORFLOW_AVAILABLE:
        raise ImportError("TensorFlow no instalado")
    
    model = Sequential([
        Dense(128, activation='relu', input_dim=input_dim),
        BatchNormalization(),
        Dropout(0.3),
        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.3),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy', 'auc']
    )
    return model


def _train_keras_model(X_train: np.ndarray, y_train: np.ndarray, 
                       X_val: np.ndarray, y_val: np.ndarray,
                       class_weight: Optional[Dict] = None) -> Any:
    """Entrena la red neuronal con early stopping."""
    model = _create_keras_model(X_train.shape[1])
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=256,
        callbacks=[early_stop],
        class_weight=class_weight,
        verbose=0
    )
    return model


def _score_model(estimator: Any, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
    """Calcula métricas de evaluación."""
    y_pred = estimator.predict(X_val)
    
    # Obtener probabilidades
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


def train_models(df: pd.DataFrame, target_col: str = "is_canceled", 
                 test_size: float = 0.2, random_state: int = 42, 
                 primary_metric: str = "roc_auc",
                 optimize_hyperparams: bool = True) -> Dict[str, Any]:
    """
    Entrena modelos con las mismas configuraciones que el notebook.
    
    Args:
        df: DataFrame con los datos
        target_col: Nombre de la variable objetivo
        test_size: Proporción de test
        random_state: Semilla aleatoria
        primary_metric: Métrica principal para seleccionar mejor modelo
        optimize_hyperparams: Si realizar optimización básica de hiperparámetros
    """
    # Preprocesar datos
    df_proc = preprocess_dataset(df)
    _validate_dataset_columns(df_proc)
    
    X = df_proc.drop(columns=[target_col])
    y = df_proc[target_col]
    
    # Identificar columnas
    numeric_cols, categorical_cols = _get_feature_columns(df_proc, target_col)
    preprocessor = _build_preprocessor(numeric_cols, categorical_cols)
    
    # Dividir datos
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=random_state, 
        stratify=y if len(np.unique(y)) > 1 else None
    )
    
    # Preprocesar y transformar para Keras (necesita arrays numéricos)
    X_train_proc = preprocessor.fit_transform(X_train)
    X_val_proc = preprocessor.transform(X_val)
    
    # Calcular ratio para balanceo de clases
    n_neg = sum(y_train == 0)
    n_pos = sum(y_train == 1)
    ratio = n_neg / n_pos if n_pos > 0 else 1.0
    print(f" Ratio de desbalanceo: {ratio:.2f} (positivos: {n_pos}, negativos: {n_neg})")
    
    # === DEFINICIÓN DE MODELOS (como en el notebook) ===
    models = {}
    
    # 1. Logistic Regression con class_weight
    models["LogisticRegression"] = Pipeline([
        ("pre", preprocessor),
        ("model", LogisticRegression(
            max_iter=1000, 
            random_state=random_state,
            class_weight='balanced'  # Manejo de desbalanceo
        ))
    ])
    
    # 2. Decision Tree con class_weight
    models["DecisionTree"] = Pipeline([
        ("pre", preprocessor),
        ("model", DecisionTreeClassifier(
            random_state=random_state,
            class_weight='balanced',  # Manejo de desbalanceo
            max_depth=10
        ))
    ])
    
    # 3. Random Forest con class_weight
    models["RandomForest"] = Pipeline([
        ("pre", preprocessor),
        ("model", RandomForestClassifier(
            n_estimators=200,
            random_state=random_state,
            class_weight='balanced',  # Manejo de desbalanceo
            n_jobs=-1
        ))
    ])
    
    # 4. XGBoost con scale_pos_weight (REQUERIDO para la práctica)
    models["XGBoost"] = Pipeline([
        ("pre", preprocessor),
        ("model", xgb.XGBClassifier(
            scale_pos_weight=ratio,  # Manejo de desbalanceo específico de XGBoost
            random_state=random_state,
            eval_metric='logloss',
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            verbosity=0
        ))
    ])
    
    # 5. Red Neuronal (Keras) - solo si TensorFlow está disponible
    if TENSORFLOW_AVAILABLE:
        from sklearn.utils.class_weight import compute_class_weight
        class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
        weight_dict = {0: class_weights[0], 1: class_weights[1]}
        
        # Keras no se integra fácilmente en Pipeline, entrenamiento separado
        keras_model = _train_keras_model(
            X_train_proc, y_train.values,
            X_val_proc, y_val.values,
            class_weight=weight_dict
        )
        
        # Guardar modelo Keras
        keras_path = MODELS_DIR / "NeuralNetwork.keras"
        keras_model.save(keras_path)
        
        # Evaluar Keras
        y_proba = keras_model.predict(X_val_proc).flatten()
        y_pred = (y_proba > 0.5).astype(int)
        metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "f1": f1_score(y_val, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_val, y_proba)
        }
        
        models_keras = {
            "NeuralNetwork": {
                "metrics": {k: float(v) for k, v in metrics.items()},
                "path": str(keras_path)
            }
        }
    else:
        models_keras = {}
        print(" TensorFlow no disponible - saltando red neuronal")
    
    # === ENTRENAMIENTO DE MODELOS scikit-learn ===
    results: Dict[str, Any] = {"models": {}, "best_model": None}
    
    best_score = -float("inf")
    best_name = None
    
    for name, pipeline in models.items():
        print(f"Entrenando {name}...")
        pipeline.fit(X_train, y_train)
        metrics = _score_model(pipeline, X_val, y_val)
        
        # Guardar modelo
        model_path = MODELS_DIR / f"{name}.pkl"
        joblib.dump(pipeline, model_path)
        
        results["models"][name] = {
            "metrics": metrics,
            "path": str(model_path)
        }
        
        score = metrics.get(primary_metric, 0.0)
        print(f"   {primary_metric}: {score:.4f}")
        
        if score > best_score:
            best_score = score
            best_name = name
    
    # Añadir Keras a resultados
    results["models"].update(models_keras)
    
    # Comparar Keras con el mejor modelo scikit-learn
    if TENSORFLOW_AVAILABLE and models_keras:
        keras_auc = models_keras["NeuralNetwork"]["metrics"]["roc_auc"]
        if keras_auc > best_score:
            best_score = keras_auc
            best_name = "NeuralNetwork"
            best_path = MODELS_DIR / "best_model.pkl"
            # Guardar referencia al modelo Keras (no se puede joblib)
            results["best_model"] = {
                "name": "NeuralNetwork",
                "path": str(MODELS_DIR / "NeuralNetwork.keras"),
                "score": best_score,
                "note": "Modelo Keras - cargar con tensorflow.keras.models.load_model()"
            }
    
    # Guardar mejor modelo de scikit-learn
    if best_name and best_name in results["models"] and best_name != "NeuralNetwork":
        best_path = MODELS_DIR / "best_model.pkl"
        joblib.dump(joblib.load(MODELS_DIR / f"{best_name}.pkl"), best_path)
        results["best_model"] = {
            "name": best_name,
            "path": str(best_path),
            "score": best_score
        }
    
    # === OPTIMIZACIÓN DE HIPERPARÁMETROS (opcional) ===
    if optimize_hyperparams and best_name and best_name != "NeuralNetwork":
        print("\n Optimizando hiperparámetros del mejor modelo...")
        best_model_path = MODELS_DIR / f"{best_name}.pkl"
        best_pipeline = joblib.load(best_model_path)
        
        # Ejemplo de optimización para XGBoost
        if best_name == "XGBoost":
            param_grid = {
                'model__n_estimators': [100, 200, 300],
                'model__max_depth': [3, 6, 9],
                'model__learning_rate': [0.01, 0.05, 0.1]
            }
            
            search = RandomizedSearchCV(
                best_pipeline,
                param_grid,
                n_iter=10,
                cv=3,
                scoring='roc_auc',
                random_state=random_state,
                n_jobs=-1
            )
            search.fit(X_train, y_train)
            
            # Guardar modelo optimizado
            best_optimized_path = MODELS_DIR / f"{best_name}_optimized.pkl"
            joblib.dump(search.best_estimator_, best_optimized_path)
            results["optimized_model"] = {
                "name": best_name,
                "path": str(best_optimized_path),
                "best_params": search.best_params_,
                "score": search.best_score_
            }
            print(f"   Mejor score CV: {search.best_score_:.4f}")
    
    # Mostrar resumen final
    print("\n" + "="*50)
    print(" RESULTADOS FINALES")
    print("="*50)
    for name, info in results["models"].items():
        auc = info["metrics"]["roc_auc"]
        print(f"   {name:20} AUC: {auc:.4f}")
    
    if results["best_model"]:
        print(f"\n MEJOR MODELO: {results['best_model']['name']} (AUC: {results['best_model']['score']:.4f})")
    
    return results


def load_model(path: str | Path) -> Any:
    """Carga un modelo guardado."""
    path = Path(path)
    if path.suffix == '.keras':
        from tensorflow.keras.models import load_model
        return load_model(path)
    else:
        return joblib.load(path)


if __name__ == "__main__":
    from src.data_loader import load_raw_dataset
    
    try:
        df = load_raw_dataset()
        resumen = train_models(df, optimize_hyperparams=True)
        print("\n Entrenamiento completado")
        print(f"Modelos guardados en: {MODELS_DIR}")
    except Exception as exc:
        print("No se pudo entrenar: ", exc)
        import traceback
        traceback.print_exc()