# -*- coding: utf-8 -*-
"""Generación de respuestas con Qwen2.5 cuantizado en GGUF y respaldo extractivo."""
from __future__ import annotations


class GeneradorLLM:
    """Carga Qwen2.5-0.5B-Instruct en GGUF Q4 para inferencia CPU de bajo consumo."""

    modo = "llm"

    def __init__(self, cfg):
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        self.cfg = cfg
        self.nombre = "Qwen2.5-0.5B-Instruct (GGUF Q4_K_M)"
        self.max_tokens = cfg.max_tokens_nuevos_cpu

        # El archivo cuantizado ocupa menos memoria que los pesos FP32 de Transformers.
        ruta_modelo = hf_hub_download(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        )
        self.modelo = Llama(
            model_path=ruta_modelo,
            n_ctx=2048,
            n_threads=2,
            n_batch=128,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:
        """Genera una respuesta usando la plantilla de chat incorporada en el GGUF."""
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
        lineas = ["Esto es lo que dice la Constitución sobre tu pregunta (texto literal, sin explicación automática):"]
        for f in fragmentos[:2]:
            texto = f["texto"] if len(f["texto"]) <= 700 else f["texto"][:700].rsplit(" ", 1)[0] + "…"
            lineas.append(f"\n**[Art. {f['articulo']}]** {texto}")
        lineas.append("\nSi algo no se entiende, pide a tu docente que lo explique con un ejemplo.")
        return "\n".join(lineas)


def crear_generador(cfg, usar_llm: bool = True):
    """Crea el LLM cuantizado; si falla su carga, activa el respaldo extractivo."""
    if usar_llm:
        try:
            return GeneradorLLM(cfg)
        except Exception as error:
            print(f"[aviso] No se pudo cargar el LLM GGUF: {error}. Se usa el modo extractivo.")
    return GeneradorExtractivo()
