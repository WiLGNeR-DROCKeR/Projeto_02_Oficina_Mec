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
@st.cache_resource
def conectar():
    return sqlite3.connect('oficina_mecanica.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela de usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, 
        cargo TEXT, nivel_acesso TEXT, senha_hash TEXT, primeiro_acesso INTEGER DEFAULT 1)''')
    
    # Tabela de estoque
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER
