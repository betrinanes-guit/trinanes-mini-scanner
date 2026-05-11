import streamlit as st
from google import genai

st.title("Teste Gemini")

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.write("Listando modelos disponíveis...")

try:
    for m in client.models.list():
        st.write(m.name)
except Exception as e:
    st.error("Erro ao listar modelos")
    st.code(str(e))