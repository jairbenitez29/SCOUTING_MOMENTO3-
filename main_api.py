"""Servicio de inferencia: uvicorn main_api:app --reload"""
from functools import lru_cache
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

RUTA=Path(__file__).resolve().parent/'models/modelo_scouting_rf.joblib'
app=FastAPI(title='Scouting Deportivo - Random Forest',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:8000','http://127.0.0.1:8000','http://localhost:5500','http://127.0.0.1:5500'],allow_methods=['GET','POST'],allow_headers=['*'])

@lru_cache(maxsize=1)
def cargar_modelo():
    if not RUTA.exists():
        raise HTTPException(503,'Modelo no encontrado: ejecuta exportar_modelo.py primero')
    return joblib.load(RUTA) # Solo cargar archivos locales generados por una fuente confiable.

class Jugador(BaseModel):
    edad: int = Field(ge=15,le=65)
    estatura_cm: float | None = Field(default=None,ge=130,le=230)
    posicion: str = Field(min_length=2,max_length=80)

@app.get('/health')
def health():
    return {'estado':'ok','modelo_disponible':RUTA.exists()}

@app.get('/opciones')
def opciones():
    paquete=cargar_modelo()
    return {'posiciones':paquete['posiciones'],'fecha_referencia':paquete['fecha_referencia'],'umbral_eur':paquete['umbral_eur']}

@app.post('/predict')
def predict(jugador:Jugador):
    paquete=cargar_modelo()
    if jugador.posicion not in paquete['posiciones']:
        raise HTTPException(422,detail={'mensaje':'Posición no reconocida','posiciones_validas':paquete['posiciones']})
    tabla=pd.DataFrame([jugador.model_dump()])
    prob=float(paquete['pipeline'].predict_proba(tabla)[0,1]);pred=int(paquete['pipeline'].predict(tabla)[0])
    return {'clasificacion':'Élite' if pred else 'Estándar','es_elite':bool(pred),
       'probabilidad_elite':round(prob*100,2),'probabilidad_estandar':round((1-prob)*100,2),
       'umbral_valor_mercado_eur':paquete['umbral_eur'],
       'advertencia':'Estimación estadística, no una valoración comercial ni decisión automática de fichaje.'}

from fastapi.responses import FileResponse

@app.get('/',include_in_schema=False)
def pagina():
    return FileResponse(Path(__file__).resolve().parent/'index.html')
