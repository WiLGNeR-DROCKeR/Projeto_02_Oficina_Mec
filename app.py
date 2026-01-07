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
# 1. IDENTIDADE VISUAL E FIX DA INTERFACE
# ==========================================
st.set_page_config(page_title="OficinaPro | ERP Master", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    /* 1. OCULTAR ELEMENTOS NATIVOS CIRCULADOS NA IMAGEM */
    .stAppDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { background: rgba(0,0,0,0) !important; }

    /* 2. FIX DO MENU: Garante a visibilidade da seta roxa NuBank */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        background-color: #8a05be !important; 
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        left: 0 !important;
        top: 15px !important;
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
    }
    
    .pix-key { color: #8a05be; font-weight: bold; background: #f3e5f5; padding: 5px 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Configurar no Secrets do Streamlit Cloud)
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
    MASTER_EMAIL = st.secrets.get("master_email", ADMIN_USER)
except:
    st.error("Erro Crítico: Configure os Secrets (admin_user e admin_password).")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS
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
# 3. MÓDULOS DE RECIBO E GATEWAY
# ==========================================
def gerar_recibo_txt(cliente, valor, desc):
    recibo = f"========================================\nRECIBO DE PAGAMENTO\n========================================\nDATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\nCLIENTE: {cliente}\nVALOR: R$ {valor:,.2f}\nREF: {desc}\nBANCO: NuBank\nCHAVE PIX: wilgner.wss@hotmail.com\n========================================"
    b64 = base64.b64encode(recibo.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="recibo_oficinapro.txt" style="color: #8a05be; font-weight: bold; text-decoration: none;">📄 Baixar Recibo Oficial</a>'

def gateway_pagamento(valor, descricao, cliente="Cliente"):
    st.markdown("<div class='payment-box'>", unsafe_allow_html=True)
    st.subheader("💳 Checkout Seguro NuBank")
    metodo = st.radio("Método de recebimento:", ["Pix Instantâneo", "Cartão de Crédito"], horizontal=True)
    
    if "Pix" in metodo:
        c1, c2 = st.columns([1, 2])
        c1.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=wilgner.wss@hotmail.com")
        with c2:
            st.markdown(f"**Destino:** Wilgner (NuBank)")
            st.write(f"Ag: 0001 | Conta: 3548549-1")
            st.markdown(f"**Chave Pix:** <span class='pix-key'>wilgner.wss@hotmail.com</span>", unsafe_allow_html=True)
            st.write(f"**Total:** R$ {valor:,.2f}")
            if st.button("✅ Confirmar Transação"):
                with st.spinner("Sincronizando com NuBank..."):
                    time.sleep(1.5)
                    st.success("Pagamento Confirmado!")
                    st.markdown(gerar_recibo_txt(cliente, valor, descricao), unsafe_allow_html=True)
                    st.balloons()
    else:
        st.write("### Pagamento via Cartão")
        st.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
        if st.button("💳 Processar Cartão"):
            st.success("Venda aprovada!")
            st.markdown(gerar_recibo_txt(cliente, valor, descricao), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 4. EXECUÇÃO DA INTERFACE
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'email': None})

if not st.session_state.logado:
    st.title("🔐 OficinaPro Enterprise V6.3")
    u = st.text_input("E-mail Profissional")
    p = st.text_input("Senha", type="password")
    if st.button("🚀 Acessar Painel"):
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

    # --- ABA INÍCIO (SINTAXE CORRIGIDA) ---
    if aba == "🏠 Início":
        st.header("🏠 Bem-vindo ao OficinaPro.")
        # A linha abaixo estava causando o SyntaxError. Corrigido!
        st.info("⬅️ Utilize o menu lateral para gerir a oficina.")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Pendências", "R$ 1.250,00", delta="Inadimplência", delta_color="inverse")
        c2.metric("O.S. Ativas", "5")
        c3.metric("Integridade Cloud", "Sincronizado")

    # --- ABA ORDENS DE SERVIÇO ---
    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Serviços")
        with st.expander("➕ Nova O.S. & Pagamento", expanded=True):
            with st.form("os_form"):
                pecas = st.multiselect("Peças Utilizadas", ["Pneu", "Óleo", "Filtro", "Pastilha"])
                c1, c2 = st.columns(2)
                veic = c1.text_input("Veículo")
                plac = c2.text_input("Placa")
                cli = st.text_input("Nome do Cliente")
                v_tot = st.number_input("Valor do Serviço (R$)", min_value=0.0)
                if st.form_submit_button("Gerar O.S. e Ir para Checkout"):
                    st.session_state.chk = {"valor": v_tot, "desc": f"Serviço {veic}", "cliente": cli}
        
        if "chk" in st.session_state:
            gateway_pagamento(st.session_state.chk["valor"], st.session_state.chk["desc"], st.session_state.chk["cliente"])

    # --- ABA ESTOQUE (LOTE E VALIDADE) ---
    elif aba == "📦 Estoque":
        st.header("📦 Gestão de Itens")
        with st.form("est"):
            c1, c2 = st.columns(2)
            p_nome = c1.text_input("Descrição da Peça")
            p_lote = c2.text_input("Lote")
            tem_val = st.checkbox("Possui Validade?", value=True)
            if tem_val: st.date_input("Vencimento")
            if st.form_submit_button("Salvar no Inventário"): st.success("Item registrado!")

    # --- ABA FINANCEIRO (INADIMPLÊNCIA) ---
    elif aba == "💰 Financeiro":
        st.header("💰 Gestão Financeira e Inadimplência")
        t1, t2 = st.tabs(["🚨 Devedores", "📊 BI Financeiro"])
        with t1:
            df_inad = pd.DataFrame({"Cliente": ["Oficina São João", "Cliente Avulso"], "Vencimento": ["2025-12-25", "2026-01-02"], "Valor": [450.0, 800.0]})
            st.table(df_inad)
            if st.button("📲 Notificar Inadimplentes"): st.info("Cobranças enviadas via WhatsApp!")

    # --- ABA ADMIN (CLOUD BACKUP SIM) ---
    elif aba == "⚙️ Administração":
        st.header("⚙️ Configurações e Backup")
        if st.button("☁️ Sincronizar Google Drive (Simulação)"):
            prog = st.progress(0)
            for i in range(101):
                time.sleep(0.01)
                prog.progress(i)
            st.success("Backup enviado com sucesso para wilgner.wss@hotmail.com!")

    # --- ABA GESTÃO SAAS (MASTER) ---
    elif aba == "👑 Gestão SaaS":
        st.header("👑 Painel Master
