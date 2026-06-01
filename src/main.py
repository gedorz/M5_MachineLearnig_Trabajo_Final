from __future__ import annotations

from pathlib import Path
import argparse
import json

import sys

import pandas as pd

from config import MODELS_DIR, OUTPUTS_DIR


def _ensure_src_on_path():
    # En contenedor /src suele estar montado
    if "/src" not in sys.path:
        sys.path.insert(0, "/src")
    if "/" not in sys.path:
        sys.path.insert(0, "/")


def main(data_path: Path, test_size: float = 0.2, random_state: int = 42, primary_metric: str = "roc_auc"):
    _ensure_src_on_path()

    from model_trainer import train_models, _get_feature_columns, _build_preprocessor
    from evaluator import ModelEvaluator
    from predictor import load_model_by_name, predict_from_dataframe

    print("Leyendo datos desde:", data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {data_path}")

    df = pd.read_csv(data_path)

    if "is_canceled" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'is_canceled' como target")

    print("Iniciando entrenamiento...")
    results = train_models(df, target_col="is_canceled", test_size=test_size,
                           random_state=random_state, primary_metric=primary_metric,
                           optimize_hyperparams=False)

    print("Entrenamiento finalizado. Resultados:")
    print(json.dumps(results.get("models", {}), indent=2, default=str))

    # Preparar evaluación: split y preprocesador
    from sklearn.model_selection import train_test_split

    X = df.drop(columns=["is_canceled"])
    y = df["is_canceled"]

    numeric_cols, categorical_cols = _get_feature_columns(df, "is_canceled")
    preprocessor = _build_preprocessor(numeric_cols, categorical_cols)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if len(y.unique()) > 1 else None
    )

    preprocessor.fit(X_train)
    X_test_proc = preprocessor.transform(X_test)

    # Cargar modelos guardados y adaptar inputs
    models_dict = {}
    from joblib import load as joblib_load

    # Helper adapter para que evaluator reciba objetos con predict/predict_proba
    class ModelAdapter:
        def __init__(self, model, model_type: str, uses_pipeline: bool = False, pre=None):
            self.model = model
            self.model_type = model_type
            self.uses_pipeline = uses_pipeline
            self.pre = pre

        def predict(self, X):
            if self.model_type == "keras":
                Xn = self.pre.transform(X) if self.pre is not None else X
                proba = self.model.predict(Xn).flatten()
                return (proba > 0.5).astype(int)
            if self.uses_pipeline:
                return self.model.predict(X)
            # modelo espera X ya transformado
            Xn = self.pre.transform(X) if self.pre is not None else X
            return self.model.predict(Xn)

        def predict_proba(self, X):
            if self.model_type == "keras":
                Xn = self.pre.transform(X) if self.pre is not None else X
                proba = self.model.predict(Xn).flatten()
                return np.vstack([1 - proba, proba]).T
            if self.uses_pipeline:
                return self.model.predict_proba(X)
            Xn = self.pre.transform(X) if self.pre is not None else X
            return self.model.predict_proba(Xn)

    import numpy as np

    # Buscar modelos en MODELS_DIR
    for p in MODELS_DIR.glob("*.pkl"):
        if p.stem == "best_model":
            continue
        try:
            m = joblib_load(p)
            uses_pipeline = hasattr(m, "named_steps") and "pre" in m.named_steps
            if uses_pipeline:
                # pipeline expects raw DataFrame
                models_dict[p.stem] = ModelAdapter(m, "sklearn", uses_pipeline=True)
            else:
                models_dict[p.stem] = ModelAdapter(m, "sklearn", uses_pipeline=False, pre=preprocessor)
        except Exception as e:
            print(f"No se pudo cargar modelo {p}: {e}")

    # Keras
    for k in MODELS_DIR.glob("*.keras"):
        try:
            from src.predictor import _load_keras_model

            km = _load_keras_model(k)
            models_dict[k.stem] = ModelAdapter(km, "keras", uses_pipeline=False, pre=preprocessor)
        except Exception as e:
            print(f"No se pudo cargar Keras {k}: {e}")

    if not models_dict:
        print(f"No se encontraron modelos en {MODELS_DIR}")
    else:
        evaluator = ModelEvaluator(output_dir=MODELS_DIR / "evaluation_reports")
        print("Generando reporte de evaluación...")
        report = evaluator.generate_report(models_dict, X_test, y_test, feature_names=numeric_cols + categorical_cols, save=True)
        print("Reporte generado. Comparison:")
        print(report.get("comparison"))

    # Prueba rápida predictor: cargar best_model y predecir primeras filas
    try:
        model, model_type, identifier = load_model_by_name(None)
        print("Cargando modelo para predecir:", identifier, model_type)
        sample = X.head(5)
        preds = predict_from_dataframe(sample, model, model_type)
        print("Predicciones de muestra:")
        print(json.dumps(preds, indent=2))
    except Exception as e:
        print("No se pudo ejecutar predicción de ejemplo:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquesta pipeline ML: train -> evaluate -> predict")
    parser.add_argument("--data", type=str, default="data/raw/dataset_practica_final.csv", help="Ruta al CSV de datos")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--random_state", type=int, default=42)
    args = parser.parse_args()

    data_path = Path(args.data)
    main(data_path, test_size=args.test_size, random_state=args.random_state)
