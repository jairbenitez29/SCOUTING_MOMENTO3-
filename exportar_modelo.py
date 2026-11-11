"""Uso: python exportar_modelo.py --origen csv  |  --origen mysql"""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, ConfusionMatrixDisplay, roc_auc_score, RocCurveDisplay)
from src.datos import obtener_datos, FECHA_REFERENCIA
from src.preprocesamiento import PreparadorScouting

ROOT = Path(__file__).resolve().parent


def evaluar(nombre, modelo, X_train, X_test, y_train, y_test):
    pred = modelo.predict(X_test)
    prob = modelo.predict_proba(X_test)[:, 1]
    return dict(modelo=nombre, accuracy_train=round(accuracy_score(y_train,modelo.predict(X_train)),4),
      accuracy_test=round(accuracy_score(y_test,pred),4),
      precision=round(precision_score(y_test,pred,zero_division=0),4),
      recall=round(recall_score(y_test,pred,zero_division=0),4),
      f1=round(f1_score(y_test,pred,zero_division=0),4),
      auc=round(roc_auc_score(y_test,prob),4), confusion=confusion_matrix(y_test,pred).tolist())


def main(origen):
    print('[1/6] Leyendo datos:',origen,flush=True)
    df=obtener_datos(origen)
    for col in ['edad','estatura_cm','valor_mercado']:df[col]=pd.to_numeric(df[col],errors='coerce')
    df=df.dropna(subset=['valor_mercado','edad']).copy()
    # Definición del target del estudio: Q3 sobre universo observado (ver limitaciones del informe).
    umbral=float(df['valor_mercado'].quantile(.75))
    y=(df['valor_mercado']>=umbral).astype(int)
    X=df[['edad','estatura_cm','posicion']]
    X_train,X_test,y_train,y_test=train_test_split(X,y,stratify=y,test_size=.2,random_state=42)
    print('[2/6] Datos:',len(df),'Umbral EUR:',umbral,'Entrenamiento:',len(X_train),'Prueba:',len(X_test),flush=True)
    cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=42)
    base=Pipeline([('prep',PreparadorScouting()),('modelo',DecisionTreeClassifier(random_state=42))])
    podado=Pipeline([('prep',PreparadorScouting()),('modelo',DecisionTreeClassifier(max_depth=3,min_samples_leaf=10,random_state=42))])
    base.fit(X_train,y_train); podado.fit(X_train,y_train)
    print('[3/6] Árboles de referencia entrenados',flush=True)
    rf=Pipeline([('prep',PreparadorScouting()),('modelo',RandomForestClassifier(random_state=42,n_jobs=-1))])
    parametros={
      'modelo__n_estimators':[80,160],
      'modelo__max_depth':[5,10,None],
      'modelo__min_samples_leaf':[5,15],
      'modelo__class_weight':['balanced', 'balanced_subsample']
    }
    busqueda=GridSearchCV(rf,parametros,cv=cv,scoring='f1',n_jobs=2,verbose=0,refit=True)
    print('[4/6] Optimización Random Forest: 24 configuraciones x 3 pliegues',flush=True)
    busqueda.fit(X_train,y_train)
    final=busqueda.best_estimator_
    resultados=[evaluar('Árbol libre',base,X_train,X_test,y_train,y_test),
      evaluar('Árbol podado',podado,X_train,X_test,y_train,y_test),
      evaluar('Random Forest',final,X_train,X_test,y_train,y_test)]
    (ROOT/'models').mkdir(exist_ok=True); (ROOT/'resultados').mkdir(exist_ok=True)
    paquete={'pipeline':final,'umbral_eur':umbral,'fecha_referencia':FECHA_REFERENCIA,
       'columnas_entrada':['edad','estatura_cm','posicion'],
       'posiciones':final.named_steps['prep'].posiciones_,
       'nota':'Probabilidad del modelo de pertenecer al grupo top Q3; no equivale a probabilidad de éxito deportivo.'}
    joblib.dump(paquete,ROOT/'models/modelo_scouting_rf.joblib',compress=3)
    reporte={'origen':origen,'fecha_referencia':FECHA_REFERENCIA,'filas_validas':len(df),
       'train':len(X_train),'test':len(X_test),'umbral_eur':umbral,'elite':int(y.sum()),
       'estandar':int((1-y).sum()), 'nulos_estatura':int(df['estatura_cm'].isna().sum()),
       'mejores_hiperparametros':busqueda.best_params_,
       'mejor_f1_cv':round(float(busqueda.best_score_),4),'resultados':resultados}
    (ROOT/'resultados/metricas.json').write_text(json.dumps(reporte,indent=2,ensure_ascii=False),encoding='utf8')
    print('[5/6] Métricas:',json.dumps(reporte['resultados'],ensure_ascii=False),flush=True)
    # Comparación Train/Test
    fig,ax=plt.subplots(figsize=(9,5)); indices=np.arange(3)
    ax.bar(indices-.2,[r['accuracy_train'] for r in resultados],.4,label='Train')
    ax.bar(indices+.2,[r['accuracy_test'] for r in resultados],.4,label='Test')
    ax.set_xticks(indices,[r['modelo'] for r in resultados]);ax.set_ylim(0,1)
    ax.set_ylabel('Accuracy');ax.set_title('Diagnóstico de sobreajuste y ensamble');ax.legend()
    fig.tight_layout();fig.savefig(ROOT/'resultados/accuracy_train_test.png',dpi=170);plt.close(fig)
    # ROC comparativa
    fig,ax=plt.subplots(figsize=(7,6))
    for nombre,mod in [('Árbol libre',base),('Árbol podado',podado),('Random Forest',final)]:
        RocCurveDisplay.from_predictions(y_test,mod.predict_proba(X_test)[:,1],name=nombre,ax=ax)
    ax.plot([0,1],[0,1],linestyle='--',color='grey',label='Azar');ax.set_title('Curvas ROC - conjunto de prueba')
    fig.tight_layout();fig.savefig(ROOT/'resultados/roc_auc.png',dpi=170);plt.close(fig)
    # Importancias agrupadas en variables originales: edad, estatura, posición
    imp=final.named_steps['modelo'].feature_importances_;cols=final.named_steps['prep'].columnas_
    agrupadas={'Edad':0.,'Estatura':0.,'Posición':0.}
    for c,v in zip(cols,imp):
        clave='Edad' if c=='edad' else ('Estatura' if c=='estatura_cm' else 'Posición')
        agrupadas[clave]+=float(v)
    reporte['importancia_variables']=agrupadas
    (ROOT/'resultados/metricas.json').write_text(json.dumps(reporte,indent=2,ensure_ascii=False),encoding='utf8')
    fig,ax=plt.subplots(figsize=(7,4));ax.bar(agrupadas.keys(),agrupadas.values());ax.set_ylim(0,1)
    ax.set_ylabel('Importancia Gini agregada');ax.set_title('Importancia por variable original')
    fig.tight_layout();fig.savefig(ROOT/'resultados/importancia_variables.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,r in zip(axs,[resultados[0],resultados[-1]]):
        ConfusionMatrixDisplay(np.array(r['confusion']),display_labels=['Estándar','Élite']).plot(ax=ax,cmap='Blues',colorbar=False)
        ax.set_title(r['modelo'])
    fig.tight_layout();fig.savefig(ROOT/'resultados/matrices_confusion.png',dpi=170);plt.close(fig)
    print('[6/6] Modelo exportado y 4 gráficas creadas',flush=True)
    print('Mejores parámetros:',busqueda.best_params_,'| F1 prueba:',resultados[-1]['f1'],flush=True)
    return reporte

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--origen',choices=['mysql','csv'],default='mysql')
    a=parser.parse_args();main(a.origen)
