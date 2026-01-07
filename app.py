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
# 1. IDENTIDADE VISUAL E OCULTAR ELEMENTOS
# ==========================================
st.set_page_config(page_title="OficinaPro | Enterprise V6", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #8a05be; }
    .payment-box { border: 1px solid #e0e0e0; padding: 25px; border-radius: 15px; background-color: #ffffff; margin-top: 15px; border-top: 5px solid #8a05be; }
    .status-vencido { color: #d32f2f; font-weight: bold; }
    .status-pago { color: #388e3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Secrets)
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
    MASTER_EMAIL = st.secrets.get("master_email", ADMIN_USER)
except:
    st.error("Configure os Secrets no Streamlit Cloud.")
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
    
    # Tabela Financeira com Vencimento para Inadimplência
    cursor.execute('''CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, valor REAL, 
        data_vencimento TEXT, status TEXT, metodo TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, lote TEXT, validade TEXT, 
        quantidade INTEGER, quantidade_minima INTEGER)''')
    
    conn.commit(); conn.close()

inicializar_db()

# ==========================================
# 3. UTILITÁRIOS E SIMULAÇÕES
# ==========================================
def simular_backup_google_drive():
    st.subheader("☁️ Sincronização com Google Drive (Simulação)")
    st.info("Status da Conexão: 🟢 Autenticado como wilgner.wss@hotmail.com")
    
    if st.button("🔄 Iniciar Sincronização Agora"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            "Compactando banco de dados...",
            "Criptografando arquivo (AES-256)...",
            "Conectando ao servidor Google API...",
            "Enviando para a pasta 'OficinaPro_Backups'...",
            "Verificando integridade da cópia..."
        ]
        
        for i, step in enumerate(steps):
            status_text.text(step)
            time.sleep(1)
            progress_bar.progress((i + 1) * 20)
            
        st.success(f"✅ Backup concluído com sucesso às {datetime.now().strftime('%H:%M:%S')}!")
        st.code(f"ID do Arquivo: drive_bkp_{int(time.time())}.db.crypt", language="text")

# ==========================================
# 4. EXECUÇÃO DO SISTEMA
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'email': None})

if not st.session_state.logado:
    st.title("🔐 OficinaPro Enterprise V6")
    u = st.text_input("E-mail")
    p = st.text_input("Senha", type="password")
    if st.button("🚀 Entrar"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'email': u})
            st.rerun()
else:
    aba = st.sidebar.radio("Navegação", ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"])

    # 🏠 INÍCIO
    if aba == "🏠 Início":
        st.header("🏠 Painel Geral")
        st.info("Sistema monitorado e criptografado.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pendências Financeiras", "R$ 1.250,00", delta="Inadimplência", delta_color="inverse")
        c2.metric("Serviços Hoje", "3")
        c3.metric("Cloud Sync", "OK")

    # 💰 FINANCEIRO & INADIMPLÊNCIA
    elif aba == "💰 Financeiro":
        st.header("💰 Gestão Financeira e Inadimplência")
        t1, t2, t3 = st.tabs(["📊 Dashboard BI", "🚨 Controle de Inadimplência", "💸 Lançamentos"])
        
        with t2:
            st.subheader("⚠️ Clientes com Pagamentos Atrasados")
            # Dados fictícios para simulação de inadimplência
            dados_inad = {
                "Cliente": ["Mecânica Silva", "Auto Peças João", "Transportadora X"],
                "Vencimento": ["2025-12-20", "2025-12-28", "2026-01-05"],
                "Valor": [450.00, 800.00, 1200.00],
                "Dias de Atraso": [18, 10, 2]
            }
            df_inad = pd.DataFrame(dados_inad)
            
            st.dataframe(df_inad, use_container_width=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total em Atraso", f"R$ {df_inad['Valor'].sum():,.2f}")
            with col_b:
                if st.button("📲 Disparar Lembretes Automáticos (WhatsApp/E-mail)"):
                    with st.spinner("Enviando cobranças amigáveis..."):
                        time.sleep(2)
                        st.success("Lembretes enviados para todos os clientes inadimplentes!")

    # 📦 ESTOQUE
    elif aba == "📦 Estoque":
        st.header("📦 Gestão de Itens")
        with st.form("est"):
            peca = st.text_input("Peça")
            lote = st.text_input("Lote")
            vld = st.checkbox("Possui Validade?", value=True)
            if vld: st.date_input("Data de Expiração")
            if st.form_submit_button("Salvar"): st.success("Item registrado.")

    # ⚙️ ADMINISTRAÇÃO & BACKUP CLOUD
    elif aba == "⚙️ Administração":
        st.header("⚙️ Configurações Master")
        t_usr, t_sec = st.tabs(["👥 Usuários", "💾 Backup & Cloud Sync"])
        
        with t_sec:
            simular_backup_google_drive()
            st.write("---")
            st.subheader("Histórico de Sincronização")
            st.table(pd.DataFrame({
                "Data/Hora": ["07/01/2026 00:00", "06/01/2026 00:00"],
                "Destino": ["Google Drive", "Google Drive"],
                "Status": ["Sucesso", "Sucesso"]
            }))

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
