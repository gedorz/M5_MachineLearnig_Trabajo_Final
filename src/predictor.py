from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from config import MODELS_DIR


def _load_keras_model(path: Path):
    try:
        from tensorflow.keras.models import load_model

        return load_model(path)
    except ImportError:
        raise ImportError("TensorFlow necesario para cargar modelos .keras")


def load_model_by_name(model_name: Optional[str] = None) -> Tuple[Any, str, str]:
    """Carga el modelo solicitado.

    Retorna una tupla (model_object, model_type, model_identifier)
    donde model_type es 'sklearn' o 'keras'.
    """
    # Preferir explicitamente el modelo indicado
    if model_name:
        pkl = MODELS_DIR / f"{model_name}.pkl"
        if pkl.exists():
            return joblib.load(pkl), "sklearn", model_name

        keras_p = MODELS_DIR / f"{model_name}.keras"
        if keras_p.exists():
            return _load_keras_model(keras_p), "keras", model_name

        raise FileNotFoundError(f"Modelo {model_name} no encontrado en {MODELS_DIR}")

    # Si no se especifica, intentar cargar best_model.pkl
    best = MODELS_DIR / "best_model.pkl"
    if best.exists():
        return joblib.load(best), "sklearn", "best_model"

    # Si no existe, elegir el primer .pkl disponible
    for p in MODELS_DIR.glob("*.pkl"):
        if p.stem == "best_model":
            continue
        try:
            return joblib.load(p), "sklearn", p.stem
        except Exception:
            continue

    # Finalmente buscar modelos Keras
    for k in MODELS_DIR.glob("*.keras"):
        try:
            return _load_keras_model(k), "keras", k.stem
        except Exception:
            continue

    raise FileNotFoundError(f"No se encontraron modelos en {MODELS_DIR}")


def _find_sklearn_preprocessor() -> Optional[Any]:
    """Busca en MODELS_DIR un pipeline sklearn que contenga un step 'pre'.

    Esto se usa para transformar datos en caso de necesitarse para modelos Keras.
    """
    for p in MODELS_DIR.glob("*.pkl"):
        try:
            candidate = joblib.load(p)
            if hasattr(candidate, "named_steps") and "pre" in candidate.named_steps:
                return candidate.named_steps["pre"]
        except Exception:
            continue
    return None


def predict_from_dataframe(df: pd.DataFrame, model: Any, model_type: str) -> List[Dict[str, Any]]:
    """Recibe un DataFrame (features únicamente) y devuelve lista de predicciones.

    Cada elemento: {"prediction": int, "probability": float | None}
    """
    if model_type == "sklearn":
        # Los pipelines sklearn deben incluir el preprocesador internamente
        try:
            probs = None
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(df)
                probs = proba[:, 1].tolist()
            else:
                # Algunos estimadores usan decision_function
                try:
                    dec = model.decision_function(df)
                    # Normalizar a 0-1
                    dec = np.array(dec, dtype=float)
                    if dec.max() - dec.min() > 0:
                        probs = ((dec - dec.min()) / (dec.max() - dec.min())).tolist()
                    else:
                        probs = [float(0.0) for _ in range(len(dec))]
                except Exception:
                    probs = [None for _ in range(len(df))]

            preds = model.predict(df).tolist()
            return [
                {"prediction": int(p), "probability": (float(pr) if pr is not None else None)}
                for p, pr in zip(preds, probs)
            ]

        except Exception as exc:
            raise RuntimeError(f"Error al predecir con modelo sklearn: {exc}")

    elif model_type == "keras":
        # Keras necesita arrays numéricos; buscar preprocessor sklearn guardado
        pre = _find_sklearn_preprocessor()
        if pre is None:
            raise RuntimeError(
                "No se encontró preprocesador sklearn en MODELS_DIR. Guarde un pipeline sklearn con step 'pre' para usar modelos Keras."
            )

        X_proc = pre.transform(df)
        y_proba = model.predict(X_proc).flatten()
        preds = (y_proba > 0.5).astype(int).tolist()
        return [{"prediction": int(int(p)), "probability": float(prob)} for p, prob in zip(preds, y_proba.tolist())]

    else:
        raise ValueError("Tipo de modelo desconocido")


def predict_from_records(records: List[Dict[str, Any]], model: Any, model_type: str) -> List[Dict[str, Any]]:
    df = pd.DataFrame(records)
    return predict_from_dataframe(df, model, model_type)


if __name__ == "__main__":
    print("Ejemplo: cargar best_model y predecir con una fila de ejemplo")
    try:
        model, mtype, name = load_model_by_name()
        print("Modelo cargado:", name, "tipo:", mtype)
    except Exception as e:
        print("No se pudo cargar modelo:", e)
