# -*- coding: utf-8 -*-
"""Generación con Groq y respaldo extractivo para el Tutor Constitucional."""
from __future__ import annotations

from threading import Lock
import os


class GeneradorGroq:
    """Generación con un modelo de pesos abiertos mediante la API de Groq."""

    modo = "llm"

    def __init__(self, cfg, api_key: str):
        self.cfg = cfg
        self.nombre = "GPT-OSS 20B (Groq)"
        self.api_key = api_key
        self.modelo = os.getenv("TUTOR_LLM_GROQ", "openai/gpt-oss-20b")
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:
        """Envía los mensajes y el contexto RAG al endpoint compatible con OpenAI."""
        import requests

        respuesta = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.modelo,
                "messages": mensajes,
                "max_completion_tokens": max(900, self.cfg.max_tokens_nuevos_gpu),
            },
            timeout=90,
        )
        if not respuesta.ok:
            raise RuntimeError(
                f"Groq API ({respuesta.status_code}): {respuesta.text[:1000]}"
            )
        datos = respuesta.json()
        texto = datos["choices"][0]["message"].get("content") or ""
        if not texto.strip():
            raise RuntimeError("Groq devolvió una respuesta vacía.")
        return texto.strip()


class GeneradorLLM:
    """Carga Qwen2.5-0.5B-Instruct en GGUF Q4 para inferencia CPU de bajo consumo."""

    modo = "llm"

    def __init__(self, cfg):
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        self.cfg = cfg
        self.nombre = "Qwen2.5-0.5B-Instruct (GGUF Q4_K_M)"
        self.max_tokens = cfg.max_tokens_nuevos_cpu
        # Streamlit comparte este generador entre sesiones; llama.cpp no debe
        # recibir inferencias simultáneas sobre la misma instancia.
        self._lock = Lock()

        # El archivo cuantizado ocupa menos memoria que los pesos FP32 de Transformers.
        ruta_modelo = hf_hub_download(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        )
        self.modelo = Llama(
            model_path=ruta_modelo,
            n_ctx=4096,
            n_threads=2,
            n_batch=128,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:
        """Genera una respuesta usando la plantilla de chat incorporada en el GGUF."""
        # La instancia se comparte mediante st.cache_resource. Serializar las
        # llamadas evita corrupción de lotes/estado interno en inferencias
        # concurrentes de distintas sesiones de Streamlit.
        with self._lock:
            salida = self.modelo.create_chat_completion(
                messages=mensajes,
                max_tokens=self.max_tokens,
                temperature=self.cfg.temperatura,
                top_p=self.cfg.top_p,
                repeat_penalty=self.cfg.penalizacion_repeticion,
            )
        texto = salida["choices"][0]["message"].get("content", "")
        return texto.strip()


class GeneradorExtractivo:
    """Respaldo sin LLM: presenta los fragmentos constitucionales recuperados."""

    modo = "extractivo"
    nombre = "extractivo"

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:
        """Construye una respuesta literal a partir de los fragmentos más relevantes."""
        if not fragmentos:
            return "No encuentro ese tema en los fragmentos de la Constitución que consulté."
        # Recupera la pregunta original del último mensaje para ofrecer una
        # explicación determinista cuando el modo extractivo pueda hacerlo.
        pregunta = ""
        if mensajes:
            contenido = mensajes[-1].get("content", "")
            if "<<<" in contenido and ">>>" in contenido:
                pregunta = contenido.split("<<<", 1)[1].split(">>>", 1)[0].strip().lower()

        lineas = []
        numeros = {str(f["articulo"]) for f in fragmentos}
        if "13" in numeros and ("igualdad" in pregunta or "iguales" in pregunta):
            lineas.extend([
                "**En palabras sencillas:** el artículo 13 establece que todas las personas "
                "deben tener los mismos derechos, oportunidades y protección ante la ley. "
                "También ordena al Estado actuar para que esa igualdad sea efectiva y proteger "
                "a quienes se encuentren en situación de vulnerabilidad o discriminación.",
                "\n**Ejemplo:** en un colegio, este principio significa que los estudiantes "
                "deben recibir el mismo respeto y las mismas oportunidades, sin ser tratados "
                "de manera desfavorable por su origen, sexo, religión u otra condición.",
                "\n**Fundamento constitucional:**",
            ])
        else:
            lineas.append("Esto es lo que dice la Constitución sobre tu pregunta:")

        # Agrupa todas las partes de cada artículo en orden para no mostrar
        # fragmentos aislados que empiecen o terminen a mitad de una frase.
        por_articulo = {}
        for f in fragmentos:
            por_articulo.setdefault(f["articulo"], []).append(f)
        for numero, partes in list(por_articulo.items())[:2]:
            partes.sort(key=lambda x: x.get("parte", 1))
            texto = " ".join(p["texto"].strip() for p in partes)
            lineas.append(f"\n**[Art. {numero}]** {texto}")
        lineas.append("\nSi algo no se entiende, pide a tu docente que lo explique con un ejemplo.")
        return "\n".join(lineas)


def crear_generador(cfg, usar_llm: bool = True):
    """Prioriza GPT-OSS 20B mediante Groq y conserva el respaldo extractivo."""
    if usar_llm:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            return GeneradorGroq(cfg, api_key)
        print("[aviso] GROQ_API_KEY no está configurada. Se usa el modo extractivo.")
        respaldo = GeneradorExtractivo()
        respaldo.motivo_respaldo = "No se detectó GROQ_API_KEY en las variables de entorno."
        return respaldo
    return GeneradorExtractivo()
