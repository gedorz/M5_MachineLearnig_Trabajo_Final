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
    source .\.venv\Scripts\activate.ps1   
```

### 2. Is done:  Instalar dependencias
    Mediante el archivo de  requirements.txt
    se realizar la inclusión de los requerimientos de la aplicación.
    Esto se realiza con el siguiente comando

```bash
    pip install -r requirements.txt


# Esquemas de Entrenamiento

df_calories_lite = pd.read_csv(PATH_DATASET_CALORIES_LITE)
# 1) Preparación de los datos para el modelo de regresión lineal
X  = df_calories_lite[["time"]]
y = df_calories_lite["calories"]
# Creación del modelo de regresión lineal
modelo = LinearRegression()
modelo.fit(X, y)

# Validaciones de datos
df_calories.isna().sum()   
df_calories.columns = df_calories.columns.str.lower()

# Coeficientes del modelo
# modelo.coef_, modelo.intercept_
coeficiente = modelo.coef_[0]
intercepto = modelo.intercept_

print(f"La fórmula de la regresión lineal es: y = {coeficiente:.4f} * x + {intercepto:.4f}")
print(f"O lo que es lo mismo: calories = {coeficiente:.4f} * time + {intercepto:.4f}")

minutos_entrenamiento = 30
calorias_estimadas = coeficiente * minutos_entrenamiento + intercepto
print(f"Calorías estimadas para {minutos_entrenamiento} minutos de entrenamiento: {calorias_estimadas:.2f} calorías")  
# Realizamos predicciones con el modelo
y_pred = modelo.predict(X)

---
# 2) Modelo y proyeccion
# Cargar datos de entrenamiento
df_calories = pd.read_csv(PATH_DATASET_CALORIES)

# Prepara un data set y para entrenar
# Preparación de los datos para el modelo de regresión lineal
variable_dependiente = "calorias"
X = df_calories.drop(columns=[variable_dependiente])
y = df_calories[variable_dependiente]

# Coeficientes del modelo y entrenamiento del modelo
modelo_regresion_multiple = LinearRegression()
modelo_regresion_multiple.fit(X, y)
coeficientes = modelo_regresion_multiple.coef_
intercepto = modelo_regresion_multiple.intercept_

for i, col in enumerate(X.columns):
    print(f"Coeficiente para {col}: {coeficientes[i]:.4f}")

# Evaluar el modelo
y_pred = modelo_boston.predict(X)
_, _, _, _ = calcular_metricas_evaluacion(y_pred, y)



# Evalucion del modelo en grado 2 para ajustar el modelo y evaluarlo
# 80% en entrenamiento y 20%de text
## Cargamos las variables independiente y dependiente
X = df_boston_rg_processado[["RM"]]
y = df_boston_rg_processado["MEDV"]

## Hacemos el train y  test haciendo split del conjunto de datos
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=45)

## Eleva a la 2 el set de entrenamiento y lo convierte en un array [x, x^2]
poly2 = PolynomialFeatures(degree=2, include_bias=False)

X_train_poly2 = poly2.fit_transform(X_train) 
X_test_poly2 = poly2.transform(X_test)

modelo_ajustado2 = LinearRegression()
modelo_ajustado2.fit(X_train_poly2, y_train)
y_pred_poly2 = modelo_ajustado2.predict(X_test_poly2)

# Calculamos las métricas de evaluación para el conjunto de prueba
_, _, _, _ = calcular_metricas_evaluacion(y_pred_poly2, y_test)


# Gracias de analisis
sns.pairplot(data=df_calories)
plot_matriz_correlacion(df_calories, "calorias")
plot_residuos(y_pred=y_pred, y_true=y)
plot_histograma_residuos(y_pred=y_pred, y_true=y)
plot_qq_plot_residuos(y_pred=y_pred, y_true=y)
sns.pairplot(data=df_boston_processado)
sns.pairplot(data=df_boston_processado[["CRIM", "MEDV"]])

---
# 3) Entrenamiento de modelo
X_train, X_test, y_train, y_test =  train_test_split(X, y, test_size=0.2, random_state=42)
variable_dependiente = "MEDV"
X = df_boston.drop(columns=[variable_dependiente])    
y = df_boston[variable_dependiente]
modelo_boston = LinearRegression()
modelo_boston.fit(X_train, y_train)


## 1. Creación de un modelo de regresión logística para clasificación

data_iris = load_iris(as_frame=True, return_X_y=False)
df_iris = data_iris['data']
lista_columnas_independientes = data_iris['data'].columns

target_column = 'target'
data_iris[target_column]
df_iris[target_column] = data_iris[target_column]
df_iris[target_column] = df_iris[target_column].astype(str)
df_iris.rename(columns=lambda x: x.replace(' (cm)', '').replace(' ', '_'), inplace=True)

## Analisis
df_iris.head()
df_iris.info()
df_iris.describe().transpose()
df_iris.describe(include='object').transpose()
df_iris[target_column].value_counts()   # Ver frecuencias absolutas de la columna 
df_iris[target_column].value_counts(normalize=True) # Ver frecuencias relativas

## Visualización de las variables numéricas con un gráfico de dispersión distinguiendo por la clase
sns.scatterplot(data=df_iris, x='sepal_length', y='sepal_width', hue=target_column, palette='viridis')
plt.title('Gráfico de dispersión de Sepal Length vs Sepal Width')
plt.xlabel('Sepal Length (cm)')
plt.ylabel('Sepal Width (cm)')
plt.grid(True)
plt.show()  

sns.pairplot(df_iris, hue=target_column, palette='viridis') 
plt.show()


## Creación del modelo LogisticRegression