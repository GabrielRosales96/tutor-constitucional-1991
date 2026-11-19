---
title: Tutor Constitucional 1991
emoji: 📘
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: app.py
pinned: false
---

# Tutor Constitucional 1991
Chatbot educativo (RAG, modelos abiertos) sobre la Constitución Política de Colombia de 1991.
Herramienta exclusivamente educativa: no ofrece asesoría jurídica ni reemplaza a docentes, abogados ni autoridades.

## Activar respuestas generativas con Groq

La aplicación utiliza el modelo de pesos abiertos `openai/gpt-oss-20b` mediante la API de Groq. Para habilitarlo en Streamlit Community Cloud:

1. Crea una cuenta en https://console.groq.com/ y genera una API Key.
2. En la aplicación de Streamlit Cloud abre **Settings → Secrets**.
3. Añade esta línea, reemplazando el valor por tu clave privada:

```toml
GROQ_API_KEY = "TU_CLAVE_PRIVADA"
```

4. Guarda los Secrets y reinicia la aplicación.

La clave se lee desde el entorno y no se almacena en el repositorio. No la publiques ni la compartas. Si no está configurada o el servicio no está disponible, la aplicación conserva el modo de respaldo extractivo y muestra el diagnóstico correspondiente.

## Componentes

- Interfaz: Streamlit.
- Recuperación de información: RAG con ChromaDB y embeddings multilingües.
- Generación: GPT-OSS 20B mediante Groq API.
- Memoria: contexto conversacional de corto plazo.
- Respaldo: generación extractiva a partir de los artículos recuperados.
