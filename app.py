import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime, date
import time
import base64

# ==========================================
# 1. IDENTIDADE VISUAL E CORREÇÃO DE INTERFACE
# ==========================================
st.set_page_config(page_title="OficinaPro | ERP Master", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    /* 1. OCULTAR ELEMENTOS NATIVOS (SHARE, DEPLOY, MENU 3 PONTOS) */
    .stAppDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { background: rgba(0,0,0,0) !important; }

    /* 2. FIX DO MENU HAMBÚRGUER (FORÇAR VISIBILIDADE DA SETA) */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        background-color: #8a05be !important; /* Roxo NuBank */
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        left: 0 !important;
        top: 10px !important;
        z-index: 1000000 !important;
        padding: 5px !important;
    }

    /* 3. ESTILIZAÇÃO PROFISSIONAL */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }
    
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
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
    }
    
    .pix-key { color: #8a05be; font-weight: bold; background: #f3e5f5; padding: 5px 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# Credenciais e Master Admin
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
        vencimento TEXT, status TEXT, metodo TEXT, categoria TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, lote TEXT, validade TEXT, 
        quantidade INTEGER, quantidade_minima INTEGER)''')
    
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. MÓDULOS: RECIBO, CHECKOUT E CLOUD
# ==========================================
def gerar_recibo_txt(cliente, valor, desc):
    recibo = f"""
    ========================================
             RECIBO DE PAGAMENTO
    ========================================
    DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    CLIENTE: {cliente}
    VALOR: R$ {valor:,.2f}
    DESCRIÇÃO: {desc}
    
    PAGAMENTO DESTINADO A: NuBank
    CHAVE PIX: wilgner.wss@hotmail.com
    ========================================
    """
    b64 = base64.b64encode(recibo.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="recibo_oficinapro.txt" style="color: #8a05be; font-weight: bold; text-decoration: none;">📄 Baixar Recibo de Pagamento</a>'

def gateway_pagamento(valor, descricao, cliente="Cliente"):
    st.markdown("<div class='payment-box'>", unsafe_allow_html=True)
    st.subheader("💳 Checkout Seguro OficinaPro")
    metodo = st.radio("Selecione o método:", ["Pix (NuBank)", "Cartão de Crédito"], horizontal=True)
    
    if "Pix" in metodo:
        c1, c2 = st.columns([1, 2])
        c1.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=wilgner.wss@hotmail.com")
        with c2:
            st.markdown(f"**Favorecido:** Wilgner (NuBank)")
            st.write(f"**Ag:** 0001 | **Conta:** 3548549-1")
            st.markdown(f"**Chave Pix:** <span class='pix-key'>wilgner.wss@hotmail.com</span>", unsafe_allow_html=True)
            st.write(f"**Valor Final:** R$ {valor:,.2f}")
            if st.button("✅ Confirmar Pagamento"):
                with st.spinner("Validando transação..."):
                    time.sleep(1.5)
                    st.success("Pagamento recebido com sucesso!")
                    st.markdown(gerar_recibo_txt(cliente, valor, descricao), unsafe_allow_html=True)
                    st.balloons()
    else:
        st.write("### Dados do Cartão")
        st.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
        if st.button("💳 Processar Cartão"):
            st.success("Transação aprovada!")
            st.markdown(gerar_recibo_txt(cliente, valor, descricao), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 4. EXECUÇÃO DA INTERFACE
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'email': None})

if not st.session_state.logado:
    st.title("🔐 OficinaPro Enterprise V6.2")
    u = st.text_input("E-mail de Acesso")
    p = st.text_input("Senha", type="password")
    if st.button("🚀 Acessar Sistema"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'email': u})
            st.rerun()
else:
    # SIDEBAR
    st.sidebar.markdown(f"### 👤 {st.session_state.perfil}")
    
    menu = ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    if st.session_state.email == MASTER_EMAIL:
        menu.append("👑 Gestão SaaS")
        
    aba = st.sidebar.radio("Navegação Principal", menu)

    # --- ABA INÍCIO ---
    if aba == "🏠 Início":
        st.header("🏠 Bem-vindo ao OficinaPro.")
        st.info("⬅️ Utilize o menu lateral
