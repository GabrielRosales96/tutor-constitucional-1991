# -*- coding: utf-8 -*-
"""Filtro determinista (sin LLM): riesgo, saludos, intentos de manipulación y consultas de caso personal."""
from __future__ import annotations  # anotaciones modernas

import re  # expresiones regulares
import unicodedata  # para quitar tildes y comparar sin acentos

from .config import LINEAS_AYUDA  # líneas de ayuda configurables


def normalizar(texto: str) -> str:  # función normalizar: Minúsculas, sin tildes y con espacios simples, para que las reglas no…
    """Minúsculas, sin tildes y con espacios simples, para que las reglas no dependan de la ortografía."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")  # quita tildes
    return re.sub(r"\s+", " ", sin_tildes).strip()  # colapsa espacios


# Reglas de riesgo: se escriben sin tildes porque el texto se normaliza antes de comparar
RIESGO = {  # continuación de la instrucción anterior
    "autolesion": (  # pensamientos de hacerse daño
        r"\bsuicid\w*", r"\bme quiero morir\b", r"\bquiero morirme\b", r"\bno quiero (seguir )?viviendo?\b",  # texto o patrón (continuación de la definición anterior)
        r"\bquitarme la vida\b", r"\bmatarme\b", r"\bacabar con mi vida\b", r"\bhacerme (dano|mal)\b",  # texto o patrón (continuación de la definición anterior)
        r"\bcortarme\b", r"\bautolesion\w*", r"\bno (le )?encuentro sentido a (la vida|vivir)\b",  # texto o patrón (continuación de la definición anterior)
        r"\bmejor (estar|estaria) muert[oa]\b",  # texto o patrón (continuación de la definición anterior)
    ),  # cierre de la estructura
    "violencia": (  # violencia o abuso hacia quien escribe
        r"\bme (pega|pegan|golpea|golpean|maltrata|maltratan|amenaza|amenazan|acosa|acosan)\b",  # texto o patrón (continuación de la definición anterior)
        r"\bme (violaron|violo|violan|abusaron|abusa|abusan)\b", r"\babusan de mi\b",  # texto o patrón (continuación de la definición anterior)
        r"\bme estan (pegando|golpeando|amenazando|maltratando|acosando)\b",  # texto o patrón (continuación de la definición anterior)
        r"\btengo miedo (de|a) (mi|que me)\b", r"\balguien me (esta )?(amenazando|siguiendo|acosando)\b",  # texto o patrón (continuación de la definición anterior)
    ),  # cierre de la estructura
    "emergencia": (  # peligro inmediato
        r"\bayuda urgente\b", r"\bme van a (matar|hacer dano)\b", r"\b(hay|tiene|tengo) un arma\b",  # texto o patrón (continuación de la definición anterior)
        r"\bme (secuestraron|secuestran)\b", r"\b(tengo|es|estoy en) una? emergencia\b",  # texto o patrón (continuación de la definición anterior)
    ),  # cierre de la estructura
}  # cierre de la estructura
# Intentos de manipular al sistema (inyección de instrucciones)
INYECCION = (  # continuación de la instrucción anterior
    r"\b(ignora|ignore|olvida)\w* (todas )?(las|tus|mis) (instrucciones|reglas)\b", r"\b(muestra|revela|dime|repite)\w* (tu|el|las) (prompt|mensaje del sistema|instrucciones)\b",  # texto o patrón (continuación de la definición anterior)
    r"\bmodo (desarrollador|dios)\b", r"\bjailbreak\b", r"\bactua como\b", r"\bfinge (ser|que)\b",  # texto o patrón (continuación de la definición anterior)
)  # cierre de la estructura
# Peticiones de asesoría sobre un caso personal (fuera del alcance educativo)
ASESORIA = (  # continuación de la instrucción anterior
    r"\bmi caso\b", r"\b(quiero|voy a|debo|puedo) (demandar|denunciar)\b", r"\bredacta(me)? (una|mi) (tutela|demanda|derecho de peticion)\b",  # texto o patrón (continuación de la definición anterior)
    r"\bcomo (demando|denuncio) a\b", r"\b(ganar|ganare|ganaria) (mi|el) (caso|juicio|pleito)\b",  # texto o patrón (continuación de la definición anterior)
)  # cierre de la estructura
# Saludos y despedidas (se responden sin recuperar documentos)
SALUDO = (r"^(hola|holi|buenas|buenos dias|buenas tardes|buenas noches|hey|que tal|hello|saludos)\b[ !.,¡?]*$", r"^(gracias|muchas gracias|chao|adios|hasta luego|ok gracias)\b[ !.,¡?]*$")  # continuación de la instrucción anterior


def clasificar(texto: str) -> tuple[str, str]:  # función clasificar: Devuelve (categoría, subtipo). Categorías: riesgo, fuera_de_alcance,…
    """Devuelve (categoría, subtipo). Categorías: riesgo, fuera_de_alcance, saludo o normal."""
    t = normalizar(texto)  # texto sin tildes ni mayúsculas
    for subtipo, patrones in RIESGO.items():  # revisa primero el riesgo (máxima prioridad)
        if any(re.search(p, t) for p in patrones):  # si coincide algún patrón
            return "riesgo", subtipo  # se interrumpe el flujo normal
    if any(re.search(p, t) for p in INYECCION):  # intento de manipulación
        return "fuera_de_alcance", "inyeccion"  # no se invoca al LLM
    if any(re.search(p, t) for p in ASESORIA):  # caso personal
        return "fuera_de_alcance", "asesoria"  # se redirige a canales humanos
    if any(re.search(p, t) for p in SALUDO):  # saludo o agradecimiento
        return "saludo", "gracias" if "gracias" in t or "chao" in t or "adios" in t else "hola"  # variante
    return "normal", ""  # consulta académica común


def _lista_lineas() -> str:  # función _lista_lineas: Formatea las líneas de ayuda configuradas.
    """Formatea las líneas de ayuda configuradas."""
    return "\n".join(f"- **{numero}**: {descripcion}" for numero, descripcion in LINEAS_AYUDA)  # viñetas


def mensaje_riesgo(subtipo: str) -> str:  # función mensaje_riesgo: Mensaje predefinido de orientación de seguridad (HU-04). No se invoca…
    """Mensaje predefinido de orientación de seguridad (HU-04). No se invoca ningún modelo de lenguaje."""
    if subtipo == "autolesion":  # apoyo emocional
        apertura = "Siento mucho que estés pasando por algo tan difícil. Lo que sientes importa y no tienes que enfrentarlo solo/a."  # empatía
    elif subtipo == "emergencia":  # peligro inmediato
        apertura = "Si estás en peligro ahora mismo, lo más importante es pedir ayuda de inmediato."  # urgencia
    else:  # violencia o abuso
        apertura = "Lamento lo que estás viviendo. Nadie tiene derecho a hacerte daño y mereces protección."  # validación
    return (  # mensaje completo
        f"{apertura}\n\n"  # texto o patrón (continuación de la definición anterior)
        "Habla ahora con un adulto de confianza (familiar, docente u orientador/a) y comunícate con estas líneas:\n"  # texto o patrón (continuación de la definición anterior)
        f"{_lista_lineas()}\n\n"  # texto o patrón (continuación de la definición anterior)
        "Este tutor es solo educativo y no puede darte la ayuda que necesitas en este momento. "  # texto o patrón (continuación de la definición anterior)
        "Cuando estés mejor, con gusto seguimos hablando de la Constitución."  # texto o patrón (continuación de la definición anterior)
    )  # cierre de la estructura


def mensaje_saludo(subtipo: str) -> str:  # función mensaje_saludo: Respuesta breve a saludos y despedidas.
    """Respuesta breve a saludos y despedidas."""
    if subtipo == "gracias":  # despedida
        return "¡Con gusto! Si tienes otra duda sobre la Constitución de 1991, aquí estaré. 📘"  # cierre amable
    return (  # saludo inicial
        "¡Hola! Soy el **Tutor Constitucional 1991**. Te explico la Constitución Política de Colombia con ejemplos sencillos "  # texto o patrón (continuación de la definición anterior)
        "y te muestro en qué artículos me baso. Pregúntame, por ejemplo, qué es la tutela o cuáles son las ramas del poder público."  # texto o patrón (continuación de la definición anterior)
    )  # cierre de la estructura


def mensaje_fuera_de_alcance(subtipo: str) -> str:  # función mensaje_fuera_de_alcance: Respuesta fija cuando la consulta pide asesoría personal o intenta…
    """Respuesta fija cuando la consulta pide asesoría personal o intenta cambiar las reglas del tutor."""
    if subtipo == "inyeccion":  # intento de manipulación
        return "No puedo cambiar mis reglas ni mostrar mis instrucciones. Puedo ayudarte con tus dudas sobre la Constitución de 1991. ¿Cuál es tu pregunta?"  # rechazo amable
    return (  # asesoría individual
        "Para un caso real necesitas apoyo humano: habla con tu docente, el personero estudiantil, la Defensoría del Pueblo "  # texto o patrón (continuación de la definición anterior)
        "o un consultorio jurídico universitario. Yo no puedo dar asesoría jurídica individual. "  # texto o patrón (continuación de la definición anterior)
        "Sí puedo explicarte, en general, qué dice la Constitución sobre el tema. ¿Quieres que lo hagamos?"  # texto o patrón (continuación de la definición anterior)
    )  # cierre de la estructura
