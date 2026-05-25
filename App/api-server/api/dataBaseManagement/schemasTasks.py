from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field   

# Modelos Pydantic para la gestión de tareas
# Modelo para crear una tarea de forma simplificada, sin campos de ID o timestamps
class TaskCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=100, description="Título de la tarea")
    contenido: str = Field(min_length=1, max_length=200, description="Contenido de la tarea")
    startline: Optional[date] = Field(default=None, description="Fecha de inicio")
    deadline: date = Field(description="Fecha de vencimiento")
    id_padre: Optional[int] = Field(default=None, description="ID de la tarea padre")
    id_user: Optional[int] = Field(default=None, description="ID del usuario responsable")

# Modelo para actualizar una tarea, permitiendo editar todos los campos excepto el ID y los timestamps
class TaskUpdate(BaseModel):
    titulo: str = Field(min_length=1, max_length=100, description="Edita título de la tarea") 
    contenido: str = Field(min_length=1, max_length=200, description="Edita contenido de la tarea")
    startline: Optional[date] = Field(default=None, description="Edita fecha de inicio")
    deadline: date = Field(description="Edita fecha de vencimiento")
    completada: bool = Field(description="Edita estado de completado")
    id_padre: Optional[int] = Field(default=None, description="ID de la tarea padre")
    id_user: Optional[int] = Field(default=None, description="ID del usuario responsable")

# Modelo para mover una tarea a otro padre
class TaskMove(BaseModel):
    id_padre: Optional[int] = Field(default=None, description="ID del nuevo padre (null para raíz)")

# Modelo para la respuesta de la API, incluyendo todos los campos de la tarea
class TaskResponse(BaseModel):
    id: int
    id_padre: Optional[int] = None
    id_user: Optional[int] = None
    titulo: str
    contenido: str
    startline: Optional[datetime] = None
    deadline: date
    completada: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
