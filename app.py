import os
import pymongo
import google.generativeai as genai
import streamlit as st
from datetime import datetime
import json

# =====================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y UI
# =====================================================================
st.set_page_config(page_title="SaaS Análisis Político", page_icon="🏛️", layout="centered")
st.title("🏛️ Analizador de Discursos Políticos con IA")
st.markdown("Plataforma para el análisis de sentimientos impulsada por Gemini y MongoDB.")

# =====================================================================
# 2. INICIALIZACIÓN DE VARIABLES DE ENTORNO Y SERVICIOS
# =====================================================================
# Usamos MONGO_URL tal como acordamos
MONGO_URL = os.getenv("MONGO_URL")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

@st.cache_resource
def init_services():
    """Inicializa conexiones a BD y API de forma eficiente para no recargar en cada interacción"""
    if not MONGO_URL or not GOOGLE_API_KEY:
        st.error("⚠️ Faltan variables de entorno críticas en el servidor (MONGO_URL o GEMINI_API_KEY).")
        st.stop()
        
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    client = pymongo.MongoClient(MONGO_URL)
    db = client["analisis_politico"]
    collection = db["discursos"]
    
    return model, collection

model, collection = init_services()

# =====================================================================
# 3. INTERFAZ DE USUARIO (El Formulario)
# =====================================================================
with st.form("speech_form"):
    politico = st.text_input("Nombre del Político", placeholder="Ej. Senador García")
    tema = st.text_input("Tema Principal", placeholder="Ej. Reforma Fiscal")
    texto_discurso = st.text_area("Texto del Discurso", height=200, placeholder="Pega aquí el discurso completo...")
    
    submitted = st.form_submit_button("Analizar Sentimiento 🚀")

# =====================================================================
# 4. LÓGICA DE PROCESAMIENTO
# =====================================================================
if submitted:
    if not politico or not tema or not texto_discurso:
        st.warning("Por favor, completa todos los campos antes de analizar.")
    else:
        with st.spinner('Analizando discurso con Inteligencia Artificial...'):
            prompt = f"""
            Analiza el siguiente discurso político. Determina el sentimiento general (Positivo, Negativo o Neutral), 
            un porcentaje de confianza (0-100%) y una breve justificación.
            Devuelve la respuesta ESTRICTAMENTE en este formato JSON válido:
            {{"sentimiento": "Valor", "confianza": 85, "justificacion": "Texto..."}}
            
            Discurso: "{texto_discurso}"
            """
            
            try:
                # 1. Llamada a Gemini
                response = model.generate_content(prompt)
                
                # Limpiamos posibles formatos de markdown que devuelve la API (ej. ```json ... ```)
                raw_json = response.text.replace('```json', '').replace('```', '').strip()
                resultado_json = json.loads(raw_json)
                
                # 2. Guardar en MongoDB
                documento = {
                    "politico": politico,
                    "tema": tema,
                    "texto": texto_discurso,
                    "analisis": resultado_json,
                    "fecha_analisis": datetime.utcnow()
                }
                collection.insert_one(documento)
                
                # 3. Mostrar Resultados en la UI
                st.success("¡Análisis completado y guardado exitosamente en MongoDB!")
                
                col1, col2 = st.columns(2)
                col1.metric("Sentimiento Detectado", resultado_json.get("sentimiento", "N/A"))
                col2.metric("Nivel de Confianza", f"{resultado_json.get('confianza', 0)}%")
                
                st.info(f"**Justificación:** {resultado_json.get('justificacion', 'No disponible')}")
                
            except Exception as e:
                st.error(f"❌ Ocurrió un error procesando el análisis: {str(e)}")