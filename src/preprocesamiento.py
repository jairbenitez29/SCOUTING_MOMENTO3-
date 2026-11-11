"""Transformador entrenado exclusivamente con los datos de entrenamiento."""
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class PreparadorScouting(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        d = self._limpiar(X)
        self.mediana_por_posicion_ = d.groupby('posicion')['estatura_cm'].median().to_dict()
        self.mediana_global_ = float(d['estatura_cm'].median())
        self.mediana_edad_ = float(d['edad'].median())
        self.posiciones_ = sorted(d['posicion'].unique().tolist())
        self.columnas_ = ['edad','estatura_cm'] + [f'posicion_{p}' for p in self.posiciones_[1:]]
        return self

    def transform(self, X):
        d = self._limpiar(X)
        d['estatura_cm'] = d['estatura_cm'].fillna(d['posicion'].map(self.mediana_por_posicion_)).fillna(self.mediana_global_)
        d['edad'] = d['edad'].fillna(self.mediana_edad_)
        categorias = pd.Categorical(d['posicion'], categories=self.posiciones_)
        dummies = pd.get_dummies(categorias, prefix='posicion', dtype=int)
        dummies.index = d.index
        result = pd.concat([d[['edad','estatura_cm']],dummies],axis=1)
        return result.reindex(columns=self.columnas_,fill_value=0).astype(float)

    @staticmethod
    def _limpiar(X):
        d = X[['edad','estatura_cm','posicion']].copy()
        d['edad'] = pd.to_numeric(d['edad'],errors='coerce')
        d['estatura_cm'] = pd.to_numeric(d['estatura_cm'],errors='coerce')
        d['posicion'] = d['posicion'].fillna('Sin Posicion').replace('', 'Sin Posicion').astype(str)
        return d
