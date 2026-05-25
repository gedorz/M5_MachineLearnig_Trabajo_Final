import io
import json
import logging

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter()
logger = logging.getLogger("api.endpointscargadatos")


@router.post("/cargadatoscsv")
async def cargadatoscsv(file: UploadFile = File(...)):
	logger.info("event=load_csv_start filename=%s", file.filename)

	if not file.filename or not file.filename.lower().endswith(".csv"):
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="El archivo debe tener extensión .csv",
		)

	try:
		contenido = await file.read()
		df_reservas = pd.read_csv(io.BytesIO(contenido))
		head_data = json.loads(
			df_reservas.head().replace([float("inf"), float("-inf")], None).to_json(orient="records")
		)
		tail_data = json.loads(
			df_reservas.tail().replace([float("inf"), float("-inf")], None).to_json(orient="records")
		)

		info_buffer = io.StringIO()
		df_reservas.info(buf=info_buffer)

		logger.info(
			"event=load_csv_success filename=%s rows=%s cols=%s",
			file.filename,
			len(df_reservas),
			len(df_reservas.columns),
		)

		return {
			"filename": file.filename,
			"head": head_data,
			"tail": tail_data,
			"columns": df_reservas.columns.tolist(),
			"info": info_buffer.getvalue(),
		}
	except Exception as exc:
		logger.exception("event=load_csv_error filename=%s", file.filename)
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"No se pudo procesar el CSV: {str(exc)}",
		)
