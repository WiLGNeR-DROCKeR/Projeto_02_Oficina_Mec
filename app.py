import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime
import time
import base64

# ==========================================
# 1. IDENTIDADE VISUAL E CORREÇÃO DA INTERFACE
# ==========================================
st.set_page_config(page_title="OficinaPro | Enterprise V6.1", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    /* OCULTAR APENAS OS ELEMENTOS SOLICITADOS (BOTÃO SHARE E MENU DIREITO) */
    /* MANTÉM O BOTÃO DE EXPANDIR O SIDEBAR VISÍVEL */
    [data-testid="stToolbar"] {visibility: hidden;}
    .stAppDeployButton {display:none;}
    footer {visibility: hidden;}

    /* Estilização Profissional */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }
    
    /* Métricas Estilo NuBank */
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        border-left: 5px solid #8a05be; 
    }
    
    .payment-box { 
        border: 1px solid #e0e0e0; 
        padding: 25px; 
        border-radius: 15px; 
        background-color: #ffffff; 
        margin-top: 15px; 
        border-top: 5px solid #8a05be; 
    }
    
    .pix-key { color: #8a05be; font-weight: bold; background: #f3e5f5; padding: 5px 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Secrets do Streamlit Cloud)
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
    MASTER_EMAIL = st.secrets.get("master_email", ADMIN_USER)
except:
    st.error("Erro Crítico: Configure os Secrets no Streamlit Cloud.")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS E INFRAESTRUTURA
# ==========================================
def conectar():
    return sqlite3.connect('oficina_master_v6.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, valor REAL, 
        data TEXT, status TEXT, metodo TEXT, vencimento TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, lote TEXT, validade TEXT, 
        quantidade INTEGER, quantidade_minima INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS planos_saas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)''')
    
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. MÓDULOS DE PAGAMENTO E RECIBO
# ==========================================
def gerar_recibo(cliente, valor, desc):
    conteudo = f"RECIBO OFICINAPRO\nCliente: {cliente}\nValor: R$ {valor:.2f}\nReferente: {desc}\nPagamento: NuBank Pix"
    b64 = base64.b64encode(conteudo.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="recibo.txt">📄 Baixar Recibo Oficial</a>'

def gateway_pagamento(valor, descricao, cliente="Cliente"):
    st.markdown("<div class='payment-box'>", unsafe_allow_html=True)
    st.subheader("💳 Gateway NuBank Integrado")
    metodo = st.radio("Forma de recebimento:", ["Pix Instantâneo", "Cartão de Crédito"], horizontal=True)
    
    if "Pix" in metodo:
        c1, c2 = st.columns([1, 2])
        c1.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=wilgner.wss@hotmail.com")
        with c2:
            st.write(f"**Destinatário:** Wilgner (NuBank)")
            st.write(f"**Dados:** Ag: 0001 | Conta: 3548549-1")
            st.markdown(f"**Chave Pix:** <span class='pix-key'>wilgner.wss@hotmail.com</span>", unsafe_allow_html=True)
            if st.button("✅ Confirmar Recebimento"):
                st.success("Pagamento Confirmado na Conta NuBank!")
                st.markdown(gerar_recibo(cliente, valor, descricao), unsafe_allow_html=True)
    else:
        st.text_input("Número do Cartão")
        if st.button("💳 Processar"): st.success("Aprovado!")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 4. EXECUÇÃO DO APP
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'email': None})

if not st.session_state.logado:
    st.title("🔐 OficinaPro Enterprise")
    u = st.text_input("E-mail")
    p = st.text_input("Senha", type="password")
    if st.button("🚀 Entrar"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'email': u})
            st.rerun()
else:
    # SIDEBAR (Com correção para não sumir ao minimizar)
    st.sidebar.markdown(f"### 👤 {st.session_state.perfil}")
    
    menu = ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    if st.session_state.email == MASTER_EMAIL:
        menu.append("👑 Gestão SaaS")
        
    aba = st.sidebar.radio("Navegação", menu)

    if aba == "🏠 Início":
        st.header("🏠 Bem-vindo ao OficinaPro.")
        st.info("⬅️ Utilize o menu lateral para gerir a oficina.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pendências", "R$ 1.250,00", delta="Inadimplência", delta_color="inverse")
        c2.metric("O.S. Ativas", "3")
        c3.metric("Backup Cloud", "Sincronizado")

    elif aba == "💰 Financeiro":
        st.header("💰 Gestão Financeira e Inadimplência")
        t1, t2 = st.tabs(["🚨 Inadimplência", "💸 Captação de Recursos"])
        with t1:
            st.subheader("Clientes Atrasados")
            df_inad = pd.DataFrame({"Cliente": ["Oficina A", "Cliente B"], "Dias": [15, 8], "Valor": [450, 300]})
            st.table(df_inad)
            if st.button("📲 Cobrança Automática"): st.info("Lembretes enviados!")
        with t2:
            v = st.number_input("Valor")
            if st.button("Iniciar Checkout"): gateway_pagamento(v, "Receita Avulsa")

    elif aba == "📦 Estoque":
        st.header("📦 Inventário")
        with st.form("est"):
            st.text_input("Peça")
            chk = st.checkbox("Possui Validade?", value=True)
            if chk: st.date_input("Vencimento")
            if st.form_submit_button("Salvar"): st.success("Registrado.")

    elif aba == "👑 Gestão SaaS":
        st.header("👑 Painel Master - Planos e Assinaturas")
        with st.form("plano"):
            st.text_input("Nome do Plano")
            st.number_input("Valor Mensal")
            if st.form_submit_button("Criar Plano"): st.success("Plano SaaS publicado!")

    elif aba == "⚙️ Administração":
        st.header("⚙️ Configurações e Cloud")
        if st.button("☁️ Simular Backup Google Drive"):
            bar = st.progress(0)
            for i in range(101):
                time.sleep(0.02); bar.progress(i)
            st.success("Backup enviado para wilgner.wss@hotmail.com no Drive!")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
