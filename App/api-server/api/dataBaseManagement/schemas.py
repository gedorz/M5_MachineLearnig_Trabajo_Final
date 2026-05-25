from datetime import datetime, date
from pydantic import BaseModel, Field   

# Is done: Modelos Pydantic para la gestión de tareas
# Modelo para crear una tarea de forma simplificada, sin campos de ID o timestamps
class TaskCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=100, description="Título de la tarea")
    contenido: str = Field(min_length=1, max_length=200, description="Contenido de la tarea")
    deadline: date = Field(description="Fecha de vencimiento")

# Modelo para actualizar una tarea, permitiendo editar todos los campos excepto el ID y los timestamps
class TaskUpdate(BaseModel):
    titulo: str = Field(min_length=1, max_length=100, description="Edita título de la tarea") 
    contenido: str = Field(min_length=1, max_length=200, description="Edita contenido de la tarea")
    deadline: date = Field(description="Edita fecha de vencimiento")
    completada: bool = Field(description="Edita estado de completado")

# Modelo para la respuesta de la API, incluyendo todos los campos de la tarea
class TaskResponse(BaseModel):
    id: int
    titulo: str
    contenido: str
    deadline: date
    completada: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
