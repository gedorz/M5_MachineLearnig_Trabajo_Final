export type SubmenuPageContent = {
  intro: string;
  checklist: string[];
};

export const submenuPageContent: Record<string, SubmenuPageContent> = {
  "importar-csv-excel": {
    intro: "Carga archivos fuente y valida su estructura antes de ejecutar cualquier entrenamiento.",
    checklist: [
      "Verificar cabeceras y tipos de columna.",
      "Detectar nulos y valores atipicos.",
      "Registrar fecha y fuente del archivo importado."
    ]
  },
  "conectar-data-lake": {
    intro: "Conecta el flujo de datos externo para consumir lotes historicos de forma controlada.",
    checklist: [
      "Configurar credenciales de acceso.",
      "Definir ruta del dataset y version.",
      "Confirmar politica de actualizacion incremental."
    ]
  },
  "previsualizar-lote": {
    intro: "Analiza una muestra rapida para validar calidad de datos antes del preprocesamiento.",
    checklist: [
      "Revisar distribucion de variables clave.",
      "Inspeccionar balance de clases objetivo.",
      "Detectar columnas con alta cardinalidad."
    ]
  },
  "preprocesamiento-balanceo": {
    intro: "Normaliza y transforma el dataset para dejarlo listo para el pipeline de modelado.",
    checklist: [
      "Aplicar imputacion y codificacion.",
      "Escalar variables numericas cuando corresponda.",
      "Seleccionar estrategia de balanceo de clases."
    ]
  },
  "definir-features": {
    intro: "Determina las variables predictoras y la variable objetivo para entrenar modelos robustos.",
    checklist: [
      "Excluir columnas con fuga de informacion.",
      "Crear variables derivadas relevantes.",
      "Documentar justificacion de cada feature."
    ]
  },
  "lanzar-automl": {
    intro: "Ejecuta una corrida comparativa para probar familias de modelos en paralelo.",
    checklist: [
      "Definir presupuesto de tiempo de entrenamiento.",
      "Configurar validacion cruzada.",
      "Guardar artefactos y resultados por experimento."
    ]
  },
  "comparar-metricas": {
    intro: "Compara resultados de cada modelo con una metrica principal y metricas complementarias.",
    checklist: [
      "Ordenar modelos por metrica objetivo.",
      "Revisar precision y recall por clase.",
      "Validar estabilidad entre folds."
    ]
  },
  "matriz-confusion-roc": {
    intro: "Visualiza errores de clasificacion y capacidad de discriminacion para cada modelo.",
    checklist: [
      "Inspeccionar falsos positivos y falsos negativos.",
      "Trazar curva ROC y calcular AUC.",
      "Comparar umbrales de decision alternativos."
    ]
  },
  "seleccion-mejor-modelo": {
    intro: "Selecciona el modelo final con criterio metodologico, rendimiento y costo operativo.",
    checklist: [
      "Definir criterio de desempate entre modelos.",
      "Validar generalizacion en datos no vistos.",
      "Registrar version final para despliegue."
    ]
  },
  "prediccion-linea": {
    intro: "Evalua una reserva individual y devuelve su probabilidad de cancelacion en tiempo real.",
    checklist: [
      "Capturar entrada del usuario.",
      "Ejecutar inferencia con el modelo publicado.",
      "Mostrar probabilidad y clase final."
    ]
  },
  "prediccion-masiva": {
    intro: "Procesa lotes completos de reservas para generar predicciones de manera automatizada.",
    checklist: [
      "Subir archivo de inferencia masiva.",
      "Procesar lote en segundo plano.",
      "Entregar resumen de resultados y estado."
    ]
  },
  "tabla-comparativa": {
    intro: "Consolida las metricas clave para comparar modelos en una sola vista ejecutiva.",
    checklist: [
      "Incluir Accuracy, F1 y ROC-AUC.",
      "Mostrar fecha de entrenamiento por modelo.",
      "Resaltar el mejor modelo segun criterio principal."
    ]
  },
  "modelos-obligatorios": {
    intro: "Verifica el cumplimiento de los algoritmos requeridos en el trabajo final.",
    checklist: [
      "Regresion logistica entrenada y evaluada.",
      "Arbol y random forest comparados.",
      "Boosting y red neuronal incluidos."
    ]
  },
  "graficas-rendimiento": {
    intro: "Publica visualizaciones para entender el comportamiento y estabilidad de los modelos.",
    checklist: [
      "Curvas ROC comparadas.",
      "Importancia de variables por modelo.",
      "Tendencia temporal de metricas."
    ]
  },
  "prediccion-7-15-30": {
    intro: "Consulta riesgo de cancelacion para diferentes horizontes de prediccion temporal.",
    checklist: [
      "Calcular ventana a 7 dias.",
      "Calcular ventana a 15 dias.",
      "Calcular ventana a 30 dias."
    ]
  },
  "exportar-resultados": {
    intro: "Descarga resultados de prediccion en formatos listos para analisis y auditoria.",
    checklist: [
      "Exportar reporte en CSV.",
      "Exportar respuesta en JSON.",
      "Incluir metadatos de version del modelo."
    ]
  }
};
