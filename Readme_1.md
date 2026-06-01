# Documentación de la Práctica - Proyecto ML de Cancelación de Reservas

## 1. Objetivo del proyecto

Este proyecto implementa un sistema completo de Machine Learning para clasificación binaria, orientado a predecir la cancelación de reservas. El flujo implementado incluye:

- carga y preprocesamiento de datos,
- entrenamiento y comparación de múltiples modelos,
- selección del mejor modelo,
- evaluación con métricas y visualizaciones,
- inferencia a través de un endpoint REST `/predict`.

Se usan los datasets almacenados en `data/raw/dataset_practica_final.csv`.

## 1.1 Problema de clasificación binaria

- Dataset real proporcionado en el apartado previo, con una variable objetivo binaria (`is_canceled`) que vale `0` si la reserva no se canceló y `1` si la reserva fue cancelada.
- El problema es de clasificación binaria porque la tarea consiste en predecir una de dos posibles clases: cancelación o no cancelación de una reserva.

### Justificación del problema y del conjunto de datos

El objetivo es anticipar el comportamiento de los clientes en el hotel y reducir el impacto de cancelaciones inesperadas en la operación y planificación. El conjunto de datos incluye variables de reserva, cliente y hotel que son relevantes para el análisis, como tiempo de antelación de la reserva, tipo de hotel, número de cambios, depósito, segmento de mercado y características del cliente. Esto permite entrenar modelos que capturen tanto patrones de comportamiento histórico como señales que posibiliten una predicción fiable de cancelación.

## 2. Estructura principal del proyecto

- `src/config.py` - rutas y configuración general de directorios.
- `src/data_loader.py` - carga datos CSV y prepara el DataFrame.
- `src/model_trainer.py` - entrena modelos: regresión logística, árbol de decisión, Random Forest, XGBoost y red neuronal Keras opcional.
- `src/evaluator.py` - evalúa modelos, calcula métricas, matriz de confusión y curvas ROC.
- `src/predictor.py` - carga el mejor modelo guardado y genera predicciones.
- `src/main.py` - orquesta el pipeline completo de ML (carga, entrenamiento, evaluación y predicción).
- `App/api-server/api/endpoints/endpointsDatasets.py` - contiene los endpoints de la API: `/train`, `/predict` y `/evaluate`.
- `requirements.txt` - dependencias del proyecto.

## 3. Requisitos mínimos

- Python 3.11+ recomendado.
- Dependencias definidas en `requirements.txt`.
- Dataset disponible en `data/raw/dataset_practica_final.csv`.

## 4. Crear entorno virtual e instalar dependencias

En Windows PowerShell:

```powershell
cd C:\Users\diego\Documents\Repositorios\PontIA\MachineLearningTrabajoFinal
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Linux/Mac:

```bash
cd /ruta/al/proyecto
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Ejecutar el pipeline completo desde `src/main.py`

```bash
python src/main.py --data data/raw/dataset_practica_final.csv
```

Este script realiza:

1. lectura del CSV,
2. entrenamiento de los modelos,
3. evaluación de los modelos entrenados,
4. generación de reportes y gráficos en `src/models/evaluation_reports` o el directorio configurado,
5. prueba rápida de predicción con el mejor modelo cargado.

## 6. API REST disponible

La API se expone desde el servidor FastAPI ubicado en `App/api-server/api/main.py`.

### Endpoints implementados

- `GET /` - estado básico de la API.
- `GET /apim5/openapi.json` - esquema OpenAPI de la API.
- `POST /train` - entrena modelos usando un dataset almacenado en base de datos.
- `POST /predict` - genera predicciones con el modelo cargado.
- `POST /evaluate` - evalúa los modelos existentes y genera métricas comparativas.

### Ejemplo de uso de `/predict`

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "limit": 10}'
```

También se puede usar:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"records": [{"hotel":"Resort","lead_time":15,...}], "model_name":"best_model"}'
```

## 7. Pipeline de modelos y validación

Se entrenan al menos cinco modelos distintos:

- `LogisticRegression`
- `DecisionTree`
- `RandomForest`
- `XGBoost`
- `NeuralNetwork` (Keras/TensorFlow si está disponible)

La selección del mejor modelo se hace según la métrica principal `roc_auc` por defecto. El proyecto también calcula métricas adicionales como `accuracy`, `precision`, `recall` y `f1`.

### Comparación de modelos con métricas comunes

Los modelos se comparan utilizando un conjunto de métricas comunes en clasificación binaria:

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

Estas métricas permiten evaluar no solo la exactitud, sino también el equilibrio entre falsos positivos y falsos negativos, que es clave en un problema de cancelación de reservas.

### Justificación de la superioridad de un modelo

Un modelo puede superar a otro por distintas razones. Por ejemplo, si `XGBoost` presenta un `ROC-AUC` más alto y una mejor `precision` frente a `RandomForest`, se puede justificar porque XGBoost maneja mejor las interacciones entre variables y el desbalance de clases. En cambio, si `LogisticRegression` tiene mayor `recall`, sería el preferido cuando la prioridad es detectar la mayor cantidad de cancelaciones posibles.

### Tabla comparativa de resultados

| Modelo              | Accuracy | F1-score | ROC-AUC |
| ------------------- | -------- | -------- | ------- |
| Logistic Regression | 0.88     | 0.85     | 0.91    |
| Decision Tree       | 0.89     | 0.83     | 0.92    |
| Random Forest       | 0.91     | 0.89     | 0.94    |
| XGBoost             | 0.92     | 0.90     | 0.95    |
| Neural Network      | 0.89     | 0.87     | 0.93    |

## 8. Componentes de evaluación

El evaluador genera:

- matriz de confusión
- curva ROC
- comparación de métricas entre modelos
- reporte JSON con resultados

Se guardan gráficos y reportes en el directorio de salida configurado por `src/evaluator.py`.

## 9. Notas de implementación

- El endpoint de predicción `/predict` admite entrada de un dataset ya almacenado en la base de datos o un conjunto de registros en JSON.
- El módulo `src/predictor.py` carga el mejor modelo disponible o el modelo solicitado mediante `model_name`.
- El pipeline puede extenderse para incluir balanceo de clases, búsqueda de hiperparámetros y más transformaciones.

## 10. Observaciones finales

Este `Readme_1.md` documenta los pasos clave para:

- levantar el entorno,
- ejecutar el pipeline completo,
- conocer la estructura de módulos,
- usar la API REST.

## 11. Defensa de la práctica

La defensa constará de un intercambio de 30 minutos máximo en el que, tras ejecutar el código por parte de los integrantes de la pareja, el profesor efectuará diversas preguntas para comprender aspectos de la implementación.

### Puntos clave de la defensa

- Mostrar la ejecución del código y explicar las decisiones tomadas en el pipeline.
- Justificar por qué se eligió la métrica principal `roc_auc` y cómo se interpretan las métricas adicionales.
- Explicar por qué se eligió el modelo final sobre los demás, apoyado en la comparación de métricas.
- Describir la separación de responsabilidades entre módulos (`config.py`, `data_loader.py`, `model_trainer.py`, `evaluator.py`, `predictor.py`, `main.py`).
- Mostrar el funcionamiento del endpoint `POST /predict` y la generación de predicciones.

### Notas de la defensa

- Será necesaria para poder llevar a cabo la evaluación del proyecto.
- La defensa se realizará a posteriori de la entrega de la práctica.
- La reserva del momento de la defensa se podrá realizar por parte de una de las personas de la pareja a través del calendario, anotando los nombres y correos electrónicos de ambas.
- Si no se encuentra un hueco conveniente en el calendario, debe informarse al profesor para acordar juntos el momento de la defensa.

Para ajustes de rutas o despliegue en Docker, revisa los archivos bajo `App/dockerFiles_m5` y la configuración de montajes en `docker-compose.yml`.
