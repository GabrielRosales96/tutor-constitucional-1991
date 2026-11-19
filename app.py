# -*- coding: utf-8 -*-
"""Interfaz web (Streamlit) del Tutor Constitucional 1991."""
import streamlit as st

from tutor.config import AVISO_LEGAL, PREGUNTAS_SUGERIDAS, Config
from tutor.memoria import MemoriaCorta
from tutor.prompts import NIVELES
from tutor.tutor import crear_tutor

st.set_page_config(page_title="Tutor Constitucional 1991", page_icon="📘", layout="centered")


@st.cache_resource(show_spinner="Cargando el tutor (la primera vez puede tardar unos minutos)…")
def cargar_tutor():
    """Crea el tutor en modo extractivo temporal para aislar el fallo de llama.cpp."""
    # Diagnóstico: se desactiva únicamente el LLM GGUF; se conservan embeddings,
    # recuperación RAG, memoria, filtros, fuentes y la interfaz Streamlit.
    return crear_tutor(Config(), usar_llm=False)


def mostrar_fuentes(fuentes):
    """Muestra las fuentes sin asumir que todas tienen una puntuación semántica."""
    for fuente in fuentes:
        articulo = fuente.get("articulo", "?")
        titulo = fuente.get("titulo", "Título no identificado")
        texto = fuente.get("texto", "")
        similitud = fuente.get("similitud")
        indicador = (
            f"similitud {similitud:.2f}"
            if isinstance(similitud, (int, float))
            else "coincidencia exacta"
        )
        st.markdown(
            f"**Artículo {articulo}** · {titulo} · {indicador}\n\n> {texto}"
        )


tutor = cargar_tutor()
if "memoria" not in st.session_state:
    st.session_state.memoria = MemoriaCorta(
        tutor.cfg.memoria_intercambios,
        tutor.cfg.max_caracteres_respuesta_memoria,
    )
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

with st.sidebar:
    st.header("📘 Tutor Constitucional 1991")
    st.write(
        "Te explico la Constitución Política de Colombia con lenguaje sencillo "
        "y te muestro los artículos en que me baso."
    )
    grado = st.selectbox(
        "Tu nivel",
        list(NIVELES),
        index=1,
        help="Ajusta el vocabulario de las explicaciones. No se guarda.",
    )
    st.subheader("Puedes preguntarme")
    for ejemplo in PREGUNTAS_SUGERIDAS:
        st.markdown(f"- {ejemplo}")
    st.subheader("Limitaciones")
    st.markdown(
        "- Solo hablo de la Constitución de 1991.\n"
        "- Si no tengo evidencia, te lo digo.\n"
        "- No doy asesoría jurídica personal."
    )
    st.warning(AVISO_LEGAL)
    if st.button("🗑️ Nueva conversación"):
        st.session_state.memoria.limpiar()
        st.session_state.mensajes = []
        st.rerun()

st.title("📘 Tutor Constitucional 1991")
st.caption(
    "Chatbot educativo con recuperación de fragmentos de la Constitución · Modelos abiertos"
)

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])
        if mensaje.get("fuentes"):
            with st.expander("Ver fuentes consultadas"):
                mostrar_fuentes(mensaje["fuentes"])

pregunta = st.chat_input("Escribe tu pregunta sobre la Constitución…")
if pregunta:
    st.session_state.mensajes.append({"rol": "user", "texto": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en la Constitución…"):
            resultado = tutor.responder(pregunta, st.session_state.memoria, grado)

        st.markdown(resultado["respuesta"])
        if resultado["fuentes"]:
            with st.expander("Ver fuentes consultadas"):
                mostrar_fuentes(resultado["fuentes"])

        if resultado.get("modo") == "extractivo":
            st.info(
                "Modo sin modelo de lenguaje: te muestro el texto constitucional tal cual."
            )

    st.session_state.mensajes.append(
        {
            "rol": "assistant",
            "texto": resultado["respuesta"],
            "fuentes": resultado["fuentes"],
        }
    )
