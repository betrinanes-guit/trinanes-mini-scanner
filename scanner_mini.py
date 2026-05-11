import json
import re
import io
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(
    page_title="TRINANES AI GARAGE VISION",
    page_icon="📸",
    layout="centered"
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #1f2937 0%, #0b0f17 45%, #05070c 100%);
    color: white;
}

.main-card, .result-card {
    background: linear-gradient(145deg, #111827, #1f2937);
    padding: 24px;
    border-radius: 24px;
    border: 1px solid #374151;
    box-shadow: 0 14px 35px rgba(0,0,0,.35);
    margin-top: 18px;
}

.info-card {
    background: #0f172a;
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid #334155;
    margin: 8px 0;
}

.big-title {
    text-align: center;
    font-size: 34px;
    font-weight: 900;
    margin-bottom: 4px;
}

.subtitle {
    text-align: center;
    color: #cbd5e1;
    margin-bottom: 22px;
}

.badge {
    display: inline-block;
    background: #f97316;
    color: #111827;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 800;
    margin-bottom: 10px;
}

h1, h2, h3 {
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">📸 TRINANES AI GARAGE VISION</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Scanner inteligente para blister, mini solto, expositor e coleção.</div>',
    unsafe_allow_html=True
)

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception:
    st.error("Erro: GEMINI_API_KEY não encontrada nos Secrets do Streamlit.")
    st.stop()

st.markdown('<div class="main-card">', unsafe_allow_html=True)

modo_analise = st.selectbox(
    "Tipo de análise",
    [
        "🚗 Mini solto",
        "📦 Blister frente e verso",
        "🖼️ Expositor / coleção",
        "🔍 Modo automático"
    ]
)

opcao = st.radio(
    "Como quer enviar a imagem?",
    ["📷 Usar câmera", "🖼️ Enviar foto"],
    horizontal=True
)

foto_1 = None
foto_2 = None
foto_3 = None

if opcao == "📷 Usar câmera":
    foto_1 = st.camera_input("Foto principal")
    if modo_analise == "📦 Blister frente e verso":
        foto_2 = st.camera_input("Foto do verso do blister")
    elif modo_analise in ["🖼️ Expositor / coleção", "🔍 Modo automático"]:
        foto_2 = st.camera_input("Foto extra opcional")
else:
    foto_1 = st.file_uploader("Foto principal", type=["jpg", "jpeg", "png", "webp"])
    if modo_analise == "📦 Blister frente e verso":
        foto_2 = st.file_uploader("Foto do verso do blister", type=["jpg", "jpeg", "png", "webp"])
    elif modo_analise in ["🖼️ Expositor / coleção", "🔍 Modo automático"]:
        foto_2 = st.file_uploader("Foto extra opcional", type=["jpg", "jpeg", "png", "webp"])
        foto_3 = st.file_uploader("Mais uma foto opcional", type=["jpg", "jpeg", "png", "webp"])

st.markdown("</div>", unsafe_allow_html=True)


def preparar_imagem_para_gemini(arquivo):
    if arquivo is None:
        return None

    try:
        imagem = Image.open(arquivo)

        if imagem.mode != "RGB":
            imagem = imagem.convert("RGB")

        imagem.thumbnail((1024, 1024))

        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)

        return types.Part.from_bytes(
            data=buffer.getvalue(),
            mime_type="image/jpeg"
        )

    except Exception as e:
        st.error(f"Erro ao preparar imagem: {e}")
        return None


def limpar_json(texto):
    texto = texto.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        texto = match.group(0)

    return json.loads(texto)


def montar_prompt(modo):
    return f"""
Você é especialista profissional em miniaturas diecast 1:64:
Hot Wheels, Mini GT, Kaido House, Matchbox, M2 Machines, GreenLight, Tarmac Works, Inno64, Johnny Lightning e similares.

Tipo de análise solicitado pelo usuário:
{modo}

As imagens podem conter:
- apenas o mini solto
- blister completo
- frente do blister
- verso do blister
- expositor
- vários minis juntos
- coleção inteira

Sua missão:
Identificar o máximo possível SEM inventar dados.

Retorne APENAS JSON válido, sem texto antes e sem texto depois.

{{
  "tipo_imagem_detectada": "",
  "modelo_detectado": "",
  "fabricante_detectado": "",
  "marca_linha": "",
  "possivel_serie": "",
  "series_index": "",
  "sku": "",
  "ano_lancamento": "",
  "possivel_raridade": "",
  "escala": "",
  "casting": "",
  "cor_principal": "",
  "cor_base": "",
  "cor_vidro": "",
  "cor_interior": "",
  "tipo_roda": "",
  "pais_origem": "",
  "designer": "",
  "valor_estimado_brasil": "",
  "nivel_confianca": "",
  "detalhes_visuais": "",
  "alerta_colecao": "",
  "observacoes": "",
  "itens_detectados": []
}}

Regras obrigatórias:
- Nunca invente SKU, ano, designer ou série.
- Se não tiver certeza, use "Não identificado".
- Para raridade, use apenas:
  "Comum", "TH", "STH", "Premium", "RLC", "Chase", "Especial", "Limitado", "Não identificado".
- O valor estimado deve ser em reais, aproximado, e com faixa. Exemplo: "R$ 80 a R$ 150".
- Se for mini solto, priorize modelo, fabricante provável, cor, rodas, decals e confiança.
- Se for blister, tente ler SKU, série, ano e informações impressas.
- Se for expositor/coleção, preencha itens_detectados com uma lista simples dos minis encontrados.
- nivel_confianca deve ser percentual, exemplo: "72%".
- alerta_colecao deve dizer se parece item comum, raro, premium, chase ou item que merece pesquisa manual.
"""


if st.button("🔥 Analisar mini", use_container_width=True):
    if not foto_1 and not foto_2 and not foto_3:
        st.error("Envie pelo menos uma foto.")
    else:
        with st.spinner("Analisando com IA..."):
            imagens = []

            for foto in [foto_1, foto_2, foto_3]:
                imagem_pronta = preparar_imagem_para_gemini(foto)
                if imagem_pronta:
                    imagens.append(imagem_pronta)

            if not imagens:
                st.error("Nenhuma imagem válida foi encontrada. Tente tirar outra foto.")
                st.stop()

            prompt = montar_prompt(modo_analise)

            try:
                resposta = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt] + imagens,
                    config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json"
                    }
                )

                texto = resposta.text.strip()

            except Exception as e:
                st.error("Erro ao consultar a IA.")
                st.info("Possíveis causas: limite da API, chave inválida, billing desativado ou imagem muito pesada.")
                st.code(str(e))
                st.stop()

            try:
                dados = limpar_json(texto)

                st.success("Mini analisado com sucesso!")

                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown('<span class="badge">AI GARAGE RESULT</span>', unsafe_allow_html=True)

                st.subheader("🚗 Resultado principal")

                campos_principais = [
                    "modelo_detectado",
                    "fabricante_detectado",
                    "marca_linha",
                    "possivel_serie",
                    "possivel_raridade",
                    "valor_estimado_brasil",
                    "nivel_confianca",
                    "alerta_colecao"
                ]

                for campo in campos_principais:
                    valor = dados.get(campo, "Não identificado")
                    st.markdown(
                        f'<div class="info-card"><b>{campo.replace("_", " ").title()}:</b> {valor}</div>',
                        unsafe_allow_html=True
                    )

                with st.expander("📋 Ver ficha completa"):
                    for chave, valor in dados.items():
                        if chave != "itens_detectados":
                            st.write(f"**{chave.replace('_', ' ').title()}:** {valor}")

                itens = dados.get("itens_detectados", [])
                if itens:
                    with st.expander("🖼️ Itens detectados no expositor/coleção"):
                        for item in itens:
                            st.write(item)

                st.markdown("</div>", unsafe_allow_html=True)

                st.download_button(
                    "⬇️ Baixar JSON do mini",
                    data=json.dumps(dados, ensure_ascii=False, indent=2),
                    file_name="mini_scanner_resultado.json",
                    mime="application/json",
                    use_container_width=True
                )

            except Exception:
                st.warning("A IA respondeu, mas não veio em JSON perfeito. Resultado bruto:")
                st.write(texto)