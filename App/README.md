# Actividad final del módulo 5 - Programación Avanzada : Task Management API

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
    para actualizar la tabla de tareas 
    para ejecutar la api puedes usar cualquiera de estos comandos:

```bash
    uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Endpoints

### Is done: Documentacion de todos los endpoints

- `GET /` - Información de la API
- `POST /tasks/` - Crear una nueva tarea con los datos básicos (título, contenido, deadline )
- `GET /tasks/{task_id}` - Obtiene el contenido de una tarea por ID
- `PUT /tasks/{task_id}/completar` - Marcar una tarea como completada 
- `PUT /tasks/{task_id}` - Actualiza todos los datos de una tarea.
- `GET /tasks/` - Obtiene el listado  de todas las tareas.
- `GET /tasks/caducadas` - Obtiene la lista de tareas caducadas.
- `GET /tasks/caducadas/count` - Obtiene el número de tareas caducadas.
- `DELETE /tasks/{task_id}` - Borra la tarea solicitada.

## Is done: Ejecutar tests
    Se desarrolla un test para validar la ejecución de la API.
    Para esto se crea un archivo .py que ejecuta todos los endPoint de la API y evalúa si funcionan correctamente al ejecutar el siguiente bash. 
```bash 
    python .\test_api.py --reload
```

## Is done:Documentación interactiva

Para ejecutar la aplicación, accede a:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
