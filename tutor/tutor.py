# -*- coding: utf-8 -*-
"""Orquestador del Tutor Constitucional: filtro → recuperación → validación → generación → citas → registro."""
from __future__ import annotations  # anotaciones modernas

import re  # expresiones regulares para verificar citas
import time  # medición de latencia

from .config import AVISO_LEGAL, PREGUNTAS_SUGERIDAS, Config  # configuración y textos fijos
from .generador import GeneradorExtractivo, crear_generador  # generación de respuestas
from .indice import IndiceConstitucion, crear_incrustador, numeros_de_articulo  # recuperación
from .ingesta import cargar_articulos, fragmentar  # corpus
from .memoria import MemoriaCorta, consulta_para_recuperar  # memoria de sesión
from .prompts import construir_mensajes  # construcción del prompt
from .registro import Registro  # registro técnico sin datos personales
from .seguridad import clasificar, mensaje_fuera_de_alcance, mensaje_riesgo, mensaje_saludo, normalizar  # filtro determinista

# Palabras sin contenido temático (se ignoran al juzgar si una pregunta es ambigua)
VACIAS = set("que cual cuales como cuando donde quien quienes por para de del la las el los un una unos unas y o a en es son se me mi tu su al lo le les con sobre dice dime explicame explica hablame cuentame podrias puedes quiero saber pregunta duda ayuda favor porfa eso esto ese esa esta este esos esas ello asi algo mas".split())  # continuación de la instrucción anterior
# Temas demasiado generales: la pregunta necesita precisión antes de recuperar
GENERICAS = {  # continuación de la instrucción anterior
    "derechos": "¿Te refieres a los **derechos fundamentales** (Art. 11 a 41), a los **sociales, económicos y culturales** (Art. 42 a 77) o a los **colectivos y del ambiente** (Art. 78 a 82)?",  # texto o patrón (continuación de la definición anterior)
    "derecho": "¿Qué derecho te interesa: la vida, la igualdad, la educación, la libertad de expresión…?",  # texto o patrón (continuación de la definición anterior)
    "deberes": "¿Quieres saber los **deberes y obligaciones de las personas y ciudadanos** (Art. 95) o los deberes del Estado?",  # texto o patrón (continuación de la definición anterior)
    "estado": "¿Te interesa cómo está **organizado el Estado** (ramas del poder), sus **fines** (Art. 2) o su **definición** (Art. 1)?",  # texto o patrón (continuación de la definición anterior)
    "gobierno": "¿Quieres saber sobre la **rama ejecutiva** (Presidente y ministros) o sobre todo el **poder público**?",  # texto o patrón (continuación de la definición anterior)
    "ley": "¿Hablas de cómo se **hacen las leyes** (rama legislativa) o de su relación con la Constitución (Art. 4)?",  # texto o patrón (continuación de la definición anterior)
    "leyes": "¿Hablas de cómo se **hacen las leyes** (rama legislativa) o de su relación con la Constitución (Art. 4)?",  # texto o patrón (continuación de la definición anterior)
    "constitucion": "¿Qué parte de la Constitución quieres entender: principios, derechos, ramas del poder o mecanismos de protección?",  # texto o patrón (continuación de la definición anterior)
}  # cierre de la estructura
# Patrón de citas escritas por el modelo: «[Art. 86]», «[Artículo 86]» o «artículo 86»
RE_CITA = re.compile(r"(?i)\bart(?:[ií]culo|\.)\s*(\d{1,3}[A-Za-z]?)\b")  # continuación de la instrucción anterior
# Variante entre corchetes, que es la que se puede eliminar si resulta inválida
RE_CITA_CORCHETES = re.compile(r"(?i)\s*\[\s*art(?:[ií]culo|\.)?\s*(\d{1,3}[A-Za-z]?)\s*\]")  # continuación de la instrucción anterior


def es_ambigua(pregunta: str, memoria: MemoriaCorta) -> str | None:  # función es_ambigua: Devuelve un mensaje de aclaración si la pregunta es demasiado…
    """Devuelve un mensaje de aclaración si la pregunta es demasiado general; si no, None (HU-03)."""
    t = normalizar(re.sub(r"[¿?¡!.,;:()\"']", " ", pregunta))  # texto sin signos ni tildes
    palabras = [w for w in t.split() if w not in VACIAS]  # palabras con contenido temático
    if numeros_de_articulo(pregunta):  # si pide un artículo concreto no es ambigua
        return None  # se continúa
    if not palabras:  # no queda ninguna palabra con contenido («¿y eso?»)
        return None if len(memoria) else "No alcancé a entender de qué tema hablas. ¿Puedes decirme qué parte de la Constitución quieres entender?"  # pide precisión
    if len(palabras) == 1 and palabras[0] in GENERICAS:  # un solo término demasiado general
        return GENERICAS[palabras[0]]  # aclaración específica
    return None  # la pregunta es suficientemente clara


def verificar_citas(respuesta: str, fragmentos: list[dict]) -> tuple[str, list[str], list[str]]:  # función verificar_citas: Comprueba que los artículos citados estén en las fuentes; elimina los…
    """Comprueba que los artículos citados estén en las fuentes; elimina los inválidos y garantiza la cita (RF-03)."""
    validos = {f["articulo"].upper() for f in fragmentos}  # artículos realmente recuperados
    citados = {c.upper() for c in RE_CITA.findall(respuesta)}  # artículos que menciona el texto
    invalidos = sorted(citados - validos)  # citas sin respaldo en las fuentes
    for numero in invalidos:  # elimina las citas entre corchetes inválidas
        respuesta = re.sub(rf"(?i)\s*\[\s*art(?:[ií]culo|\.)?\s*{numero}\s*\]", "", respuesta)  # quita «[Art. N]»
    restantes = {c.upper() for c in RE_CITA.findall(respuesta)}  # citas que sobreviven
    if invalidos and restantes & set(invalidos):  # quedó alguna mención en prosa sin respaldo
        respuesta += f"\n\n⚠️ Revisa en el texto oficial: se mencionó el artículo {', '.join(invalidos)}, que no aparece en las fuentes consultadas."  # advertencia
    buenas = sorted(citados & validos, key=lambda x: (int(re.match(r"\d+", x).group()), x))  # citas válidas ordenadas
    if not buenas:  # el modelo no citó nada válido
        orden = sorted(validos, key=lambda x: (int(re.match(r"\d+", x).group()), x))  # fuentes ordenadas
        respuesta += "\n\nFuentes consultadas: " + ", ".join(f"[Art. {a}]" for a in orden)  # se agregan automáticamente
    return respuesta.strip(), buenas, invalidos  # texto final, citas válidas e inválidas


class TutorConstitucional:  # clase TutorConstitucional: Canaliza cada pregunta por el flujo completo y devuelve respuesta,…
    """Canaliza cada pregunta por el flujo completo y devuelve respuesta, fuentes y metadatos."""

    def __init__(self, cfg: Config, indice: IndiceConstitucion, generador, registro: Registro):  # función __init__
        self.cfg = cfg  # configuración
        self.indice = indice  # almacén vectorial
        self.generador = generador  # LLM o respaldo extractivo
        self.registro = registro  # registro técnico
        self.respaldo = GeneradorExtractivo()  # respaldo ante fallos del LLM

    def _salida(self, categoria: str, texto: str, t0: float, fuentes=None, **extra) -> dict:  # función _salida: Cierra una interacción: calcula latencia, registra (sin texto…
        """Cierra una interacción: calcula latencia, registra (sin texto personal) y arma la respuesta."""
        fuentes = fuentes or []  # lista vacía si no hubo recuperación
        latencia = (time.perf_counter() - t0) * 1000  # milisegundos transcurridos
        self.registro.registrar(categoria, latencia, len(fuentes))  # registro sin datos personales
        return {"respuesta": texto, "categoria": categoria, "fuentes": fuentes, "latencia_ms": round(latencia, 1), **extra}  # resultado

    def responder(self, pregunta: str, memoria: MemoriaCorta, grado: str | None = None) -> dict:  # función responder: Procesa una pregunta del estudiante.
        """Procesa una pregunta del estudiante."""
        t0 = time.perf_counter()  # inicio del cronómetro
        pregunta = pregunta.strip()[: self.cfg.max_caracteres_pregunta]  # limpia y limita el tamaño
        categoria, subtipo = clasificar(pregunta)  # filtro determinista (sin LLM)
        if categoria == "riesgo":  # HU-04: se interrumpe el flujo y no se invoca el LLM
            return self._salida("riesgo", mensaje_riesgo(subtipo), t0, modo="filtro")  # mensaje de seguridad
        if categoria == "saludo":  # saludos y despedidas
            return self._salida("saludo", mensaje_saludo(subtipo), t0, modo="filtro")  # respuesta fija
        if categoria == "fuera_de_alcance":  # manipulación o caso personal
            return self._salida("fuera_de_alcance", mensaje_fuera_de_alcance(subtipo), t0, modo="filtro")  # redirección
        aclaracion = es_ambigua(pregunta, memoria)  # HU-03: ¿pregunta demasiado general?
        if aclaracion:  # si necesita precisión
            sugerencias = "\n".join(f"- {p}" for p in PREGUNTAS_SUGERIDAS[:3])  # ejemplos de preguntas claras
            return self._salida("aclaracion", f"{aclaracion}\n\nPor ejemplo, puedes preguntarme:\n{sugerencias}", t0, modo="filtro")  # pide aclaración
        consulta = consulta_para_recuperar(pregunta, memoria)  # añade contexto si hay referencias a lo anterior
        pedidos = numeros_de_articulo(consulta)  # artículos mencionados explícitamente (incluye el contexto previo)
        directos = [f for n in pedidos for f in self.indice.articulo(n)]  # búsqueda exacta por número
        if pedidos and not directos:  # pidió un artículo que no existe en el corpus
            texto = f"No encuentro el artículo {', '.join(pedidos)} en la parte permanente de la Constitución (tiene {self.cfg.articulos_esperados} artículos). Revisa el número o pregúntame por el tema."  # abstención
            return self._salida("sin_evidencia", texto, t0, modo="filtro")  # sin evidencia
        semanticos = self.indice.buscar(consulta, self.cfg.top_k)  # búsqueda semántica
        umbral = self.cfg.umbral_para(self.indice.incrustador.etiqueta)  # umbral calibrado para el embedding activo
        if not directos and (not semanticos or semanticos[0]["similitud"] < umbral):  # evidencia insuficiente
            texto = ("No encuentro ese tema en la Constitución de 1991. Puede que esté fuera de mi alcance o que necesite "  # continuación de la instrucción anterior
                     "otras palabras. ¿Puedes reformular la pregunta o decirme qué artículo o tema buscas?")  # abstención (RF-05)
            return self._salida("sin_evidencia", texto, t0, modo="filtro", mejor_similitud=semanticos[0]["similitud"] if semanticos else 0.0)  # sin LLM
        if directos:  # si se pidió un artículo, no se mezclan artículos vecinos
            fragmentos = directos
        else:
            # La búsqueda semántica identifica artículos pertinentes; luego se recuperan
            # todas sus partes para evitar respuestas que empiecen a mitad de una frase.
            articulos_relevantes = []
            for resultado in semanticos:
                if resultado["similitud"] < umbral - self.cfg.margen_fragmentos:
                    continue
                numero = resultado["articulo"]
                if numero not in articulos_relevantes:
                    articulos_relevantes.append(numero)
                if len(articulos_relevantes) == 1:
                    break
            fragmentos = [
                f for numero in articulos_relevantes
                for f in self.indice.articulo(numero)
            ]
        mensajes = construir_mensajes(pregunta, fragmentos, memoria.como_mensajes(), grado, self.cfg.max_caracteres_contexto)  # prompt
        try:  # generación con el LLM
            texto = self.generador.generar(mensajes, fragmentos)  # respuesta del modelo
            modo = getattr(self.generador, "modo", "llm")  # modo usado
        except Exception as error:  # fallo en tiempo de ejecución (memoria, etc.)
            print(f"[aviso] Falló la generación: {error}. Se usa el modo extractivo.")  # informa
            texto, modo = self.respaldo.generar(mensajes, fragmentos), "extractivo"  # respaldo
        texto, validas, invalidas = verificar_citas(texto, fragmentos)  # verificación de citas
        memoria.agregar(pregunta, texto)  # guarda el intercambio en la memoria de sesión
        return self._salida("normal", texto, t0, fuentes=fragmentos, modo=modo, citas_validas=validas, citas_invalidas=invalidas)  # resultado


def crear_tutor(cfg: Config | None = None, usar_llm: bool = True, forzar_lexico: bool = False) -> TutorConstitucional:  # función crear_tutor: Construye todas las piezas del sistema a partir de la configuración.
    """Construye todas las piezas del sistema a partir de la configuración."""
    cfg = cfg or Config()  # configuración por defecto
    articulos = cargar_articulos(cfg.ruta_articulos)  # corpus ya segmentado
    fragmentos = fragmentar(articulos, cfg.max_caracteres_fragmento, cfg.solape_caracteres)  # fragmentos indexables
    incrustador = crear_incrustador(cfg, forzar_lexico)  # modelo de embeddings (o respaldo)
    indice = IndiceConstitucion(cfg, incrustador)  # almacén vectorial persistente
    indice.construir(fragmentos)  # indexa solo si hace falta
    generador = crear_generador(cfg, usar_llm)  # LLM o respaldo extractivo
    return TutorConstitucional(cfg, indice, generador, Registro(cfg.ruta_registro))  # sistema completo


__all__ = ["TutorConstitucional", "crear_tutor", "verificar_citas", "es_ambigua", "AVISO_LEGAL"]  # API pública del módulo
