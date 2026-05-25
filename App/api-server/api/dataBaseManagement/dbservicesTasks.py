from datetime import date, datetime, timezone
from typing import Any

from .dbManagementTasks import (
    insert_task,
    update_task,
    delete_task,
    get_task_by_id,
    get_all_tasks,
    get_expired_tasks,
    count_overdue_tasks,
)
from .schemasTasks import TaskCreate, TaskUpdate

# Clase TaskServicesManager para gestionar las operaciones CRUD de tareas en la base de datos
# y valiar eliminar palabras ofensivas en los campos de texto
# y convertir las fechas a formato datetime con zona horaria UTC para su almacenamiento en la base de datos.
# Además, se incluye la serialización de las tareas para convertir los campos de fecha a formato date al devolverlos en las respuestas de la API.
# se valida los json sean correctos y se maneja los errores de validación con un logger para facilitar la identificación y solución de problemas relacionados con la validación de solicitudes en la API.
class TaskServicesManager:
    def __init__(self, db: Any = None):
        self.db = db
        self.table_name = "tasks"

    def _clean_text(self, text: str | None) -> str:
        if text is None:
            return ""

        censored_words = ["maldicion", "tonto", "idiota", "malo", "feo"]
        cleaned_text = text.strip()
        for word in censored_words:
            cleaned_text = cleaned_text.replace(word, "****")
        return cleaned_text

    def _serialize_task(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)

        deadline = result.get("deadline")
        if isinstance(deadline, datetime):
            result["deadline"] = deadline.date()

        return result

    def add_task(self, task_create: TaskCreate) -> dict[str, Any]:
        payload = {
            "titulo": self._clean_text(task_create.titulo),
            "contenido": self._clean_text(task_create.contenido),
            "startline": datetime.combine(task_create.startline, datetime.min.time(), tzinfo=timezone.utc) if task_create.startline else None,
            "deadline": datetime.combine(task_create.deadline, datetime.min.time(), tzinfo=timezone.utc),
            "completada": False,
            "id_padre": task_create.id_padre,
            "id_user": task_create.id_user,
        }
        created = insert_task(payload, connection=self.db)
        return self._serialize_task(created)

    def get_task(self, task_id: int) -> dict[str, Any]:
        row = get_task_by_id(task_id, connection=self.db)
        if not row:
            raise ValueError(f"Tarea con ID {task_id} no encontrada")
        return self._serialize_task(row)

    def get_all_tasks(self) -> list[dict[str, Any]]:
        rows = get_all_tasks(connection=self.db)
        return [self._serialize_task(row) for row in rows]

    def set_task_completed(self, task_id: int) -> dict[str, Any]:
        updated = update_task(
            task_id,
            {
                "completada": True,
                "updated_at": datetime.now(timezone.utc),
            },
            connection=self.db,
        )
        if not updated:
            raise ValueError(f"Tarea con ID {task_id} no encontrada")
        return self._serialize_task(updated)

    def update_task(self, task_id: int, task_update: TaskUpdate) -> dict[str, Any]:
        payload = {
            "titulo": self._clean_text(task_update.titulo),
            "contenido": self._clean_text(task_update.contenido),
            "startline": datetime.combine(task_update.startline, datetime.min.time(), tzinfo=timezone.utc) if task_update.startline else None,
            "deadline": datetime.combine(task_update.deadline, datetime.min.time(), tzinfo=timezone.utc),
            "completada": task_update.completada,
            "id_padre": task_update.id_padre,
            "id_user": task_update.id_user,
            "updated_at": datetime.now(timezone.utc),
        }

        updated = update_task(task_id, payload, connection=self.db)
        if not updated:
            raise ValueError(f"Tarea con ID {task_id} no encontrada")
        return self._serialize_task(updated)

    def move_task(self, task_id: int, id_padre: int | None) -> dict[str, Any]:
        payload = {
            "id_padre": id_padre,
            "updated_at": datetime.now(timezone.utc),
        }
        updated = update_task(task_id, payload, connection=self.db)
        if not updated:
            raise ValueError(f"Tarea con ID {task_id} no encontrada")
        return self._serialize_task(updated)

    def delete_task(self, task_id: int) -> bool:
        deleted = delete_task(task_id, connection=self.db)
        if not deleted:
            raise ValueError(f"Tarea con ID {task_id} no encontrada")
        return True

    def get_expired_tasks(self) -> list[dict[str, Any]]:
        rows = get_expired_tasks(connection=self.db)
        return [self._serialize_task(row) for row in rows]

    def count_overdue_tasks(self) -> int:
        return count_overdue_tasks(connection=self.db)

    def count_overdue(self) -> int:
        return len(get_expired_tasks(connection=self.db))

    def get_gantt_items(self) -> list[dict[str, Any]]:
        tasks = self.get_all_tasks()
        gantt_rows: list[dict[str, Any]] = []
        for task in tasks:
            startline = task.get("startline") or task.get("created_at")
            deadline = task.get("deadline")
            gantt_rows.append(
                {
                    "id": task.get("id"),
                    "id_padre": task.get("id_padre"),
                    "id_user": task.get("id_user"),
                    "titulo": task.get("titulo"),
                    "contenido": task.get("contenido"),
                    "completada": task.get("completada"),
                    "startline": startline,
                    "deadline": deadline,
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                }
            )

        gantt_rows.sort(key=lambda row: (row.get("startline") or row.get("created_at") or datetime.now(timezone.utc)))
        return gantt_rows