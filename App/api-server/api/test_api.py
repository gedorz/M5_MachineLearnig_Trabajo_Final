import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from dataBaseManagement.dbManagement import get_postgres_connection_server

# Este un test para validar la funcionalidad de la API de gestión de tareas implementada con FastAPI.
# El test incluye casos para crear, actualizar, obtener, marcar como completada, eliminar tareas, así como para obtener tareas caducadas y manejar casos de datos incorrectos.
# Se utiliza la librería requests para realizar llamadas HTTP a la API y validar las respuestas.

load_dotenv()  # Cargar variables de entorno desde el archivo .env

URL = "http://localhost:8080"

client = requests.Session()

# Función para limpiar la base de datos antes de ejecutar los tests
def clear_db():
    with get_postgres_connection_server(host="localhost") as db:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM tasks")
        db.commit()

# Funcion para crear una tarea deacuerdo a un payload dado y devolver la respuesta de la
# API en formato json, junto con el payload utilizado para la creación
def createTask(payload):
    # Función para crear una nueva tarea y devolver su ID"""
    response = client.post(f"{URL}/tasks/", json=payload)
    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    return response.json(), payload 

# Crea una nueva tarea utilizando la función createTask y devuelve la respuesta de la API en formato json, junto con el payload utilizado para la creación
def createNewTask():
    # Función para crear una nueva tarea y devolver su ID"""
    payload = {
        "titulo": f"Prueba crear tarea: {datetime.now().isoformat()}",
        "contenido": f"Contenido de prueba: {datetime.now().isoformat()}",
        "deadline": str(date.today() + timedelta(days=3))
        }
    data, payload = createTask(payload)
    return data, payload

# Implementar test para crear una tarea con datos correctos

def test_crear_tarea():
    # Is done: Implementar test para crear una tarea con datos correctos"""
    clear_db()  # Limpiar la base de datos antes de ejecutar el test
    #Test para crear una tarea con datos correctos
    # Implementar test para crear una tarea con datos incorrectos que debe devolver 400
    data, payload = createNewTask()
    assert data["titulo"] == payload["titulo"], f"Expected titulo '{payload['titulo']}', got '{data['titulo']}'"
    assert data["contenido"] == payload["contenido"], f"Expected contenido '{payload['contenido']}', got '{data['contenido']}'"
    assert data["deadline"] == payload["deadline"], f"Expected deadline '{payload['deadline']}', got '{data['deadline']}'"
    return True 

# Test para actualizar una tarea existente con datos correctos y validar que los cambios se reflejen correctamente en la API
def test_actualizar_tarea():
    clear_db()
    payload = {
        "titulo": "Prueba para actualizar",
        "contenido": "Contenido para actualizar",
        "deadline": str(date.today() + timedelta(days=7))
    }
    data, payload = createTask(payload)
    taskID = data.get("id")
   
    update_payload = {
        "titulo": "Titulo Actualizado",
        "contenido": f"Contenido actualizado {datetime.now().isoformat()}",
        "deadline": str(date.today() + timedelta(days=8)),
        "completada": True
    }
    response = client.put(f"{URL}/tasks/{taskID}", json=update_payload )
    assert response.status_code == 202, f"Expected status code 202, got {response.status_code}"
    taskData = response.json()
    
    assert taskData["id"] == taskID, f"Expected task ID '{taskID}', got '{taskData['id']}'"
    assert taskData["titulo"] == update_payload["titulo"], f"Expected titulo '{update_payload['titulo']}', got '{taskData['titulo']}'"
    assert taskData["contenido"] == update_payload["contenido"], f"Expected contenido '{update_payload['contenido']}', got '{taskData['contenido']}'"
    assert taskData["deadline"] == update_payload["deadline"], f"Expected deadline '{update_payload['deadline']}', got '{taskData['deadline']}'"
    assert taskData["completada"] is True
    

def test_obtener_tarea():
    # Is done: Implementar test para obtener una tarea por ID"""
    clear_db()  # Limpiar la base de datos antes de ejecutar el test
    data, payload = createNewTask()  # Crear una nueva tarea y obtener su ID
    taskID = data.get("id")  

    # Obtener la tarea creada por su ID y validar los datos devueltos por la API
    response = client.get(f"{URL}/tasks/{taskID}")
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert data["id"] == taskID, f"Expected task ID '{taskID}', got '{data['id']}'"
    assert data["titulo"] == payload["titulo"], f"Expected titulo '{payload['titulo']}', got '{data['titulo']}'"
    assert data["contenido"] == payload["contenido"], f"Expected contenido '{payload['contenido']}', got '{data['contenido']}'"
    assert data["deadline"] == payload["deadline"], f"Expected deadline '{payload['deadline']}', got '{data['deadline']}'"

def test_marcar_completada():
    # Is done: Implementar test para marcar una tarea como completada
    clear_db()  # Limpiar la base de datos antes de ejecutar el test
    responseCreateTask, payload = createNewTask()  # Crear una nueva tarea y obtener su ID
    taskID = responseCreateTask.get("id")  

    # Obtener la tarea creada por su ID y validar que el campo "completada" sea False por defecto
    taskResponse = client.get(f"{URL}/tasks/{taskID}")
    assert taskResponse.status_code == 200, f"Expected status code 200, got {taskResponse.status_code}"
    taskData = taskResponse.json()
    assert taskData["id"] == taskID, f"Expected task ID '{taskID}', got '{taskData['id']}'"

    # Marca la tarea como completada y validar que el campo "completada" se actualice correctamente
    response = client.put(f"{URL}/tasks/completar/{taskID}")
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()  
    assert data["completada"] is True, f"Tarea completada 'True', got '{data['completada']}'"

def test_obtener_tareas_caducadas():
    # Is done: Implementar test para obtener tareas caducadas"
    clear_db()  # Crear tareas con deadlines pasados y futuros
    past_date = date.today() - timedelta(days=1)
    future_date = date.today() + timedelta(days=1)

    createTask({"titulo": "Caducada","contenido": "Pasado", "deadline": past_date.isoformat()})
    createTask({"titulo": "Vigente", "contenido": "Futuro", "deadline": future_date.isoformat()})

    # Obtener la lista de tareas caducadas y validar que solo se devuelvan las tareas con deadlines pasados
    response = client.get(f"{URL}/tasks/caducadas")
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    assert len(data) == 1, f"Expected 1 caducada task, got {len(data)}"
    assert data[0]["titulo"] == "Caducada", f"Expected caducada task title 'Caducada', got '{data[0]['titulo']}'"

def test_datos_incorrectos():
    # is done: Implementar test con datos incorrectos que debe devolver 400
    clear_db()
    response = client.post(f"{URL}/tasks/", json={"titulo": "", "contenido": "", "deadline": "invalid-date"})
    assert response.status_code == 422

def test_datos_incorrectos_id():
    # is done: Implementar test para obtener una tarea con ID inexistente que debe devolver 404
    response = client.get(f"{URL}/tasks/999")
    assert response.status_code == 404

def test_borrar_tarea():
    clear_db()
    payload = {
        "titulo": "Prueba borrar",
        "contenido": "Contenido borrar",
        "deadline": str(date.today() + timedelta(days=2))
    }
    data, payload = createTask(payload)
    taskID = data.get("id")
   
    response = client.delete(f"{URL}/tasks/{taskID}")
    assert response.status_code == 204
    
    response = client.get(f"{URL}/tasks/{taskID}")
    assert response.status_code == 404

if __name__ == "__main__":
    tests = [
        test_crear_tarea,
        test_actualizar_tarea,
        test_obtener_tarea,
        test_marcar_completada,
        test_borrar_tarea,
        test_obtener_tareas_caducadas,
        test_datos_incorrectos,
        test_datos_incorrectos_id,
    ]    

    print("*" * 50)
    print("*   Ejecutando tests...")
    print("*" * 50)
    
    errors = 0
    for test in tests:
        try:
            r = test()
            print(f"[Test OK] > {test.__name__} {r} ")
        except AssertionError as e:
            errors += 1
            print(f"[Error  ] > {test.__name__} :\n Descripción: {e}")

    # Llamar a las funciones de test y validar resultados
    print(1 * "\n")
    print("Tests completados:")
    if errors > 0:
        print(f"Se encontraron {errors} errores en los tests.")
    else:
        print("Todos los tests pasaron correctamente.")
