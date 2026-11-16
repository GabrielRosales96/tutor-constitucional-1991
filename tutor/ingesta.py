# -*- coding: utf-8 -*-
"""Ingesta: descarga del PDF oficial, limpieza, segmentación por artículo y fragmentación."""
from __future__ import annotations  # anotaciones modernas

import json  # lectura y escritura del corpus en JSON Lines
import re  # expresiones regulares para limpiar y segmentar
from pathlib import Path  # rutas de archivos

# Estructura oficial de los Títulos de la Constitución: (primer artículo, último artículo, nombre)
TITULOS = (  # continuación de la instrucción anterior
    (1, 10, "Título I. De los principios fundamentales"),  # principios del Estado
    (11, 95, "Título II. De los derechos, las garantías y los deberes"),  # derechos y deberes
    (96, 102, "Título III. De los habitantes y del territorio"),  # nacionalidad, ciudadanía, territorio
    (103, 112, "Título IV. De la participación democrática y de los partidos políticos"),  # participación
    (113, 131, "Título V. De la organización del Estado"),  # estructura y función pública
    (132, 187, "Título VI. De la rama legislativa"),  # Congreso
    (188, 227, "Título VII. De la rama ejecutiva"),  # Presidente y Gobierno
    (228, 257, "Título VIII. De la rama judicial"),  # justicia
    (258, 266, "Título IX. De las elecciones y de la organización electoral"),  # elecciones
    (267, 284, "Título X. De los organismos de control"),  # Contraloría, Ministerio Público
    (285, 331, "Título XI. De la organización territorial"),  # departamentos y municipios
    (332, 373, "Título XII. Del régimen económico y de la hacienda pública"),  # economía
    (374, 380, "Título XIII. De la reforma de la Constitución"),  # reformas
)  # cierre de la estructura

# Líneas que son ruido del PDF (encabezados, números de página, notas editoriales)
PATRONES_RUIDO = (  # continuación de la instrucción anterior
    r"^\s*Departamento Administrativo de la Función Pública\s*$",  # encabezado de Función Pública
    r"^\s*Constitución Política 1 de 1991 Asamblea\s*$",  # encabezado de Función Pública
    r"^\s*Nacional Constituyente\s*$",  # continuación del encabezado
    r"^\s*\d+\s+EVA\s*-\s*Gestor Normativo\s*$",  # pie de página con número
    r"^\s*\*jurisprudencia\*\s*$",  # marcador editorial
    r"^\s*\(Ver\b.*$",  # notas de concordancia "(Ver Ley ...)"
    r"^\s*Página\s+\d+(\s+de\s+\d+)?\s*$",  # numeración de página genérica
    r"^\s*\d{1,4}\s*$",  # línea que solo contiene un número de página
    r"^\s*Constitución Política de Colombia\s*(\d{4})?\s*$",  # encabezado repetido
    r"^\s*Los datos publicados tienen propósitos.*$",  # aviso de Función Pública
)  # cierre de la estructura

# Marcador donde terminan los artículos permanentes y empiezan los transitorios
PATRON_TRANSITORIOS = re.compile(r"(?m)^\s*(DISPOSICIONES TRANSITORIAS|ART[IÍ]CULO\s+TRANSITORIO)\b")  # continuación de la instrucción anterior
# Encabezado de artículo: «ARTÍCULO 86.» o «ARTICULO 1o.-»; admite sufijos como 22A
PATRON_ARTICULO = re.compile(r"(?im)^\s*ART[IÍ]CULO\s+(\d{1,3}[A-Z]?)\s*(?:[º°]|o\b)?\s*[.\-–]")  # continuación de la instrucción anterior


def descargar_pdf(url: str, destino: Path) -> Path:  # función descargar_pdf: Descarga el PDF desde la URL oficial y verifica que realmente sea un…
    """Descarga el PDF desde la URL oficial y verifica que realmente sea un PDF."""
    import requests  # se importa aquí para que el módulo funcione aunque no haya internet

    destino.parent.mkdir(parents=True, exist_ok=True)  # crea la carpeta de destino si no existe
    cabeceras = {"User-Agent": "Mozilla/5.0 (TutorConstitucional; uso academico)"}  # algunos sitios rechazan clientes sin agente
    respuesta = requests.get(url, headers=cabeceras, timeout=90)  # petición HTTP con tiempo máximo
    respuesta.raise_for_status()  # lanza error si el servidor responde con código de fallo
    if not respuesta.content.startswith(b"%PDF"):  # un PDF válido empieza con esta firma
        raise ValueError("La URL no devolvió un PDF válido.")  # se detiene para evitar procesar HTML por error
    destino.write_bytes(respuesta.content)  # guarda el PDF en disco
    return destino  # devuelve la ruta del archivo


def extraer_texto(ruta_pdf: Path) -> str:  # función extraer_texto: Extrae el texto de todas las páginas del PDF.
    """Extrae el texto de todas las páginas del PDF."""
    from pypdf import PdfReader  # lector de PDF de código abierto

    lector = PdfReader(str(ruta_pdf))  # abre el PDF
    paginas = [(pagina.extract_text() or "") for pagina in lector.pages]  # texto de cada página
    return "\n".join(paginas)  # une todas las páginas en un solo texto


def limpiar_texto(texto: str) -> str:  # función limpiar_texto: Elimina ruido editorial y normaliza espacios sin alterar el contenido…
    """Elimina ruido editorial y normaliza espacios sin alterar el contenido normativo."""
    texto = texto.replace("\r", "\n").replace(" ", " ")  # unifica saltos de línea y espacios duros
    patrones = [re.compile(p) for p in PATRONES_RUIDO]  # compila los patrones de ruido
    lineas_limpias = []  # aquí se acumulan las líneas que se conservan
    for linea in texto.split("\n"):  # recorre línea por línea
        if any(p.match(linea) for p in patrones):  # si la línea es ruido
            continue  # se descarta
        lineas_limpias.append(linea.rstrip())  # se conserva sin espacios al final
    texto = "\n".join(lineas_limpias)  # reconstruye el texto
    texto = re.sub(r"[ \t]+", " ", texto)  # colapsa espacios repetidos
    texto = re.sub(r"\n{3,}", "\n\n", texto)  # colapsa saltos de línea excesivos
    return texto.strip()  # quita espacios en los extremos


def titulo_de(numero: int) -> str:  # función titulo_de: Devuelve el nombre del Título al que pertenece un artículo según su…
    """Devuelve el nombre del Título al que pertenece un artículo según su número."""
    for inicio, fin, nombre in TITULOS:  # recorre la estructura oficial
        if inicio <= numero <= fin:  # si el artículo cae en el rango
            return nombre  # devuelve el nombre del Título
    return "Sin título identificado"  # valor de respaldo


def _es_encabezado(linea: str) -> bool:  # función _es_encabezado: Indica si una línea parece un encabezado de sección (todo en…
    """Indica si una línea parece un encabezado de sección (todo en mayúsculas o TÍTULO/CAPÍTULO)."""
    texto = linea.strip()  # quita espacios
    if not texto or len(texto) > 140:  # vacía o demasiado larga para ser encabezado
        return False  # no es encabezado
    if re.match(r"(?i)^(T[IÍ]TULO|CAP[IÍ]TULO)\b", texto):  # empieza con TÍTULO o CAPÍTULO
        return True  # es encabezado
    letras = [c for c in texto if c.isalpha()]  # solo letras
    return bool(letras) and all(c.isupper() for c in letras) and len(letras) > 3  # todo en mayúsculas


def segmentar_articulos(texto_limpio: str, salto_maximo: int = 6) -> list[dict]:  # función segmentar_articulos: Divide el texto en artículos permanentes con metadatos (número,…
    """Divide el texto en artículos permanentes con metadatos (número, título y capítulo).

    salto_maximo: mayor diferencia aceptada entre artículos consecutivos (filtra falsos encabezados dentro de notas)."""
    corte = PATRON_TRANSITORIOS.search(texto_limpio)  # busca dónde empiezan los transitorios
    permanente = texto_limpio[: corte.start()] if corte else texto_limpio  # se conserva solo la parte permanente
    candidatos = list(PATRON_ARTICULO.finditer(permanente))  # todos los posibles encabezados de artículo
    aceptados = []  # encabezados que pasan la validación secuencial
    ultimo = 0  # último número de artículo aceptado
    for m in candidatos:  # recorre los candidatos en orden
        numero = int(re.match(r"\d+", m.group(1)).group())  # parte numérica del identificador
        if ultimo <= numero <= ultimo + salto_maximo or (not aceptados and numero <= 3):  # debe seguir la numeración
            aceptados.append(m)  # se acepta el encabezado
            ultimo = max(ultimo, numero)  # se actualiza el último número
    articulos = []  # lista final de artículos
    capitulo_actual = ""  # capítulo vigente mientras se recorre el texto
    for i, m in enumerate(aceptados):  # recorre los encabezados aceptados
        fin = aceptados[i + 1].start() if i + 1 < len(aceptados) else len(permanente)  # fin del cuerpo
        cuerpo = permanente[m.end(): fin].strip()  # texto del artículo
        lineas = cuerpo.split("\n")  # separa en líneas para detectar encabezados al final
        encabezados = []  # encabezados de sección que pertenecen al artículo siguiente
        while lineas and (not lineas[-1].strip() or _es_encabezado(lineas[-1])):  # retira líneas finales de sección
            if lineas[-1].strip():  # si no es una línea vacía
                encabezados.insert(0, lineas[-1].strip())  # se guarda en orden original
            lineas.pop()  # se quita del cuerpo del artículo
        cuerpo = re.sub(r"\s*\n\s*", " ", "\n".join(lineas)).strip()  # une el texto en un solo párrafo continuo
        cuerpo = re.sub(r"\s{2,}", " ", cuerpo)  # elimina espacios dobles
        numero_txt = m.group(1).upper()  # identificador como texto (por ejemplo «86» o «22A»)
        numero = int(re.match(r"\d+", numero_txt).group())  # parte numérica
        articulos.append({  # registro del artículo
            "articulo": numero_txt,  # identificador del artículo
            "numero": numero,  # parte numérica para ordenar y filtrar
            "titulo": titulo_de(numero),  # Título oficial
            "capitulo": capitulo_actual,  # capítulo vigente al iniciar el artículo
            "texto": cuerpo,  # contenido normativo
        })  # cierre de la estructura
        esperando_nombre = False  # indica si la siguiente línea es el nombre de un capítulo
        for h in encabezados:  # los encabezados finales aplican al artículo siguiente
            if re.match(r"(?i)^CAP[IÍ]TULO\b", h):  # si es un capítulo
                capitulo_actual = h.rstrip(". ").capitalize()  # se actualiza el capítulo vigente
                esperando_nombre = True  # la próxima línea será el nombre del capítulo
            elif esperando_nombre:  # nombre del capítulo
                capitulo_actual = f"{capitulo_actual}. {h.capitalize()}"  # se completa «Capítulo 2. De los ...»
                esperando_nombre = False  # ya se consumió el nombre
            else:  # nombre de un nuevo Título (el Título sale del mapa oficial)
                capitulo_actual = ""  # al cambiar de Título se reinicia el capítulo
    return articulos  # devuelve los artículos


def diagnosticar(articulos: list[dict], esperados: int = 380) -> dict:  # función diagnosticar: Calcula indicadores de calidad de la ingesta para revisarlos en el…
    """Calcula indicadores de calidad de la ingesta para revisarlos en el cuaderno."""
    numeros = sorted({a["numero"] for a in articulos})  # números distintos encontrados
    faltantes = [n for n in range(1, esperados + 1) if n not in numeros]  # números sin artículo
    vacios = [a["articulo"] for a in articulos if len(a["texto"]) < 20]  # artículos con texto casi vacío
    return {  # resumen de calidad
        "total_registros": len(articulos),  # artículos (incluye sufijos como 22A)
        "numeros_distintos": len(numeros),  # números base distintos
        "faltantes": faltantes,  # números ausentes
        "vacios": vacios,  # artículos sospechosos
        "caracteres_totales": sum(len(a["texto"]) for a in articulos),  # tamaño del corpus
    }  # cierre de la estructura


def guardar_articulos(articulos: list[dict], ruta: Path) -> None:  # función guardar_articulos: Guarda los artículos en un archivo JSON Lines.
    """Guarda los artículos en un archivo JSON Lines."""
    ruta.parent.mkdir(parents=True, exist_ok=True)  # crea la carpeta si no existe
    with ruta.open("w", encoding="utf-8") as f:  # abre el archivo para escribir
        for a in articulos:  # recorre los artículos
            f.write(json.dumps(a, ensure_ascii=False) + "\n")  # una línea JSON por artículo


def cargar_articulos(ruta: Path) -> list[dict]:  # función cargar_articulos: Lee los artículos desde el archivo JSON Lines.
    """Lee los artículos desde el archivo JSON Lines."""
    with ruta.open(encoding="utf-8") as f:  # abre el archivo
        return [json.loads(linea) for linea in f if linea.strip()]  # una entrada por línea


def _cortar(texto: str, maximo: int, solape: int) -> list[str]:  # función _cortar: Divide un texto largo en ventanas, intentando cortar en un punto o…
    """Divide un texto largo en ventanas, intentando cortar en un punto o salto natural."""
    partes = []  # ventanas resultantes
    inicio = 0  # posición inicial de la ventana
    while inicio < len(texto):  # mientras quede texto por cubrir
        fin = min(inicio + maximo, len(texto))  # fin tentativo de la ventana
        if fin < len(texto):  # si no es la última ventana
            corte = max(texto.rfind(". ", inicio, fin), texto.rfind("; ", inicio, fin))  # último punto o punto y coma
            if corte > inicio + maximo // 2:  # solo si el corte no deja una ventana demasiado corta
                fin = corte + 1  # se corta después del signo
        partes.append(texto[inicio:fin].strip())  # guarda la ventana
        if fin >= len(texto):  # si ya se cubrió todo
            break  # termina
        inicio = max(fin - solape, inicio + 1)  # la siguiente ventana retrocede para solapar
    return partes  # devuelve las ventanas


def fragmentar(articulos: list[dict], maximo: int = 1200, solape: int = 150) -> list[dict]:  # función fragmentar: Crea los fragmentos indexables: un fragmento por artículo, o varias…
    """Crea los fragmentos indexables: un fragmento por artículo, o varias partes si es muy largo."""
    fragmentos = []  # lista de fragmentos
    for a in articulos:  # recorre los artículos
        partes = [a["texto"]] if len(a["texto"]) <= maximo else _cortar(a["texto"], maximo, solape)  # decide si dividir
        for j, parte in enumerate(partes, start=1):  # recorre las partes
            fragmentos.append({  # registro del fragmento
                "id": f"art{a['articulo']}-p{j}",  # identificador único
                "articulo": a["articulo"],  # artículo al que pertenece
                "numero": a["numero"],  # número base del artículo
                "parte": j,  # número de parte dentro del artículo
                "n_partes": len(partes),  # total de partes del artículo
                "titulo": a["titulo"],  # Título oficial
                "capitulo": a.get("capitulo", ""),  # capítulo
                "texto": parte,  # contenido del fragmento
            })  # cierre de la estructura
    return fragmentos  # devuelve los fragmentos
