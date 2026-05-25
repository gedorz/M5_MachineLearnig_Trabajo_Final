import logging
from typing import Any
from fastapi import  APIRouter, HTTPException
from DataBaseManagement.dbConectionPostgres import get_db_tasks
from DataBaseManagement.schemasTasks import TaskCreate, TaskMove, TaskUpdate, TaskResponse
from DataBaseManagement.dbservicesTasks import TaskServicesManager
from fastapi import Depends, status
from typing import List

router = APIRouter()
logger = logging.getLogger("api.endpointsTasks")

# Endpoints de la API para crear una tarea
@router.post("/tasks/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def crear_tarea(task: TaskCreate, db=Depends(get_db_tasks)):
    logger.info("event=create_task_start title=%s", task.titulo)
    manager: TaskServicesManager = TaskServicesManager(db)
    created_task = manager.add_task(task)
    logger.info("event=create_task_success task_id=%s", created_task.get("id"))
    return created_task
    
# cambiar el estado de una tarea a completada
@router.put("/tasks/completar/{task_id}", response_model=TaskResponse)
def marcar_completada(task_id: int, db=Depends(get_db_tasks)):
    logger.info("event=complete_task_start task_id=%s", task_id)
    manager = TaskServicesManager(db)
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
def actualizar_tarea(task_id: int, task_update: TaskUpdate, db=Depends(get_db_tasks)):
    logger.info("event=update_task_start task_id=%s", task_id)
    manager = TaskServicesManager(db)
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
def listar_tareas(db=Depends(get_db_tasks)):
    logger.info("event=list_tasks")
    manager = TaskServicesManager(db)
    return manager.get_all_tasks()


@router.get("/tasks/gantt")
def listar_tareas_gantt(db=Depends(get_db_tasks)):
    logger.info("event=list_tasks_gantt")
    manager = TaskServicesManager(db)
    return manager.get_gantt_items()

# Endpoint para listar tareas caducadas
@router.get("/tasks/caducadas", response_model=List[TaskResponse])
def obtener_tareas_caducadas(db=Depends(get_db_tasks)):
    logger.info("event=list_expired_tasks")
    manager = TaskServicesManager(db)
    return manager.get_expired_tasks()

# Endpoint para contar tareas caducadas
@router.get("/tasks/caducadas/count")
def contar_caducadas(db=Depends(get_db_tasks)):
    logger.info("event=count_expired_tasks")
    manager = TaskServicesManager(db)
    return {"overdue": manager.count_overdue()}

# Endpoint para obtener detalles de una tarea específica
@router.get("/tasks/{task_id}", response_model=TaskResponse)
def obtener_tarea(task_id: int, db=Depends(get_db_tasks)):
    logger.info("event=get_task_start task_id=%s", task_id)
    manager = TaskServicesManager(db)
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

# Endpoint para mover una tarea (cambiar su padre) — para drag and drop
@router.patch("/tasks/{task_id}/move", response_model=TaskResponse)
def mover_padre_tarea(task_id: int, body: TaskMove, db=Depends(get_db_tasks)):
    logger.info("event=move_task_start task_id=%s new_parent=%s", task_id, body.id_padre)
    manager = TaskServicesManager(db)
    try:
        updated = manager.move_task(task_id, body.id_padre)
        logger.info("event=move_task_success task_id=%s", task_id)
        return updated
    except ValueError as e:
        logger.warning("event=move_task_not_found task_id=%s detail=%s", task_id, str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Endpoint para eliminar una tarea
@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_tarea(task_id: int, db=Depends(get_db_tasks)):
    logger.info("event=delete_task_start task_id=%s", task_id)
    manager = TaskServicesManager(db)
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