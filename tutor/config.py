# -*- coding: utf-8 -*-
"""Configuración centralizada del Tutor Constitucional 1991 (gestión de configuración)."""
from __future__ import annotations  # permite anotaciones de tipos modernas en cualquier versión de Python 3

import json  # se usa para leer el umbral de relevancia calibrado
import os  # se usa para leer variables de entorno (sin escribir secretos en el código)
from dataclasses import dataclass  # estructura de parámetros con valores por defecto
from pathlib import Path  # manejo de rutas independiente del sistema operativo

# Carpeta raíz del proyecto: se puede cambiar con la variable de entorno TUTOR_RAIZ
RAIZ = Path(os.getenv("TUTOR_RAIZ", str(Path(__file__).resolve().parent.parent)))  # continuación de la instrucción anterior
# Carpeta donde se guardan corpus, índice vectorial y registros técnicos
DATOS = RAIZ / "data"  # continuación de la instrucción anterior


@dataclass(frozen=True)  # objeto inmutable: evita cambios accidentales de configuración en ejecución
class Config:  # clase Config: Todos los parámetros ajustables del sistema, con valores por defecto…
    """Todos los parámetros ajustables del sistema, con valores por defecto razonables."""

    # ----- Fuentes del corpus (documentos públicos y no sensibles) -----
    url_pdf_dapre: str = "https://dapre.presidencia.gov.co/normativa/normativa/Constitucion-Politica-Colombia-1991.pdf"  # PDF oficial
    url_pagina_dapre: str = "https://dapre.presidencia.gov.co/normativa/constitucion-politica"  # página de referencia
    ruta_pdf: Path = DATOS / "Constitucion-Politica-Colombia-1991.pdf"  # copia local del PDF
    ruta_articulos: Path = DATOS / "articulos.jsonl"  # corpus ya segmentado por artículo
    articulos_esperados: int = 380  # número de artículos permanentes (sirve para validar la ingesta)

    # ----- Modelos abiertos (licencias: Apache-2.0 y MIT) -----
    modelo_embeddings: str = os.getenv("TUTOR_EMBEDDINGS", "intfloat/multilingual-e5-small")  # embeddings multilingües (MIT)
    modelo_llm_gpu: str = os.getenv("TUTOR_LLM_GPU", "Qwen/Qwen2.5-1.5B-Instruct")  # LLM cuando hay GPU (Apache-2.0)
    modelo_llm_cpu: str = os.getenv("TUTOR_LLM_CPU", "Qwen/Qwen2.5-0.5B-Instruct")  # LLM liviano sin GPU (Apache-2.0)

    # ----- Segmentación (chunking) -----
    max_caracteres_fragmento: int = 1200  # un artículo más largo se divide en partes de este tamaño máximo
    solape_caracteres: int = 150  # solapamiento entre partes para no cortar ideas

    # ----- Recuperación (RAG) -----
    top_k: int = 4  # número de fragmentos que se recuperan por consulta
    umbral_defecto: float = 0.80  # similitud mínima con embeddings E5 si no se ha calibrado (se recalibra en el Ejercicio 3)
    umbral_defecto_lexico: float = 0.20  # similitud mínima con el respaldo léxico si no se ha calibrado
    margen_fragmentos: float = 0.03  # se aceptan fragmentos hasta este margen por debajo del umbral
    max_caracteres_contexto: int = 4500  # tope de contexto inyectado al prompt (controla latencia)

    # ----- Memoria de corto plazo -----
    memoria_intercambios: int = 4  # RF-04: se recuerdan los últimos cuatro intercambios (pregunta + respuesta)
    max_caracteres_respuesta_memoria: int = 500  # las respuestas largas se recortan al guardarlas en memoria

    # ----- Generación -----
    temperatura: float = 0.2  # baja: respuestas más estables y menos inventadas
    top_p: float = 0.9  # muestreo por núcleo
    penalizacion_repeticion: float = 1.1  # reduce repeticiones del modelo pequeño
    max_tokens_nuevos_gpu: int = 450  # longitud máxima de respuesta con GPU
    max_tokens_nuevos_cpu: int = 260  # longitud máxima de respuesta sin GPU (latencia controlada)
    max_caracteres_pregunta: int = 600  # se recorta la pregunta del usuario a este tamaño

    # ----- Registro técnico (RF-07 / RNF-02): sin datos personales ni texto de la conversación -----
    ruta_registro: Path = DATOS / "logs" / "interacciones.jsonl"  # archivo JSON Lines del registro
    ruta_umbral: Path = DATOS / "umbral.json"  # umbral calibrado (lo escribe el cuaderno)
    ruta_chroma: Path = DATOS / "chroma_db"  # carpeta del almacén vectorial persistente
    nombre_coleccion: str = "constitucion_1991"  # nombre base de la colección en ChromaDB

    def umbral_para(self, etiqueta: str = "e5") -> float:  # función umbral_para: Devuelve el umbral calibrado para ese tipo de embedding («e5» o…
        """Devuelve el umbral calibrado para ese tipo de embedding («e5» o «lexico»); si no existe, el valor por defecto."""
        try:  # se intenta leer el archivo de calibración
            return float(json.loads(self.ruta_umbral.read_text(encoding="utf-8"))[etiqueta])  # valor guardado
        except (OSError, ValueError, KeyError):  # si no existe, está dañado o no incluye ese tipo
            return self.umbral_defecto if etiqueta == "e5" else self.umbral_defecto_lexico  # valor por defecto


# Líneas de ayuda que muestra el filtro de seguridad. VERIFICAR su vigencia antes de publicar el sistema.
LINEAS_AYUDA = (  # continuación de la instrucción anterior
    ("123", "Línea única de emergencias (Policía, ambulancia, bomberos)"),  # emergencias en todo el país
    ("141", "Línea de protección de niños, niñas y adolescentes (ICBF)"),  # protección de menores
    ("155", "Orientación a mujeres víctimas de violencia"),  # violencias basadas en género
    ("192, opción 4", "Línea nacional de salud mental"),  # apoyo emocional
)  # cierre de la estructura

# Frases de apoyo para estudiantes: se muestran como ejemplos de uso en la interfaz
PREGUNTAS_SUGERIDAS = (  # continuación de la instrucción anterior
    "¿Qué es la acción de tutela y para qué sirve?",  # HU-01
    "¿Cuál es la diferencia entre la rama legislativa y la rama ejecutiva?",  # HU-02
    "¿Qué dice el artículo 13 sobre la igualdad?",  # consulta con número de artículo
    "¿Qué derechos tienen los niños según la Constitución?",  # derechos de la niñez
)  # cierre de la estructura

# Aviso permanente que acompaña al sistema
AVISO_LEGAL = (  # continuación de la instrucción anterior
    "Tutor Constitucional 1991 es una herramienta exclusivamente educativa. "  # texto o patrón (continuación de la definición anterior)
    "Puede equivocarse: verifica siempre en el texto oficial. "  # texto o patrón (continuación de la definición anterior)
    "No ofrece asesoría jurídica individual, no emite conceptos vinculantes y no reemplaza "  # texto o patrón (continuación de la definición anterior)
    "a docentes, abogados, autoridades ni servicios de emergencia."  # texto o patrón (continuación de la definición anterior)
)  # cierre de la estructura
