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


## Activar respuestas generativas (Hugging Face)

La aplicación usa Qwen2.5-1.5B-Instruct, un modelo de pesos abiertos, mediante la cuota gratuita disponible de Hugging Face Inference. Para habilitarlo en Streamlit Community Cloud:

1. Crea una cuenta gratuita en https://huggingface.co/ y genera un token de acceso desde Settings → Access Tokens.
2. En la aplicación de Streamlit Cloud abre **Settings → Secrets**.
3. Añade esta línea, reemplazando el valor por tu token:

```toml
HF_TOKEN = "hf_tu_token"
```

4. Guarda los Secrets y reinicia la aplicación.

El token se lee desde el entorno y no se almacena en el repositorio. Si no está configurado o el servicio gratuito no está disponible, la aplicación conserva el modo de respaldo extractivo y muestra un aviso.
