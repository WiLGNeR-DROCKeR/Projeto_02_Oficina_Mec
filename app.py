import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import plotly.express as px

# ==========================================
# 1. CONFIGURAÇÕES E IDENTIDADE VISUAL
# ==========================================
st.set_page_config(page_title="OficinaPro | Inteligência de Negócio", page_icon="💰", layout="wide")

# CSS para cards financeiros profissionais
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. BANCO DE DADOS (DATABASE)
# ==========================================
def conectar():
    """Sempre abre uma nova conexão para evitar erros de concorrência no Streamlit Cloud."""
    return sqlite3.connect('oficina_mecanica.db', check_same_thread=False)

def inicializar_db():
    conn = conectar()
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cargo TEXT,
        nivel_acesso TEXT,
        senha_hash TEXT,
        primeiro_acesso INTEGER DEFAULT 1
    )
    """)
    
    # Tabela de estoque
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca TEXT,
        quantidade INTEGER,
        quantidade_minima INTEGER,
        valor_compra REAL
    )
    """)
    
    # Tabela de ordens de serviço
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carro_modelo TEXT,
        carro_placa TEXT,
        id_mecanico TEXT,
        status_solicitacao TEXT DEFAULT 'Pendente',
        valor_pecas REAL DEFAULT 0.0,
        valor_mao_de_obra REAL DEFAULT 0.0,
        valor_comissao REAL DEFAULT 0.0,
        data TEXT DEFAULT CURRENT_DATE
    )
    """)
    
    conn.commit()
    conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. LÓGICA DE ACESSO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None})

if not st.session_state.logado:
    st.title("🔐 Login OficinaPro")
    u = st.text_input("E-mail")
    p = st.text_input("Senha", type="password")
    if st.button("Aceder"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update
