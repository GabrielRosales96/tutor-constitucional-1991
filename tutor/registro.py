# -*- coding: utf-8 -*-
"""Registro técnico (logging) sin datos personales: solo categoría, fecha, latencia y número de fragmentos."""
from __future__ import annotations  # anotaciones modernas

import json  # formato JSON Lines
from datetime import datetime, timezone  # marca de tiempo en UTC
from pathlib import Path  # rutas de archivos

# Únicos campos permitidos: cualquier otro se rechaza para garantizar privacidad por diseño (RNF-02)
CAMPOS_PERMITIDOS = ("fecha", "categoria", "latencia_ms", "n_fragmentos")  # continuación de la instrucción anterior
# Categorías válidas de una interacción
CATEGORIAS = ("normal", "riesgo", "saludo", "aclaracion", "sin_evidencia", "fuera_de_alcance")  # continuación de la instrucción anterior


class Registro:  # clase Registro: Escribe una línea JSON por interacción, sin guardar el texto del…
    """Escribe una línea JSON por interacción, sin guardar el texto del estudiante ni de las respuestas."""

    def __init__(self, ruta: Path):  # función __init__
        self.ruta = ruta  # archivo de destino
        self.ruta.parent.mkdir(parents=True, exist_ok=True)  # crea la carpeta si no existe

    def registrar(self, categoria: str, latencia_ms: float, n_fragmentos: int) -> dict:  # función registrar: Guarda la interacción y devuelve el registro escrito.
        """Guarda la interacción y devuelve el registro escrito."""
        if categoria not in CATEGORIAS:  # valida la categoría
            raise ValueError(f"Categoría no permitida: {categoria}")  # evita registrar datos inesperados
        entrada = {  # registro con los cuatro campos permitidos
            "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),  # fecha y hora UTC
            "categoria": categoria,  # tipo de interacción
            "latencia_ms": round(float(latencia_ms), 1),  # tiempo total de respuesta
            "n_fragmentos": int(n_fragmentos),  # fragmentos usados como evidencia
        }  # cierre de la estructura
        assert tuple(entrada) == CAMPOS_PERMITIDOS  # comprobación de privacidad por diseño
        with self.ruta.open("a", encoding="utf-8") as f:  # abre el archivo en modo agregar
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")  # escribe una línea JSON
        return entrada  # devuelve lo escrito

    def leer(self):  # función leer: Carga el registro como DataFrame de pandas para analizarlo.
        """Carga el registro como DataFrame de pandas para analizarlo."""
        import pandas as pd  # biblioteca de análisis de datos

        if not self.ruta.exists():  # si aún no hay registros
            return pd.DataFrame(columns=list(CAMPOS_PERMITIDOS))  # tabla vacía con las columnas esperadas
        return pd.read_json(self.ruta, lines=True)  # lee el JSON Lines
