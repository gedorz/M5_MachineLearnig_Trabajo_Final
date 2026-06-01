# Actividad final del módulo 5 - Programación Avanzada : Management API

Para esta actividad se crea:
    * Un archivo README.md con una breve explicación de los endpoints implementados.
    * Una carpeta api, dentro de la cual esté el código fuente de la aplicación web.
    * Un archivo test_python.py, script en Python usando requests, debidamente comentado, que
      Interactúe con la API (apuntando a localhost) y compruebe resultados.

# Is done: Descripción explicativa de la actividad entregada
## Creación de un entorno virtual en Python 

### 1. Is done: Crear entorno virtual
    Se crea un entorno virtual de Python para la creación de la API de FastAPI
    y su base de datos mediante la postgres
    Se hizo mediante los siguientes comandos.
```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/Mac
    python -m venv .venv
    source .venv/bin/activate
```

### 2. Is done:  Instalar dependencias
    Mediante el archivo de  requirements.txt
    se realizar la inclusión de los requerimientos de la aplicación.
    Esto se realiza con el siguiente comando

```bash
    pip install -r requirements.txt
```

### 3. Is done: Como Ejecutar la aplicación API

    Se crea una API con postgres + SQLAlchemy 
    para actualizar la tabla de (dataset_operations, dataset_versions,datasets)
    para ejecutar la api puedes usar cualquiera de estos comandos:

```bash
    uvicorn main:app --reload
```

La API estará disponible en `http://localhost:80` ó `http://localhost/apim5`

## Endpoints

### Is done: Documentacion de todos los endpoints

- `GET  /` - estado básico de la API.
- `GET  /apim5/openapi.json` - esquema OpenAPI de la API.
- `POST /train` - entrena modelos usando un dataset almacenado en base de datos.
- `POST /predict` - genera predicciones con el modelo cargado.
- `POST /evaluate` - evalúa los modelos existentes y genera métricas comparativas.

- `POST /cargadatoscsv` - argadatoscsv
- `POST /datasets/upload` - Upload Dataset
- `GET  /datasets/{dataset_id}` - Get Dataset
- `GET  /datasets/{dataset_id}/preview` - Preview Latest Dataset Version

- `GET /datasets/{dataset_id}/versions/{version_id}/` - Preview Dataset Version
- `GET /datasets/{dataset_id}/null-summary` -  Null Summary Latest Dataset Version
- `GET /datasets/{dataset_id}/versions/{version_id}/null-summary` -  Null Summary Dataset Version
- `POST /datasets/{dataset_id}/versions/{version_id}/lowercase-columns` -  Lowercase Dataset Columns

- `GET /datasets-viewer/{dataset_id}/versions` -  List Dataset Versions
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/data-info` -   Dataset Data Info
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/distribution` -  Dataset Distribution Plots
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/distribution-cancelaciones` -  Dataset Distribution Cancelaciones
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/histogramas-numericos` -  Dataset Histogramas Numericos
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/boxplots-outliers` -  Dataset Boxplots Outliers
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/histplot-adr` -  Dataset Histplot Adr
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/histplot-adr-kde` -  Dataset Histplot Adr Kde
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/pairplot Dataset Pairplot` - 
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/nulls-heatmap Dataset Nulls Heatmap` - 
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/cancelaciones-por-hotel` -  Dataset Cancelaciones Por Hotel
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/cancelaciones-por-mes` -  Dataset Cancelaciones Por Mes
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/lead-time-distribution` -  Dataset Lead Time Distribution
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/adr-por-hotel-cancelacion` -  Dataset Adr Por Hotel Cancelacion
- `GET /datasets-viewer/{dataset_id}/versions/{version_id}/plots/correlacion-variable-objetivo` -  Dataset Correlacion Variable Objetivo

- `GET /features/profile/{dataset_id}/versions/{version_id}` -  Feature Profile
- `POST /features/plan Create Feature Plan
- `GET /features/plan/{dataset_id}/versions/{version_id}/latest` -  Get Latest Feature Plan 
- `POST /features/apply Apply` -  Feature Plan
- `POST /features/automl/train` -  Train With Feature Plan


## Is done:Documentación interactiva

Para ejecutar la aplicación, accede a:
- Swagger UI: `http://localhost/apim5/docs#/`

### Ejemplo de uso de `/train`

```bash
curl -X POST http://localhost/train \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_id": 1,
        "version_id": 1,
        "test_size": 0.2,
        "random_state": 42,
        "primary_metric": "roc_auc"
    }'
```

### Ejemplo de uso de `/evaluate`

```bash
curl -X POST http://localhost/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "version_id": 1,
    "model_name": "",
    "test_size": 0.2,
    "random_state": 42,
    "primary_metric": "roc_auc"
  }'
```

### Ejemplo de uso de `/predict`

```bash
curl -X POST http://localhost/predict \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "limit": 10}'
```

## 8 Estructura del proyecto Dataset Machine learnig y Deep Learning

Estructura para organizar un proyecto de Machine Learning de forma profesional y escalable.

```bash
proyecto-final-ML/
│
├── .gitignore                             # Archivos que no se suben al repo (e.g., modelos, archivos de desarrollo)
├── APP/                                   # Datos usados en el proyecto
│   ├── api-server/                        # Api de servicio para el proceso y entrenamiento de dato
│   ├── dockerFiles_m5/                    # Constructor de los servidores de Fastapi base de datos de postgres y web UI
│   └── html_nginx/                        # Pagina web para cargar los datos activar el reentrenamiento y
│       └── web                            # mostrar los resultados de los modelos y predicciones. 
│           └──react-app
│               └──index.html                 # entrada a toda la app
│          
└── data/                                  # Datos usados en el proyecto Volumen de Dockerfiles_m5_api_data_m5
    ├── Datasets 
    │   ├── raw/                           # Datos originales sin procesar del csv
    │   └── versions/                      # 
    │       └── Dataset_"#"                # Datos tras limpieza y transformación (listos para modelar)  en formato csv  
    └── models                             # modelos generados por train     
        ├── best_model.pkl
        ├── DecisionTree.pkl
        ├── LogisticRegression.pkl
        ├── NeuralNetwork.keras
        ├── RandomForest.pkl
        └── XGBoost.pkl


```