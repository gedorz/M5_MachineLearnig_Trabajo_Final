from endpoints.endpoints import init_fastapi, router
from fastapi import FastAPI

import logging

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from endpoints.endpoints import init_fastapi, router
from DataBaseManagement.dbConectionPostgres import init_db

# IS done: Modifica la configuración de logging para que los mensajes de error de validación se registren con un nivel de advertencia (warning) en lugar de error (error). Esto permitirá que los errores de validación se destaquen sin interrumpir el flujo normal del programa.
# define la fecha y hora en el formato deseado, por ejemplo: "2024-06-01 12:00:00"
# y el nombre del logger, por ejemplo: "api.main"
# mas mensaje de error de validación, por ejemplo: "event=request_validation_error errors=%s", exc.errors() para mostrar los detalles del error de validación en el log.
# para la trazabilidad
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# se crea un objeto logger para registrar los mensajes de log en el módulo "api.main". Esto permite que los mensajes de log se identifiquen claramente como provenientes de este módulo específico.
# y generar la trazabilidad de los errores de validación en el módulo "api.main" para facilitar la identificación y solución de problemas relacionados con la validación de solicitudes en la API.
logger = logging.getLogger("api.main")

# Se crea una instancia de la aplicación FastAPI 
# utilizando la función init_fastapi() y se incluye 
# el router definido en endpoints.endpoints. 
# Esto configura la aplicación para manejar las rutas y 
# funcionalidades definidas en el router.
app = init_fastapi()
app.include_router(router)

# Asguro que la base de datos esté inicializada al iniciar la aplicación,
# llamando a la función init_db() en el evento de inicio (startup) de FastAPI.
@app.on_event("startup")
def on_startup_init_db() -> None:
	logger.info("event=startup_init_db")
	init_db()

# IS done: Agrega un manejador de excepciones personalizado para capturar 
# los errores de validación de solicitudes (RequestValidationError) y
# registrar los detalles del error utilizando el logger configurado. 
# Esto permitirá que los errores de validación se registren con un 
# nivel de advertencia (warning) en lugar de error (error), 
# lo que facilitará la identificación y solución de problemas 
# relacionados con la validación de solicitudes en la API.
# para la trazabilidad de los errores de validación en el módulo "api.main" y facilitar la identificación y solución de problemas relacionados con la validación de solicitudes en la API. 
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_request, exc: RequestValidationError):
	logger.warning("event=request_validation_error errors=%s", exc.errors())
	return JSONResponse(
		status_code=422,
		content={
			"detail": "Bad Request on json body",
			"errors": exc.errors(),
		},
	)

# IS done: Agrega un endpoint adicional para exponer el esquema OpenAPI 
# de la API en la ruta "/apim5/openapi.json". 
# Esto permitirá que los clientes y herramientas de desarrollo 
# puedan acceder fácilmente a la documentación de la API y 
# al esquema de validación de solicitudes.
@app.get("/apim5/openapi.json", include_in_schema=False)
def openapi_proxy_alias():
	return app.openapi()



