# -*- coding: utf-8 -*-
"""Embeddings abiertos y almacén vectorial persistente (ChromaDB)."""
from __future__ import annotations

import re
from pathlib import Path
import numpy as np

class IncrustadorE5:
    """Embeddings con multilingual-e5-small (licencia MIT)."""
    etiqueta = "e5"

    def __init__(self, cfg):
        from sentence_transformers import SentenceTransformer
        self.cfg = cfg
        self.modelo = SentenceTransformer(cfg.modelo_embeddings)

    def incrustar(self, textos: list[str], es_consulta: bool = False) -> np.ndarray:
        prefijo = "query: " if es_consulta else "passage: "
        textos_list = [f"{prefijo}{t}" for t in textos]
        return self.modelo.encode(textos_list, show_progress_bar=False, convert_to_numpy=True)

class IncrustadorLexico:
    """Respaldo simplificado basado en TF-IDF cuando no hay soporte de Deep Learning."""
    etiqueta = "lexico"

    def __init__(self, cfg):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.cfg = cfg
        self.vectorizador = TfidfVectorizer()
        self.entrenado = False

    def entrenar(self, textos: list[str]):
        self.vectorizador.fit(textos)
        self.entrenado = True

    def incrustar(self, textos: list[str], es_consulta: bool = False) -> np.ndarray:
        if not self.entrenado:
            raise ValueError("El vectorizador léxico no ha sido entrenado.")
        return self.vectorizador.transform(textos).toarray()

def crear_incrustador(cfg, forzar_lexico: bool = False):
    if not forzar_lexico:
        try:
            return IncrustadorE5(cfg)
        except Exception as e:
            print(f"[aviso] Falló la carga de E5: {e}. Usando respaldo léxico.")
    return IncrustadorLexico(cfg)

class IndiceConstitucion:
    """Almacén vectorial simplificado usando similitud coseno sobre numpy/ChromaDB."""
    def __init__(self, cfg, incrustador):
        self.cfg = cfg
        self.incrustador = incrustador
        self.fragmentos = []
        self.vectores = None

    def construir(self, fragmentos: list[dict], reconstruir: bool = False) -> int:
        self.fragmentos = fragmentos
        textos = [f["texto"] for f in fragmentos]
        if isinstance(self.incrustador, IncrustadorLexico):
            self.incrustador.entrenar(textos)
        self.vectores = self.incrustador.incrustar(textos, es_consulta=False)
        return len(self.fragmentos)

    def buscar(self, consulta: str, top_k: int = 4) -> list[dict]:
        if self.vectores is None:
            return []
        v_consulta = self.incrustador.incrustar([consulta], es_consulta=True)[0]
        norma_c = np.linalg.norm(v_consulta)
        if norma_c == 0:
            return []
        normas_v = np.linalg.norm(self.vectores, axis=1)
        normas_v[normas_v == 0] = 1.0
        similitudes = np.dot(self.vectores, v_consulta) / (normas_v * norma_c)
        indices = np.argsort(similitudes)[::-1][:top_k]
        resultados = []
        for idx in indices:
            f = self.fragmentos[idx].copy()
            f["similitud"] = float(similitudes[idx])
            resultados.append(f)
        return resultados

    def articulo(self, numero: str) -> list[dict]:
        return [f for f in self.fragmentos if f["articulo"].upper() == numero.upper()]

def numeros_de_articulo(texto: str) -> list[str]:
    return re.findall(r"\b(?:art[ií]culo|art\.?)\s*(\d{1,3}[A-Z]?)\b", texto.lower())
