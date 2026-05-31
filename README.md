# Proyecto Final - Dataset Machine learnig y Deep Learning.

    - **Autor:** Diego Gil & German Dario Realpe
    - **Contacto:** pontia@sergiobenito.com
    - **Última actualización:** 24/05/2025

# Objetivo del la App de Machine learnig y Deep Learning M5.
    Diseñar e implementar un sistema automático que: 
    - Entrene, evalúe y compare distintos modelos de clasificación binaria. 
    - Seleccione el mejor modelo según una métrica principal, además de ofrecer una visión de otra secundarias. 
    - Automatice el flujo completo desde los datos hasta la inferencia. 
    - Se propone adjunto el dataset que se utilizará para llevar a cabo el proyecto.
    - Usar las funciones metodos y algoridmos planteadas en \notebooks\exploracion\TestPractica.ipynb

# Requisitos mínimos del sistema.

## 1 Problema de clasificación binaria 
    - Dataset real proporcionado en el apartado previo, con una variable objetivo binaria (0 o 1). 
    - Justificación del problema y del conjunto de datos

## 2 Modelos a implementar y comparar
    Se deben entrenar al menos los siguientes algoritmos, además de otros que puedan ser de interés: 
    - Regresión logística 
    - Árbol de decisión 
    - Random Forest 
    - Gradient Boosting (XGBoost, LightGBM o CatBoost) 
    - Red neuronal multicapa usando Keras de TensorFlow
## 3. Evaluación de modelos 
    - Utilizar al menos una de las siguientes métricas como principal: accuracy, precision, recall, F1-score, AUC-ROC. 
    - Se debe justificar el por qué se ha elegido dicha métrica como principal. 
    - Mostrar: matriz de confusión y curva ROC.

## 4. Automatización del flujo
    - Implementar un pipeline estructurado para: carga de datos, preprocesamiento, entrenamiento, evaluación, y selección del mejor modelo.

## 5 Crea una api con fasApi con el siguiente objetivo
    - Crear una API REST para exponer endpoints como /train, /predict o /evaluate.
    - Embeddings personalizados: Uso de Word2Vec, TF-IDF o embeddings categoricos para representar variables complejas.
    - Optimización de hiperparámetros: Aplicación de GridSearchCV o RandomizedSearchCV.
    - Balanceo de clases: Aplicacion de técnicas como: SMOTE, undersampling, class_weight.
    - Interpretabilidad: Uso de SHAP, LIME, o feature_importances_.
    - Interfaz visual: web UI simple.    
    - La app debe cargar la informacion del CSV y entrenar el modelo.
    - Se debe implementar 5 modelos distintos:(regresión logística, árbol, bosques aleatorios, boosting, red neuronal)
    - los modelos y los compare usando un enfoque metodológico coherente
    - Crear un endpoint para para optener una prediccion de cancelaciones para los siguientes 7,15 y 30 dias.
    - Acorde a los datos del proporcionados y al modelo entrenado, hace la predición si el usuario cancelará o no la reserva.
    - Separación de funcionalidades en distintos módulos o scripts (dconfig.py,data_loader.py  ,model_trainer.py,evaluator.py ,predictor.py).  
    - Script principal (trainer.py) que lanza todo el flujo de trabajo. 
    - Uso de funciones o clases reutilizables. 
    - Pipeline de Scikit-learn bien estructurado.

## 6 Resultados en el Frontend
    - Debe mostrar los resultados de los datos de las predicciones por cada modelo
    - Comparar modelos usando un conjunto de métricas comunes
    - Mostrar resultados en una tabla similar a la siguiente:
    - la pagina se debe llamar features_informance.html
    - debe mostrara las graficas de: 

| Modelo                  | Accuracy | F1-score  | ROC-AUC | 
| ------------------------| -------- | --------  | ------- |
| Logistic Regression     |   0,88   | 0,85      | 0,91    |
| Decision Tree           |   0,89   | 0,83      | 0,92    |
| Random Fores            |   0,91   | 0,89      | 0,94    |
| XGBoost                 |   0,92   | 0,90      | 0,95    |
| Deep Neural             |   0,89   | 0,87      | 0,93    |
| Network (Keras)         |          |           |         |



# 7 Explicacion de los datos a trabajar
Es ideal para aplicar modelos de clasificación binaria, donde el objetivo puede ser predecir si una reserva será cancelada

## Variables de datos en csv .\data\raw\dataset_practica_final.csv

| Nombre Variable                  | Descripción                                              |
| -------------------------------- | -------------------------------------------------------- |
| `hotel`                          | Tipo de hotel: City Hotel o Resort Hotel                 |
| `is_canceled`                    | Variable objetivo: 1 si fue cancelado, 0 si no           |
| `lead_time`                      | Días entre la reserva y la fecha de llegada              |
| `arrival_date_year`              | Año de llegada                                           |
| `arrival_date_month`             | Mes de llegada                                           |
| `arrival_date_week_number`       | Número de la semana del año                              |
| `arrival_date_day_of_month`      | Día del mes de llegada                                   |
| `stays_in_weekend_nights`        | Noches de fin de semana reservadas                       |
| `stays_in_week_nights`           | Noches entre semana reservadas                           |
| `adults`                         | Número de adultos                                        |
| `children`                       | Número de niños                                          |
| `babies`                         | Número de bebés                                          |
| `meal`                           | Tipo de comida reservada                                 |
| `country`                        | País de origen del cliente                               |
| `market_segment`                 | Canal de marketing (online, offline, grupos...)          |
| `distribution_channel`           | Canal de distribución (directo, TA/TO...)                |
| `is_repeated_guest`              | 1 si el cliente ha estado anteriormente                  |
| `previous_cancellations`         | Nº de cancelaciones anteriores                           |
| `previous_bookings_not_canceled` | Nº de reservas previas no canceladas                     |
| `reserved_room_type`             | Tipo de habitación reservada                             |
| `assigned_room_type`             | Tipo de habitación asignada                              |
| `booking_changes`                | Nº de cambios en la reserva                              |
| `deposit_type`                   | Tipo de depósito: No Deposit, Refundable, etc.           |
| `agent`                          | ID del agente (puede ser nulo)                           |
| `company`                        | ID de la empresa (puede ser nulo)                        |
| `days_in_waiting_list`           | Días en lista de espera                                  |
| `customer_type`                  | Tipo de cliente: Transient, Group, etc.                  |
| `adr`                            | Average Daily Rate (precio promedio por noche)           |
| `required_car_parking_spaces`    | Plazas de parking solicitadas                            |
| `total_of_special_requests`      | Nº de peticiones especiales                              |
| `reservation_status`             | Estado final de la reserva: Check-Out, Canceled, No-Show |
| `reservation_status_date`        | Fecha en que se actualizó el estado                      |

## 

# 8 Proyecto Final ML

Estructura para organizar un proyecto de Machine Learning de forma profesional y escalable.

---

## 8 Estructura del proyecto Dataset Machine learnig y Deep Learning

```bash
proyecto-final-ML/
│
├── .gitignore                              # Archivos que no se suben al repo (e.g., modelos, datos temporales)
│           
├── APP/                                   # Datos usados en el proyecto
│   ├── api-server/                          # Api de servicio para el proceso y entrenamiento de dato
│   └── dockerFiles_m5/                         # Constructor de los servidores de Fastapi base de datos de postgres y web UI
│   └── html_nginx/                          # Pagina web para cargar los datos activar el reentrenamiento y
│   │   └── web                              # mostrar los resultados de los modelos y predicciones. 
│   │       └── feature_importance.html  
│   │      
├── data/                                   # Datos usados en el proyecto
│   ├── raw/                                # Datos originales sin procesar
│   └── processed/                          # Datos tras limpieza y transformación (listos para modelar)
│           
├── docs/                                   # Documentación adicional
│           
├── models/                                 # Modelos entrenados (guardados con joblib o pickle)
│   ├── tests/                              # (Opcional) Modelos intermedios de prueba
│   │   ├── logistic_regression.pkl         # Ejemplo: Modelo de Regresión Logística
│   │   ├── tree.pkl                        # Ejemplo: Modelo de Árbol de Decisión
│   │   ├── random_forest.pkl               # Ejemplo: Modelo Random Forest
│   │   ├── xgboost.pkl                     # Ejemplo: Modelo XGBoost
│   │   ├── lightgbm.pkl                    # Ejemplo: Modelo LightGBM
│   │   └── neural_network.pkl              # Ejemplo: Red Neuronal
│   │
│   └── best_model.pkl                      # El mejor modelo seleccionado para producción
│
├── notebooks/                              # Todos los notebooks del proyecto
│   ├── exploracion/                        # Notebooks de pruebas, EDA inicial, prototipos
│   │   ├── eda_inicial.ipynb               # Ejemplo: análisis inicial del dataset
│   │   └── pruebas_modelos.ipynb           # Ejemplo: pruebas de diferentes modelos
│   │
│   └── finales/                            # Notebooks finales con resultados o presentación
│       ├── eda_final.ipynb                 # Ejemplo: EDA final del dataset
│       └── comparativa_modelos.ipynb       # Ejemplo: comparación final de modelos usada para scripts
│
├── outputs/                                # Gráficos, reportes y resultados generados
│   ├── confusion_matrix.png
│   └── feature_importance.html
│
├── src/                                    # Código fuente del proyecto
│   ├── __init__.py                         # Inicializador del paquete src
│   ├── config.py                           # Parámetros y configuración del proyecto
│   ├── data_loader.py                      # Funciones para cargar y transformar datos
│   ├── model_trainer.py                    # Clases o funciones para entrenar modelos
│   ├── evaluator.py                        # Métricas y visualización de resultados
│   └── predictor.py                        # Funciones para hacer predicciones con modelos entrenados
│           
├── requirements.txt                        # Dependencias del proyecto
│           
└── README.md                               # Documentación principal del proyecto con comandos de ejecución


.

---

## 9 Guía operativa de la subpágina: Definir features

Objetivo de la subpágina Definir features:
- Determinar las variables predictoras y la variable objetivo para entrenar modelos robustos.

Checklist operativo de Definir features:
- Excluir columnas con fuga de informacion.
- Crear variables derivadas relevantes.
- Documentar justificacion de cada feature.

### 9.1 Paso a paso para definicion de una Matriz de Featues(caracteristicas de los dato) 

1. Definir variable objetivo del problema (Cancelacion de las reservaciones)
- Variable objetivo: `is_canceled` (0 no cancela, 1 cancela) .
- Confirmar que todas las decisiones de features responden a este objetivo binario (Seleccion de la caracteristica con un check de usar o no usar).

2. Construir listado inicial de variables candidatas
- Incluir todas las columnas del dataset excepto la objetivo.
- Separar por tipo: Numericas, categoricas, fecha/tiempo e identificadores.

3. Excluir variables con fuga de informacion (data leakage)
- Regla: excluir cualquier variable que se conozca despues del momento de prediccion.
- Candidatas tipicas a revisar por fuga: `reservation_status`, `reservation_status_date` y variables operativas que cambian despues de la reserva.

4. Diseñar features derivadas con sentido de negocio (No se desarrolla en esta version)
- Proponer variables derivadas y su formula antes de entrenar modelos.
- Ejemplos:
    - `total_noches = stays_in_weekend_nights + stays_in_week_nights`
    - `total_huespedes = adults + children + babies`
    - `historial_cancelacion = previous_cancellations / (previous_cancellations + previous_bookings_not_canceled + 1)`
    - `temporada_alta` derivada de `arrival_date_month`

5. Definir transformaciones por tipo de variable
- Numericas: imputacion de nulos, escalado si aplica.
- Categoricas: codificacion (one-hot o equivalente), manejo de categorias raras.
- Fechas: extraccion de componentes utiles (mes, semana, estacionalidad).

6. Establecer criterios de inclusion/exclusion
- Cobertura de datos (porcentaje de nulos aceptable).
- Estabilidad temporal (que no dependa de informacion futura).
- Utilidad de negocio (explicable para el dominio hotelero).
- Utilidad tecnica (impacto esperado en F1 y ROC-AUC).

7. Documentar decisiones feature por feature
- Completar la matriz de justificacion y versionarla junto al experimento.
- Dejar evidencia de por que una variable se usa, se transforma o se excluye.

8. Definir salida de esta subpágina
- Lista final de features aprobadas.
- Lista de features excluidas por fuga o baja calidad.
- Diccionario de transformaciones por feature.
- Matriz de justificacion firmada para auditoria del experimento.

### 9.2 Matriz de justificacion de features (plantilla)

| feature | tipo | usar (si/no) | motivo de negocio | motivo tecnico | riesgo de fuga (alto/medio/bajo) | transformacion | notas |
|--------|------|--------------|-------------------|----------------|-----------------------------------|----------------|-------|
| lead_time | numerica | si | Anticipacion de reserva | Predictor fuerte en cancelacion | bajo | escalar/imputar | validar outliers |
| reservation_status | categorica | no | Estado final de la reserva | Introduce leakage directo | alto | excluir | se conoce al final |
| reservation_status_date | fecha | no | Fecha de estado final | Variable posterior al evento | alto | excluir | no disponible al predecir |
| country | categorica | si | Segmentacion geografica | puede requerir agrupacion | bajo | codificar/agrupar raras | revisar cardinalidad |
| total_noches | derivada numerica | si | Duracion de estancia | mejora señal de comportamiento | bajo | crear + escalar | suma de noches |

### 9.3 Criterio de cierre de la subpágina

Se considera completada la subpágina Definir features cuando exista evidencia de:
- Objetivo binario validado (`is_canceled`).
- Variables con fuga identificadas y excluidas.
- Features derivadas definidas con formula.
- Matriz de justificacion completa para todas las features finales.
- Entrega de lista final para la siguiente etapa de preprocesamiento y entrenamiento.