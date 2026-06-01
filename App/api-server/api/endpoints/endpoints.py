
from fastapi import FastAPI, APIRouter
from .endpointsCargaDatos import router as cargadatos_router
from .endpointsDatasets import router as datasets_router
from .endpointsDatasetsViewer import router as datasets_viewer_router
from .endPointFeatures import router as features_router
from .endPointEntrenarAutoML import router as entrenar_automl_router
    
router = APIRouter()
router.include_router(cargadatos_router)
router.include_router(datasets_router)
router.include_router(datasets_viewer_router)
router.include_router(features_router)
router.include_router(entrenar_automl_router)

def init_fastapi():
    description = """
    Actividad final del módulo 5 - Machine learnig y Deep Learning. 

    ## Objetivos de aprendizaje:
        - Entrenar modelos de manera muy rápida y eficiente, probando diferentes 
        - algoritmos al mismo tiempo y ofreciendo el resultado al usuario denominadas librerías de 
        - AutoML, algunos ejemplos son PyCaret, MLJar, H2O, TPOT, etc. 
        - Desplegar modelos de Machine Learning en producción utilizando contenedores Docker,
        - Implementar una API RESTful con FastAPI para servir un modelo de Machine Learning.
    ## Tecnologías utilizadas:
        - Python 3.8+
        - FastAPI
        - postgreSQL
        - psycopg2
        - Pydantic
    ## Modelo de DB:
        - TaskDB: id, titulo, contenido, status, deadline, created_at, updated_at
        - Pydantic: TaskCreate, TaskUpdate, TaskResponse (hereda orm_mode)
        - TaskManager con encapsulamiento + abstracción:  _clean_text() (normaliza / censura palabras malsonantes) 
    """
    app = FastAPI(title="Prediccion de cancelacion de reservas API",
                description=description,
                version="1.0.7",
                contact={
                    "name": "Creador: Diego Gil & German Dario Realpe Zambrano",
                    "email": "gedorz@gmail.com",
                })
    return app


# Endpoint raíz para verificar que la API está funcionando
@router.get("/")
def root():
    return {"status": "ok", "hint": "Ir a /docs o usar POST /analyze o POST /analyze-system"}
