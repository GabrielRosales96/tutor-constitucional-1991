# -*- coding: utf-8 -*-
"""Memoria de corto plazo: ventana deslizante de los últimos intercambios de la sesión."""
from __future__ import annotations  # anotaciones modernas

import re  # detección de referencias a lo dicho antes
from collections import deque  # cola con tamaño máximo

from .seguridad import normalizar  # normalización de texto sin tildes

# Palabras que suelen referirse a algo mencionado antes («esa acción», «y eso»)
ANAFORAS = re.compile(r"\b(esa|ese|esto|eso|esta|este|esas|esos|ella|ello|anterior|mismo|misma|tambien)\b|^y\b|^pero\b|^entonces\b")  # continuación de la instrucción anterior


class MemoriaCorta:  # clase MemoriaCorta: Guarda como máximo N pares (pregunta, respuesta) y expone el…
    """Guarda como máximo N pares (pregunta, respuesta) y expone el historial como mensajes de chat."""

    def __init__(self, intercambios: int = 4, max_caracteres_respuesta: int = 500):  # función __init__
        self.turnos = deque(maxlen=intercambios)  # al llenarse, descarta automáticamente el más antiguo
        self.max_caracteres_respuesta = max_caracteres_respuesta  # límite de tamaño por respuesta guardada

    def agregar(self, pregunta: str, respuesta: str) -> None:  # función agregar: Registra un intercambio; la respuesta se recorta para controlar la…
        """Registra un intercambio; la respuesta se recorta para controlar la longitud del contexto."""
        corta = respuesta if len(respuesta) <= self.max_caracteres_respuesta else respuesta[: self.max_caracteres_respuesta].rsplit(" ", 1)[0] + "…"  # recorte
        self.turnos.append((pregunta, corta))  # añade el par

    def como_mensajes(self) -> list[dict]:  # función como_mensajes: Convierte el historial al formato de mensajes de un modelo de chat.
        """Convierte el historial al formato de mensajes de un modelo de chat."""
        mensajes = []  # lista de mensajes
        for pregunta, respuesta in self.turnos:  # recorre del más antiguo al más reciente
            mensajes.append({"role": "user", "content": pregunta})  # turno del estudiante
            mensajes.append({"role": "assistant", "content": respuesta})  # turno del tutor
        return mensajes  # historial completo

    def ultima_pregunta(self) -> str:  # función ultima_pregunta: Devuelve la pregunta más reciente, o texto vacío si no hay historial.
        """Devuelve la pregunta más reciente, o texto vacío si no hay historial."""
        return self.turnos[-1][0] if self.turnos else ""  # última pregunta guardada

    def limpiar(self) -> None:  # función limpiar: Borra el historial (botón «nueva conversación»).
        """Borra el historial (botón «nueva conversación»)."""
        self.turnos.clear()  # vacía la cola

    def __len__(self) -> int:  # función __len__: Número de intercambios guardados.
        """Número de intercambios guardados."""
        return len(self.turnos)  # tamaño actual


def consulta_para_recuperar(pregunta: str, memoria: MemoriaCorta) -> str:  # función consulta_para_recuperar: Si la pregunta depende de lo anterior («¿y qué requisitos tiene esa…
    """Si la pregunta depende de lo anterior («¿y qué requisitos tiene esa acción?»), le agrega la pregunta previa."""
    t = normalizar(pregunta)  # texto normalizado
    es_corta = len(t.split()) <= 12  # preguntas cortas suelen depender del contexto
    if memoria.ultima_pregunta() and es_corta and ANAFORAS.search(t):  # hay historial y señales de referencia
        return f"{memoria.ultima_pregunta()} {pregunta}"  # se combinan para recuperar mejor
    return pregunta  # en otro caso se usa la pregunta tal cual
