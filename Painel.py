import streamlit as st
import json
import os
import time

# Configuração da Página
st.set_page_config(
    page_title="DJ Bot Controller",
    page_icon="🎵",
    layout="centered"
)

FILE_STATUS = "status.json"
FILE_COMANDOS = "comandos.json"

# Função para enviar comando pro bot
def enviar_comando(action, data=None):
    cmd = {"action": action, "data": data}
    with open(FILE_COMANDOS, "w", encoding="utf-8") as f:
        json.dump(cmd, f)
    st.toast(f"Comando '{action}' enviado!", icon="🚀")
    time.sleep(1) # Espera o bot ler

# Função para ler status
def ler_status():
    if not os.path.exists(FILE_STATUS):
        return {"tocando": "Bot Offline", "fila": [], "status": "Desconectado"}
    try:
        with open(FILE_STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"tocando": "Atualizando...", "fila": [], "status": "..."}

# --- INTERFACE ---

st.title("🎛️ Painel do DJ Bot")

# Auto-refresh a cada 2 segundos para ver a música mudar
if st.button("🔄 Atualizar Status"):
    st.rerun()

dados = ler_status()

# Seção: O que está tocando
st.header("🎵 Tocando Agora")
col1, col2 = st.columns([3, 1])

with col1:
    st.info(f"**{dados['tocando']}**")
    st.caption(f"Status: {dados['status']}")

with col2:
    if st.button("⏭️ Pular", use_container_width=True):
        enviar_comando("skip")
        st.rerun()

# Seção: Adicionar Música
st.divider()
st.header("🔎 Adicionar Música")

with st.form("add_music_form"):
    url = st.text_input("Nome da música ou Link do YouTube")
    submitted = st.form_submit_button("Tocar 🔈")
    
    if submitted and url:
        enviar_comando("add", url)
        st.success(f"Adicionado à fila: {url}")

# Seção: Fila
st.divider()
st.header(f"📜 Fila de Espera ({len(dados['fila'])})")

if len(dados['fila']) > 0:
    for i, musica in enumerate(dados['fila']):
        st.text(f"{i+1}. {musica}")
else:
    st.write("_A fila está vazia._")

# Botão de Pânico
st.divider()
if st.button("🛑 PARAR TUDO (Desconectar)", type="primary"):
    enviar_comando("stop")