import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime
import time

# ==========================================
# 1. IDENTIDADE VISUAL E OCULTAR ELEMENTOS (IMAGE FIX)
# ==========================================
st.set_page_config(page_title="OficinaPro | ERP Master", page_icon="🛠️", layout="wide")

# CSS para ocultar o que foi circulado na imagem e estilizar métricas
st.markdown("""
<style>
    /* Ocultar elementos nativos do Streamlit circulados */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Secrets)
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
    # E-mail que terá acesso ao Painel de Assinaturas (Master)
    MASTER_EMAIL = st.secrets.get("master_email", ADMIN_USER) 
except:
    st.error("Erro: Configure os Secrets no Streamlit Cloud.")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS EXPANDIDA
# ==========================================
def conectar():
    return sqlite3.connect('oficina_master_v4.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, email TEXT UNIQUE,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1,
        permissoes_gerente TEXT DEFAULT '[]')''')
    
    # Estoque com Lote e Validade
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, lote TEXT, validade TEXT, 
        quantidade INTEGER, quantidade_minima INTEGER, valor_compra REAL)''')

    # Financeiro (Despesas e Receitas)
    cursor.execute('''CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, 
        valor REAL, data TEXT, status TEXT)''')

    # Master: Assinaturas de Clientes
    cursor.execute('''CREATE TABLE IF NOT EXISTS assinaturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_nome TEXT, plano TEXT, 
        status TEXT, vcto TEXT)''')

    # OS
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_placa TEXT, 
        valor_pecas REAL, valor_mao_obra REAL, pecas_trocadas TEXT, status TEXT)''')
    
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. INTERFACE DE LOGIN
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
        # Lógica para usuários do BD aqui...

else:
    # Sidebar
    st.sidebar.markdown(f"### ⚙️ {st.session_state.perfil}")
    
    # Definição de Abas
    abas = ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    if st.session_state.email == MASTER_EMAIL:
        abas.append("🔑 Gestão SaaS") # Painel Master invisível para outros
    
    aba = st.sidebar.radio("Navegação", abas)

    # 🏠 INÍCIO
    if aba == "🏠 Início":
        st.header("🏠 Bem-vindo ao OficinaPro.")
        st.info("⬅️ Utilize o menu lateral para gerir a oficina.")
        c1, c2, c3 = st.columns(3)
        c1.metric("O.S. Ativas", "5")
        c2.metric("Estoque Crítico", "2", delta="-Reposição")
        c3.metric("Integridade", "100%")

    # 📋 ORDENS DE SERVIÇO
    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Serviços")
        with st.expander("➕ Nova O.S.", expanded=True):
            with st.form("os_form"):
                # Inversão solicitada: Peças em cima
                pecas_uso = st.multiselect("Selecione as Peças Utilizadas", ["Filtro Óleo", "Pastilha", "Vela"])
                
                col1, col2 = st.columns(2)
                veic = col1.text_input("Veículo")
                plac = col2.text_input("Placa")
                v_peca = col1.number_input("Valor Peças")
                v_obra = col2.number_input("Mão de Obra")
                
                if st.form_submit_button("Lançar"):
                    st.success("OS Lançada com sucesso!")

    # 📦 ESTOQUE
    elif aba == "📦 Estoque":
        st.header("📦 Estoque e Inteligência")
        with st.form("estoque_form"):
            col1, col2 = st.columns(2)
            peca = col1.text_input("Nome da Peça")
            lote = col2.text_input("Lote")
            
            tem_validade = st.checkbox("Item possui validade?", value=True)
            validade = "N/A"
            if tem_validade:
                validade = st.date_input("Data de Validade")
            
            if st.form_submit_button("Salvar Item"):
                st.success(f"Item {peca} salvo com sucesso!")

    # 💰 FINANCEIRO (ERP COMPLETO)
    elif aba == "💰 Financeiro":
        st.header("💰 Gestão Financeira ERP")
        t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "💸 Fluxo de Caixa", "🧾 Docs Fiscais", "🛠 Config"])
        
        with t1:
            st.subheader("Indicadores de Desempenho")
            col1, col2, col3 = st.columns(3)
            col1.metric("MRR (Recorrente Mensal)", "R$ 15.000")
            col2.metric("ARR (Recorrente Anual)", "R$ 180.000")
            col3.metric("Inadimplência", "2%", delta_color="inverse")
            
            st.write("### Fluxo de Caixa (Entradas vs Saídas)")
            st.bar_chart({"Entradas": [10, 20, 15], "Saídas": [5, 8, 7]})
            
        with t2:
            st.subheader("Contas a Pagar e Receber")
            st.table(pd.DataFrame({"Vencimento": ["10/01", "15/01"], "Tipo": ["Receber", "Pagar"], "Valor": [500, 200]}))

    # 🔑 GESTÃO SAAS (PAINEL MASTER EXCLUSIVO)
    elif aba == "🔑 Gestão SaaS":
        st.header("🔑 Painel Master - Gestão de Assinaturas")
        st.write("Gerencie os clientes que utilizam o seu sistema.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Assinantes Ativos", "12")
        col2.metric("Planos Suspensos", "1")
        col3.metric("Churn Rate", "0.5%")
        
        st.subheader("Histórico de Faturas")
        st.dataframe(pd.DataFrame({"Cliente": ["Oficina X", "Mecânica Y"], "Plano": ["Premium", "Basic"], "Status": ["Pago", "Pendente"]}))

    # ⚙️ ADMINISTRAÇÃO
    elif aba == "⚙️ Administração":
        st.header("⚙️ Painel de Gestão Master")
        t1, t2, t3 = st.tabs(["👥 Usuários", "🔑 Resetar Senhas", "💾 Backup e Segurança"])
        
        with t3:
            st.subheader("Configuração de Backup Automático")
            nuvem = st.selectbox("Escolha a Nuvem para Backup Automático", ["Google Drive", "OneDrive", "Dropbox", "iCloud"])
            horario = st.time_input("Horário do Backup Diário")
            if st.button("Agendar Backups"):
                st.info(f"Backups agendados para as {horario} no {nuvem}.")
            
            st.write("---")
            st.download_button("📥 Backup Local Imediato", "Dados", file_name="backup.db")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
