from fastapi.testclient import TestClient
from main_api import app

def test_health():
    c=TestClient(app);r=c.get('/health');assert r.status_code==200 and r.json()['modelo_disponible']

def test_predict():
    c=TestClient(app);p=c.get('/opciones').json()['posiciones'][0]
    r=c.post('/predict',json={'edad':24,'estatura_cm':180,'posicion':p})
    assert r.status_code==200,r.text
    d=r.json();assert d['clasificacion'] in ['Élite','Estándar'] and 0<=d['probabilidad_elite']<=100

def test_invalid():
    c=TestClient(app);assert c.post('/predict',json={'edad':999,'estatura_cm':180,'posicion':'Attack'}).status_code==422
