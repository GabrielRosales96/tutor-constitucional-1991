# -*- coding: utf-8 -*-
"""Generación de respuestas: LLM abierto (Qwen2.5) con respaldo extractivo si el modelo no está disponible."""
from __future__ import annotations  # anotaciones modernas


class GeneradorLLM:  # clase GeneradorLLM: Carga un LLM abierto con Transformers y genera la respuesta a partir…
    """Carga un LLM abierto con Transformers y genera la respuesta a partir de los mensajes de chat."""

    modo = "llm"  # etiqueta que indica cómo se generó la respuesta

    def __init__(self, cfg):  # función __init__
        import torch  # biblioteca de tensores
        from transformers import AutoModelForCausalLM, AutoTokenizer  # carga de modelos de Hugging Face

        self.cfg = cfg  # configuración global
        self.hay_gpu = torch.cuda.is_available()  # detecta si hay GPU
        self.nombre = cfg.modelo_llm_gpu if self.hay_gpu else cfg.modelo_llm_cpu  # modelo según el hardware (RNF-06)
        tipo = torch.float16 if self.hay_gpu else torch.float32  # precisión según el dispositivo
        self.tokenizador = AutoTokenizer.from_pretrained(self.nombre)  # tokenizador del modelo
        self.modelo = AutoModelForCausalLM.from_pretrained(self.nombre, torch_dtype=tipo)  # pesos del modelo
        self.modelo.to("cuda" if self.hay_gpu else "cpu")  # mueve el modelo al dispositivo
        self.modelo.eval()  # modo inferencia (sin entrenamiento)
        self.max_tokens = cfg.max_tokens_nuevos_gpu if self.hay_gpu else cfg.max_tokens_nuevos_cpu  # longitud máxima

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:  # función generar: Genera la respuesta del tutor.
        """Genera la respuesta del tutor."""
        import torch  # necesario para desactivar gradientes

        texto = self.tokenizador.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)  # plantilla de chat
        entradas = self.tokenizador(texto, return_tensors="pt").to(self.modelo.device)  # tokeniza y envía al dispositivo
        with torch.no_grad():  # no se calculan gradientes: ahorra memoria
            salida = self.modelo.generate(  # generación de texto
                **entradas,  # ids de entrada y máscara de atención
                max_new_tokens=self.max_tokens,  # longitud máxima de la respuesta
                do_sample=self.cfg.temperatura > 0,  # muestreo si la temperatura es mayor que cero
                temperature=max(self.cfg.temperatura, 1e-5),  # temperatura baja: respuestas estables
                top_p=self.cfg.top_p,  # muestreo por núcleo
                repetition_penalty=self.cfg.penalizacion_repeticion,  # evita repeticiones
                pad_token_id=self.tokenizador.eos_token_id,  # token de relleno
            )  # cierre de la estructura
        nuevos = salida[0][entradas["input_ids"].shape[1]:]  # se descarta el prompt y se conserva lo generado
        return self.tokenizador.decode(nuevos, skip_special_tokens=True).strip()  # texto de la respuesta


class GeneradorExtractivo:  # clase GeneradorExtractivo: Respaldo sin LLM: presenta el texto constitucional recuperado con una…
    """Respaldo sin LLM: presenta el texto constitucional recuperado con una explicación mínima."""

    modo = "extractivo"  # etiqueta del modo degradado
    nombre = "extractivo"  # nombre para mostrar

    def generar(self, mensajes: list[dict], fragmentos: list[dict] | None = None) -> str:  # función generar: Construye la respuesta citando literalmente los fragmentos más…
        """Construye la respuesta citando literalmente los fragmentos más relevantes."""
        if not fragmentos:  # sin evidencia no hay nada que mostrar
            return "No encuentro ese tema en los fragmentos de la Constitución que consulté."  # abstención
        lineas = ["Esto es lo que dice la Constitución sobre tu pregunta (texto literal, sin explicación automática):"]  # introducción
        for f in fragmentos[:2]:  # solo los dos fragmentos más relevantes
            texto = f["texto"] if len(f["texto"]) <= 700 else f["texto"][:700].rsplit(" ", 1)[0] + "…"  # recorta textos largos
            lineas.append(f"\n**[Art. {f['articulo']}]** {texto}")  # cita con número de artículo
        lineas.append("\nSi algo no se entiende, pide a tu docente que lo explique con un ejemplo.")  # cierre pedagógico
        return "\n".join(lineas)  # respuesta completa


def crear_generador(cfg, usar_llm: bool = True):  # función crear_generador: Crea el generador: LLM si es posible; si falla la carga, usa el…
    """Crea el generador: LLM si es posible; si falla la carga, usa el respaldo extractivo (degradación controlada)."""
    if usar_llm:  # si se desea el modelo de lenguaje
        try:  # intenta cargarlo
            return GeneradorLLM(cfg)  # LLM abierto
        except Exception as error:  # sin red, sin memoria, versión incompatible, etc.
            print(f"[aviso] No se pudo cargar el LLM: {error}. Se usa el modo extractivo.")  # informa del problema
    return GeneradorExtractivo()  # respaldo
