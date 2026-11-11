# Scouting Deportivo — Proyecto final de Electiva II

Sistema end-to-end: extracción MySQL/CSV → preparación → árboles vs. Random Forest → GridSearchCV → Joblib → API FastAPI → interfaz HTML/JS.

## Archivos clave
- `src/database/connection2.py`: conector MySQL (adaptación preservada del Momento 2)
- `src/datos.py`: lectura reproducible MySQL o CSV
- `src/preprocesamiento.py`: imputación por medianas agrupadas y One-Hot, ajustado solo con Train
- `exportar_modelo.py`: entrenamiento, grid, gráficas y serialización
- `models/modelo_scouting_rf.joblib`: modelo entrenado
- `main_api.py`: FastAPI, rutas `/health`, `/opciones`, `/predict`, `/docs`
- `index.html`: interfaz cliente
- `resultados/`: métricas y gráficos del experimento reproducible
- `informe/INFORME_FINAL.pdf`: informe ejecutivo de entrega
- `momento2_original/`: scripts e informe anteriores para trazabilidad

## Configuración
Copia `.env.example` a `.env` y cambia la conexión a MySQL únicamente si deseas usar ese origen. El CSV original está incluido en `data/players_transfermarkt.zip`. **No publiques tu `.env`**.

La guía detallada de ejecución y sustentación se entrega en un PDF separado, fuera del ZIP.

## Alcance y limitaciones
La etiqueta élite usa Q3 del valor de mercado en la muestra completa para definir el grupo del estudio; se fija fecha de referencia en 2026-10-07. Las medianas y categorías **se estiman con Train** mediante el pipeline; en CV se estiman nuevamente dentro de cada pliegue. El target Q3 global es una decisión de definición de la población, no una predicción operacional de valores futuros. AUC y probabilidades miden discriminación en este conjunto, no garantizan aptitud deportiva. El conjunto tiene solo tres variables originales y carece de estadísticas técnicas y contractuales. Cuando se regenere el modelo con MySQL, los números de métricas podrían variar si los registros difieren del CSV.

**Seguridad:** `joblib.load` solo debe cargar el archivo generado localmente, no archivos descargados de procedencia desconocida.
