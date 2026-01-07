import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date
import plotly.express as px
import pandas as pd

# ---------- Config ----------
st.set_page_config(page_title="Oficina Mecânica", layout="wide")
DB_PATH = "oficina.db"

# ---------- Helpers ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Usuários
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        senha_hash TEXT,
        papel TEXT CHECK(papel IN ('colaborador','gerente','admin')),
        ativo INTEGER DEFAULT 1
    )""")
    # Ordens de serviço
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        veiculo TEXT,
        placa TEXT,
        descricao TEXT,
        status TEXT,
        responsavel_id INTEGER,
        data_abertura TEXT,
        data_prevista TEXT,
        valor_bruto REAL,
        percentual_mecanico REAL DEFAULT 0.3,
        bonus REAL DEFAULT 0,
        progresso INTEGER DEFAULT 0
    )""")
    # Peças
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        sku TEXT UNIQUE,
        estoque_atual INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 0,
        preco_medio REAL DEFAULT 0
    )""")
    # Fornecedores
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cnpj TEXT,
        contato TEXT
    )""")
    # Cotações
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cotacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id INTEGER,
        peca_id INTEGER,
        preco REAL,
        data TEXT
    )""")
    conn.commit()
    # Seed admin
    cur.execute("SELECT COUNT(*) FROM users WHERE papel='admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (nome,email,senha_hash,papel) VALUES (?,?,?,?)",
                    ("Admin", "admin@oficina.local", hash_pwd("admin123"), "admin"))
        conn.commit()
    conn.close()

def login(email, pwd):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,nome,email,senha_hash,papel,ativo FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    if row and row[3] == hash_pwd(pwd) and row[5] == 1:
        return {"id": row[0], "nome": row[1], "email": row[2], "papel": row[4]}
    return None

def require_role(roles):
    user = st.session_state.get("user")
    return user and user["papel"] in roles

def alerta_linha_vermelha():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT nome, sku, estoque_atual, estoque_minimo FROM pecas")
    rows = cur.fetchall()
    conn.close()
    criticas = [r for r in rows if r[2] <= r[3]]
    if criticas:
        st.warning(f"Peças em linha vermelha: {len(criticas)}")
        st.table({"Nome": [r[0] for r in criticas],
                  "SKU": [r[1] for r in criticas],
                  "Estoque": [r[2] for r in criticas],
                  "Mínimo": [r[3] for r in criticas]})

# ---------- Init ----------
init_db()
if "user" not in st.session_state:
    st.session_state.user = None

# ---------- Sidebar ----------
st.sidebar.title("Oficina Mecânica")
if st.session_state.user:
    st.sidebar.success(f"Logado como {st.session_state.user['nome']} ({st.session_state.user['papel']})")
    page = st.sidebar.radio("Navegação", ["Dashboard", "Trabalhos", "Gestão", "Estoque", "Admin", "Sair"])
else:
    page = "Login"

# ---------- Pages ----------
# Login
if page == "Login":
    st.title("Acesso")
    email = st.text_input("Email")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = login(email, pwd)
        if user:
            st.session_state.user = user
            st.experimental_rerun()
        else:
            st.error("Credenciais inválidas ou usuário inativo.")

# Dashboard
elif page == "Dashboard":
    st.title("Painel Principal")
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM ordens_servico", conn)
    conn.close()
    col1, col2, col3 = st.columns(3)
    if not df.empty:
        df["ganho_mecanico"] = df["valor_bruto"] * df["percentual_mecanico"] + df["bonus"]
        df["ganho_empresa"] = df["valor_bruto"] - df["ganho_mecanico"]
        with col1:
            st.metric("Receita Empresa (total)", f"R$ {df['ganho_empresa'].sum():,.2f}")
        with col2:
            st.metric("Receita Mecânicos (total)", f"R$ {df['ganho_mecanico'].sum():,.2f}")
        with col3:
            status_counts = df["status"].value_counts()
            st.metric("O.S. abertas", int(status_counts.get("aberta", 0)))
        fig = px.bar(df, x="status", title="Status das Ordens de Serviço")
        st.plotly_chart(fig, use_container_width=True)
    else:
        with col1:
            st.metric("Receita Empresa (total)", "R$ 0,00")
        with col2:
            st.metric("Receita Mecânicos (total)", "R$ 0,00")
        with col3:
            st.metric("O.S. abertas", 0)
        st.info("Nenhuma O.S. cadastrada ainda.")
    st.divider()
    st.subheader("Alertas de estoque")
    alerta_linha_vermelha()

# Trabalhos
elif page == "Trabalhos":
    st.title("Trabalhos disponíveis")
    if not require_role(["colaborador", "gerente", "admin"]):
        st.error("Acesso negado.")
    else:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT id, cliente, veiculo, placa, descricao, status,
                              valor_bruto, percentual_mecanico, bonus, progresso
                       FROM ordens_servico ORDER BY id DESC""")
        rows = cur.fetchall()
        conn.close()
        if not rows:
            st.info("Nenhuma O.S. disponível.")
        for r in rows:
            os_id, cliente, veiculo, placa, desc, status, valor, perc, bonus, prog = r
            ganho_mec = (valor or 0) * (perc or 0) + (bonus or 0)
            with st.expander(f"O.S. {os_id} - {cliente} ({veiculo}/{placa})"):
                st.write(f"Descrição: {desc}")
                st.write(f"Status: {status}")
                st.success(f"Ganho do mecânico: R$ {ganho_mec:,.2f}")
                st.progress(int(prog))
                novo_prog = st.slider(f"Atualizar progresso da O.S. {os_id}", 0, 100, int(prog), key=f"prog_{os_id}")
                if st.button(f"Salvar progresso {os_id}"):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE ordens_servico SET progresso=? WHERE id=?", (novo_prog, os_id))
                    conn.commit()
                    conn.close()
                    st.success("Progresso atualizado.")

# Gestão
elif page == "Gestão":
    st.title("Gestão de Ordens de Serviço")
    if not require_role(["gerente", "admin"]):
        st.error("Acesso negado.")
    else:
        st.subheader("Abertura rápida de O.S.")
        with st.form("nova_os"):
            cliente = st.text_input("Cliente")
            veiculo = st.text_input("Veículo")
            placa = st.text_input("Placa")
            descricao = st.text_area("Descrição do problema")
            valor_bruto = st.number_input("Valor bruto do serviço", min_value=0.0, step=0.01)
            percentual = st.slider("Percentual mecânico", 0.0, 1.0, 0.3)
            bonus = st.number_input("Bônus (opcional)", min_value=0.0, step=0.01)
            data_prevista = st.date_input("Data prevista", value=date.today())
