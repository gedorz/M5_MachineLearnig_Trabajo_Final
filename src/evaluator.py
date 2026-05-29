# Métricas y visualización de resultados

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, roc_curve, confusion_matrix, classification_report,
    precision_recall_curve
)

from config import MODELS_DIR, OUTPUTS_DIR


class ModelEvaluator:
    """
    Evaluador de modelos para el problema de cancelación de reservas.
    Proporciona métricas consistentes y visualizaciones para comparar modelos.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa el evaluador.     
        Args:
            output_dir: Directorio donde guardar gráficos y reportes.
                       Por defecto usa OUTPUTS_DIR/evaluation
        """
        self.output_dir = output_dir or (OUTPUTS_DIR / "evaluation")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Métricas estándar que calcularemos
        self.metrics_names = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
        
    def evaluate_model(self, model: Any, X_test: pd.DataFrame, 
                       y_test: pd.Series, model_name: str = "Model") -> Dict[str, float]:
        """
        Evalúa un modelo y calcula todas las métricas.
        
        Args:
            model: Modelo entrenado (Pipeline o cualquier estimator con predict/predict_proba)
            X_test: Features de test
            y_test: Target real
            model_name: Nombre del modelo para logging       
        Returns:
            Diccionario con todas las métricas calculadas
        """
        # Predicciones
        y_pred = model.predict(X_test)
        
        # Probabilidades (para AUC y curvas)
        try:
            y_proba = model.predict_proba(X_test)[:, 1]
        except (AttributeError, IndexError):
            # Si no tiene predict_proba, intentar decision_function
            try:
                y_proba = model.decision_function(X_test)
                # Normalizar a [0,1] si es necesario
                if y_proba.min() < 0:
                    y_proba = (y_proba - y_proba.min()) / (y_proba.max() - y_proba.min())
            except (AttributeError, ValueError):
                y_proba = y_pred  # Fallback a predicciones binarias
                print(f"{model_name}: No se pudo obtener probabilidades")
        
        # Calcular métricas
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        }
        
        # AUC solo si tenemos probabilidades
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))
        except ValueError:
            metrics["roc_auc"] = 0.0
            print(f"{model_name}: No se pudo calcular AUC")
        
        # Guardar también las predicciones para uso posterior
        metrics["_y_pred"] = y_pred
        metrics["_y_proba"] = y_proba
        
        return metrics
    
    def compare_models(self, models_dict: Dict[str, Any], 
                       X_test: pd.DataFrame, 
                       y_test: pd.Series) -> pd.DataFrame:
        """
        Compara múltiples modelos y devuelve DataFrame con resultados.
        
        Args:
            models_dict: Diccionario {nombre_modelo: modelo_entrenado}
            X_test: Features de test
            y_test: Target real
            
        Returns:
            DataFrame con métricas comparativas
        """
        results = []
        
        for name, model in models_dict.items():
            print(f" Evaluando {name}...")
            metrics = self.evaluate_model(model, X_test, y_test, name)
            metrics["model"] = name
            results.append(metrics)
        
        # Convertir a DataFrame
        df_results = pd.DataFrame(results)
        
        # Reordenar columnas
        cols = ["model"] + self.metrics_names
        df_results = df_results[[c for c in cols if c in df_results.columns]]
        
        # Ordenar por AUC descendente
        if "roc_auc" in df_results.columns:
            df_results = df_results.sort_values("roc_auc", ascending=False)
        
        return df_results
    
    def plot_confusion_matrix(self, model: Any, X_test: pd.DataFrame, 
                               y_test: pd.Series, model_name: str = "Model",
                               save: bool = True) -> plt.Figure:
        """
        Genera y muestra la matriz de confusión.
        
        Args:
            model: Modelo entrenado
            X_test: Features de test
            y_test: Target real
            model_name: Nombre del modelo
            save: Si guardar la figura en disco
            
        Returns:
            Figura de matplotlib
        """
        y_pred = model.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                    xticklabels=['No Cancelado (0)', 'Cancelado (1)'],
                    yticklabels=['No Cancelado (0)', 'Cancelado (1)'])
        ax.set_xlabel('Predicción')
        ax.set_ylabel('Valor Real')
        ax.set_title(f'Matriz de Confusión - {model_name}')
        
        # Añadir anotaciones con porcentajes
        total = np.sum(cm)
        for i in range(2):
            for j in range(2):
                percentage = cm[i, j] / total * 100
                ax.text(j + 0.5, i + 0.5, f'\n({percentage:.1f}%)',
                        ha='center', va='center', fontsize=10, color='gray')
        
        plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / f"confusion_matrix_{model_name}.png", 
                       dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_roc_curve(self, model: Any, X_test: pd.DataFrame, 
                        y_test: pd.Series, model_name: str = "Model",
                        save: bool = True) -> plt.Figure:
        """
        Genera y muestra la curva ROC.
        
        Args:
            model: Modelo entrenado
            X_test: Features de test
            y_test: Target real
            model_name: Nombre del modelo
            save: Si guardar la figura en disco
            
        Returns:
            Figura de matplotlib
        """
        try:
            y_proba = model.predict_proba(X_test)[:, 1]
        except (AttributeError, IndexError):
            try:
                y_proba = model.decision_function(X_test)
                if y_proba.min() < 0:
                    y_proba = (y_proba - y_proba.min()) / (y_proba.max() - y_proba.min())
            except (AttributeError, ValueError):
                print(f" {model_name}: No se puede generar curva ROC sin probabilidades")
                return None
        
        fpr, tpr, thresholds = roc_curve(y_test, y_proba)
        auc = roc_auc_score(y_test, y_proba)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(fpr, tpr, 'b-', label=f'{model_name} (AUC = {auc:.4f})', linewidth=2)
        ax.plot([0, 1], [0, 1], 'r--', label='Clasificador Aleatorio (AUC = 0.5)', linewidth=1)
        ax.set_xlabel('Tasa de Falsos Positivos (1 - Especificidad)')
        ax.set_ylabel('Tasa de Verdaderos Positivos (Sensibilidad)')
        ax.set_title(f'Curva ROC - {model_name}')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / f"roc_curve_{model_name}.png", 
                       dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_roc_comparison(self, models_dict: Dict[str, Any], 
                             X_test: pd.DataFrame, y_test: pd.Series,
                             save: bool = True) -> plt.Figure:
        """
        Compara curvas ROC de múltiples modelos en una sola figura.
        
        Args:
            models_dict: Diccionario {nombre_modelo: modelo_entrenado}
            X_test: Features de test
            y_test: Target real
            save: Si guardar la figura en disco
            
        Returns:
            Figura de matplotlib
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = ['blue', 'green', 'orange', 'red', 'purple', 'brown']
        auc_scores = {}
        
        for idx, (name, model) in enumerate(models_dict.items()):
            try:
                y_proba = model.predict_proba(X_test)[:, 1]
            except (AttributeError, IndexError):
                try:
                    y_proba = model.decision_function(X_test)
                    if y_proba.min() < 0:
                        y_proba = (y_proba - y_proba.min()) / (y_proba.max() - y_proba.min())
                except (AttributeError, ValueError):
                    continue
            
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            auc = roc_auc_score(y_test, y_proba)
            auc_scores[name] = auc
            
            color = colors[idx % len(colors)]
            ax.plot(fpr, tpr, color=color, label=f'{name} (AUC = {auc:.4f})', linewidth=2)
        
        ax.plot([0, 1], [0, 1], 'k--', label='Clasificador Aleatorio (AUC = 0.5)', linewidth=1)
        ax.set_xlabel('Tasa de Falsos Positivos')
        ax.set_ylabel('Tasa de Verdaderos Positivos')
        ax.set_title('Comparativa de Curvas ROC')
        ax.legend(loc='lower right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / "roc_comparison.png", dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_feature_importance(self, model: Any, feature_names: List[str],
                                 model_name: str = "Model", top_n: int = 20,
                                 save: bool = True) -> Optional[plt.Figure]:
        """
        Genera gráfico de importancia de características.
        
        Args:
            model: Modelo entrenado (debe tener .feature_importances_)
            feature_names: Nombres de las características
            model_name: Nombre del modelo
            top_n: Número de características a mostrar
            save: Si guardar la figura en disco
            
        Returns:
            Figura de matplotlib o None si el modelo no soporta feature importance
        """
        # Intentar obtener importancias
        importances = None
        
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = np.abs(model.coef_[0])
        elif hasattr(model, 'named_steps') and 'model' in model.named_steps:
            # Para pipelines de scikit-learn
            inner_model = model.named_steps['model']
            if hasattr(inner_model, 'feature_importances_'):
                importances = inner_model.feature_importances_
            elif hasattr(inner_model, 'coef_'):
                importances = np.abs(inner_model.coef_[0])
        
        if importances is None:
            print(f" {model_name}: No soporta feature importance")
            return None
        
        # Crear DataFrame con importancias
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False).head(top_n)
        
        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))
        sns.barplot(data=importance_df, x='importance', y='feature', ax=ax, palette='viridis')
        ax.set_xlabel('Importancia')
        ax.set_title(f'Top {top_n} Características Importantes - {model_name}')
        ax.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / f"feature_importance_{model_name}.png", 
                       dpi=150, bbox_inches='tight')
        
        return fig
    
    def generate_report(self, models_dict: Dict[str, Any], 
                        X_test: pd.DataFrame, y_test: pd.Series,
                        feature_names: Optional[List[str]] = None,
                        save: bool = True) -> Dict[str, Any]:
        """
        Genera un reporte completo de evaluación.
        
        Args:
            models_dict: Diccionario de modelos
            X_test: Features de test
            y_test: Target real
            feature_names: Nombres de características (para feature importance)
            save: Si guardar gráficos
            
        Returns:
            Diccionario con todas las métricas y rutas de gráficos
        """
        report = {
            "models": {},
            "comparison": None,
            "plots": {}
        }
        
        # 1. Comparar modelos
        print("Comparando modelos...")
        df_comparison = self.compare_models(models_dict, X_test, y_test)
        report["comparison"] = df_comparison.to_dict(orient='records')
        
        # 2. Generar gráficos para cada modelo
        for name, model in models_dict.items():
            print(f"Generando gráficos para {name}...")
            model_report = {}
            
            # Matriz de confusión
            cm_file = self.plot_confusion_matrix(model, X_test, y_test, name, save=save)
            if save and cm_file:
                model_report["confusion_matrix"] = str(self.output_dir / f"confusion_matrix_{name}.png")
            
            # Curva ROC
            roc_file = self.plot_roc_curve(model, X_test, y_test, name, save=save)
            if save and roc_file:
                model_report["roc_curve"] = str(self.output_dir / f"roc_curve_{name}.png")
            
            # Feature importance (si aplica y tenemos nombres)
            if feature_names:
                importance_file = self.plot_feature_importance(model, feature_names, name, save=save)
                if save and importance_file:
                    model_report["feature_importance"] = str(self.output_dir / f"feature_importance_{name}.png")
            
            report["models"][name] = model_report
        
        # 3. Gráfico comparativo ROC
        roc_comp_file = self.plot_roc_comparison(models_dict, X_test, y_test, save=save)
        if save and roc_comp_file:
            report["plots"]["roc_comparison"] = str(self.output_dir / "roc_comparison.png")
        
        # 4. Guardar reporte en JSON
        if save:
            # Convertir DataFrame a formato serializable
            report_serializable = {
                "models": {name: {k: v for k, v in metrics.items() 
                                 if not k.startswith('_')} 
                          for name, metrics in report["models"].items()},
                "comparison": report["comparison"],
                "plots": report["plots"]
            }
            
            with open(self.output_dir / "evaluation_report.json", 'w', encoding='utf-8') as f:
                json.dump(report_serializable, f, indent=2, default=str)
        
        return report


def quick_evaluate(model_path: Path, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """
    Función rápida para evaluar un modelo guardado.
    
    Args:
        model_path: Ruta al modelo guardado (.pkl o .joblib)
        X_test: Features de test
        y_test: Target real
        
    Returns:
        Diccionario con métricas
    """
    model = joblib.load(model_path)
    evaluator = ModelEvaluator()
    return evaluator.evaluate_model(model, X_test, y_test, model_path.stem)


if __name__ == "__main__":
    # Ejemplo de uso rápido (para pruebas)
    import joblib
    from sklearn.datasets import make_classification
    from sklearn.ensemble import RandomForestClassifier
    
    # Crear datos dummy
    X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # Entrenar modelo
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    # Evaluar
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_model(model, X_test, y_test, "RandomForest")
    print(metrics)