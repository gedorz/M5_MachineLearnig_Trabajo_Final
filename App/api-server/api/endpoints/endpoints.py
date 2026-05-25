import logging

from fastapi import FastAPI,APIRouter,Depends, HTTPException, status
from dataBaseManagement.dbManagement import get_db
from dataBaseManagement.dbservices import TaskManager
from dataBaseManagement.schemas import TaskCreate, TaskUpdate, TaskResponse
from typing import List

router = APIRouter()
logger = logging.getLogger("api.endpoints")

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
                version="1.0.5",
                contact={
                    "name": "Creador: Diego Gil & German Dario Realpe Zambrano",
                    "email": "gedorz@gmail.com",
                })
    return app

# Endpoints de la API para crear una tarea
@router.post("/tasks/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def crear_tarea(task: TaskCreate, db=Depends(get_db)):
    logger.info("event=create_task_start title=%s", task.titulo)
    manager = TaskManager(db)
    created_task = manager.add_task(task)
    logger.info("event=create_task_success task_id=%s", created_task.get("id"))
    return created_task
    
# cambiar el estado de una tarea a completada
@router.put("/tasks/completar/{task_id}", response_model=TaskResponse)
def marcar_completada(task_id: int, db=Depends(get_db)):
    logger.info("event=complete_task_start task_id=%s", task_id)
    manager = TaskManager(db)
    try:
        updated_task = manager.set_task_completed(task_id)
        logger.info("event=complete_task_success task_id=%s", task_id)
        return updated_task
    except ValueError as e:
        logger.warning("event=complete_task_not_found task_id=%s detail=%s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

# Actualización de tarea (no requerida en los tests pero implementada para completar la API)
@router.put("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
def actualizar_tarea(task_id: int, task_update: TaskUpdate, db=Depends(get_db)):
    logger.info("event=update_task_start task_id=%s", task_id)
    manager = TaskManager(db)
    try:
        updated_task = manager.update_task(task_id, task_update)
        logger.info("event=update_task_success task_id=%s", task_id)
        return updated_task
    except ValueError as e:
        logger.warning("event=update_task_not_found task_id=%s detail=%s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )   

# Endpoint para listar todas las tareas    
@router.get("/tasks/", response_model=List[TaskResponse])
def listar_tareas(db=Depends(get_db)):
    logger.info("event=list_tasks")
    manager = TaskManager(db)
    return manager.get_all_tasks()

# Endpoint para listar tareas caducadas
@router.get("/tasks/caducadas", response_model=List[TaskResponse])
def obtener_tareas_caducadas(db=Depends(get_db)):
    logger.info("event=list_expired_tasks")
    manager = TaskManager(db)
    return manager.get_expired_tasks()

# Endpoint para contar tareas caducadas
@router.get("/tasks/caducadas/count")
def contar_caducadas(db=Depends(get_db)):
    logger.info("event=count_expired_tasks")
    manager = TaskManager(db)
    return {"overdue": manager.count_overdue()}

# Endpoint para obtener detalles de una tarea específica
@router.get("/tasks/{task_id}", response_model=TaskResponse)
def obtener_tarea(task_id: int, db=Depends(get_db)):
    logger.info("event=get_task_start task_id=%s", task_id)
    manager = TaskManager(db)
    try:
        task = manager.get_task(task_id)
        logger.info("event=get_task_success task_id=%s", task_id)
        return task
    except ValueError as e:
        logger.warning("event=get_task_not_found task_id=%s detail=%s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )

# Endpoint para eliminar una tarea
@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_tarea(task_id: int, db=Depends(get_db)):
    logger.info("event=delete_task_start task_id=%s", task_id)
    manager = TaskManager(db)
    try:
        manager.delete_task(task_id)
        logger.info("event=delete_task_success task_id=%s", task_id)
    except ValueError as e:
        logger.warning("event=delete_task_not_found task_id=%s detail=%s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    return None

# Endpoint raíz para verificar que la API está funcionando
@router.get("/")
def root():
    return {"message": "Task Management API"}
