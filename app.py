# -*- coding: utf-8 -*-
"""Interfaz web (Streamlit) del Tutor Constitucional 1991."""
import streamlit as st  # framework de interfaz web de código abierto

from tutor.config import AVISO_LEGAL, PREGUNTAS_SUGERIDAS, Config  # textos y configuración centralizados
from tutor.memoria import MemoriaCorta  # memoria de corto plazo
from tutor.prompts import NIVELES  # niveles escolares disponibles
from tutor.tutor import crear_tutor  # fábrica del sistema completo

st.set_page_config(page_title="Tutor Constitucional 1991", page_icon="📘", layout="centered")  # título de la pestaña


@st.cache_resource(show_spinner="Cargando el tutor (la primera vez puede tardar unos minutos)…")  # se carga una sola vez por servidor
def cargar_tutor():  # función cargar_tutor: Crea el tutor: embeddings, índice y modelo de lenguaje.
    """Crea el tutor: embeddings, índice y modelo de lenguaje."""
    return crear_tutor(Config())  # sistema completo con la configuración por defecto


tutor = cargar_tutor()  # instancia compartida entre sesiones (solo lectura)
if "memoria" not in st.session_state:  # cada sesión del navegador tiene su propia memoria
    st.session_state.memoria = MemoriaCorta(tutor.cfg.memoria_intercambios, tutor.cfg.max_caracteres_respuesta_memoria)  # memoria nueva
if "mensajes" not in st.session_state:  # historial visible en pantalla
    st.session_state.mensajes = []  # lista vacía al comenzar

with st.sidebar:  # panel lateral con guía de uso
    st.header("📘 Tutor Constitucional 1991")  # título del panel
    st.write("Te explico la Constitución Política de Colombia con lenguaje sencillo y te muestro los artículos en que me baso.")  # descripción
    grado = st.selectbox("Tu nivel", list(NIVELES), index=1, help="Ajusta el vocabulario de las explicaciones. No se guarda.")  # nivel escolar
    st.subheader("Puedes preguntarme")  # sección de ejemplos
    for ejemplo in PREGUNTAS_SUGERIDAS:  # recorre las preguntas sugeridas
        st.markdown(f"- {ejemplo}")  # muestra cada ejemplo
    st.subheader("Limitaciones")  # sección de límites
    st.markdown("- Solo hablo de la Constitución de 1991.\n- Si no tengo evidencia, te lo digo.\n- No doy asesoría jurídica personal.")  # límites
    st.warning(AVISO_LEGAL)  # aviso de posibles errores
    if st.button("🗑️ Nueva conversación"):  # botón para reiniciar
        st.session_state.memoria.limpiar()  # borra la memoria de corto plazo
        st.session_state.mensajes = []  # borra el historial visible
        st.rerun()  # recarga la página

st.title("📘 Tutor Constitucional 1991")  # título principal
st.caption("Chatbot educativo con recuperación de fragmentos de la Constitución · Modelos abiertos")  # subtítulo

for m in st.session_state.mensajes:  # muestra la conversación previa
    with st.chat_message(m["rol"]):  # distingue visualmente estudiante y tutor
        st.markdown(m["texto"])  # contenido del mensaje
        if m.get("fuentes"):  # HU-05: el docente puede verificar las fuentes
            with st.expander("Ver fuentes consultadas"):  # sección desplegable
                for f in m["fuentes"]:  # recorre los fragmentos
                    st.markdown(f"**Artículo {f['articulo']}** · {f['titulo']} · similitud {f['similitud']:.2f}\n\n> {f['texto']}")  # cita textual

pregunta = st.chat_input("Escribe tu pregunta sobre la Constitución…")  # caja de entrada del chat
if pregunta:  # si el estudiante envió algo
    st.session_state.mensajes.append({"rol": "user", "texto": pregunta})  # guarda el turno del estudiante
    with st.chat_message("user"):  # muestra el turno del estudiante
        st.markdown(pregunta)  # texto escrito
    with st.chat_message("assistant"):  # turno del tutor
        with st.spinner("Buscando en la Constitución…"):  # indicador de espera
            resultado = tutor.responder(pregunta, st.session_state.memoria, grado)  # flujo completo
        st.markdown(resultado["respuesta"])  # respuesta del tutor
        if resultado["fuentes"]:  # si hubo evidencia
            with st.expander("Ver fuentes consultadas"):  # sección desplegable
                for f in resultado["fuentes"]:  # recorre los fragmentos
                    st.markdown(f"**Artículo {f['articulo']}** · {f['titulo']} · similitud {f['similitud']:.2f}\n\n> {f['texto']}")  # cita textual
        if resultado.get("modo") == "extractivo":  # modo degradado
            st.info("Modo sin modelo de lenguaje: te muestro el texto constitucional tal cual.")  # aviso
    st.session_state.mensajes.append({"rol": "assistant", "texto": resultado["respuesta"], "fuentes": resultado["fuentes"]})  # guarda el turno
