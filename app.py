import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json

# ==========================================
# 1. CONFIGURAÇÕES E ESTILO
# ==========================================
st.set_page_config(page_title="OficinaPro 2.0", page_icon="🛠️", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_password=True)

# Segredos do Servidor (Configurar no Streamlit Cloud)
ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. GESTÃO DE DADOS
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, 
        cargo TEXT, nivel_acesso TEXT, senha_hash TEXT, primeiro_acesso INTEGER DEFAULT 1)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL, fornecedor TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_placa TEXT, 
        carro_ano TEXT, descricao_problema TEXT, pecas_sugeridas_mecanico TEXT, 
        id_mecanico TEXT, status_solicitacao TEXT DEFAULT 'Pendente',
        valor_total REAL DEFAULT 0.0, valor_comissao REAL DEFAULT 0.0)''')
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. AUTENTICAÇÃO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None})

if not st.session_state.logado:
    st.title("🔐 Login OficinaPro")
    user = st.text_input("E-mail")
    pw = st.text_input("Senha", type="password")
    
    if st.button("Aceder"):
        if user == ADMIN_USER and pw == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'nome': "Proprietário", 'primeiro_acesso': 0})
            st.rerun()
        else:
            conn = conectar(); cursor = conn.cursor()
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email FROM usuarios WHERE email=? AND senha_hash=?", (user, hash_senha(pw)))
            res = cursor.fetchone(); conn.close()
            if res:
                st.session_state.update({'logado': True, 'perfil': res[0], 'nome': res[1], 'primeiro_acesso': res[2], 'email_u': res[3]})
                st.rerun()
            else: st.error("Acesso negado.")

else:
    # --- TROCA DE SENHA OBRIGATÓRIA ---
    if st.session_state.get('primeiro_acesso') == 1:
        st.warning("🔒 Primeiro acesso: Altere a sua senha.")
        with st.form("nova_senha"):
            n_pw = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar"):
                if len(n_pw) >= 6:
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash=?, primeiro_acesso=0 WHERE email=?", (hash_senha(n_pw), st.session_state.email_u))
                    conn.commit(); conn.close()
                    st.session_state.primeiro_acesso = 0
                    st.success("Senha alterada!"); st.rerun()
    
    else:
        # --- MENU PRINCIPAL ---
        st.sidebar.title(f"👤 {st.session_state.nome}")
        aba = st.sidebar.radio("Navegação", ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"])

        if aba == "🏠 Início":
            st.header("Dashboard de Operações")
            c1, c2, c3 = st.columns(3)
            conn = conectar()
            pendentes = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status_solicitacao='Pendente'", conn).iloc[0,0]
            criticos = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
            c1.metric("O.S. Pendentes", pendentes)
            c2.metric("Alertas de Estoque", criticos, delta_color="inverse", delta=-criticos if criticos > 0 else 0)
            c3.metric("Status", "Online")
            conn.close()

        elif aba == "📋 Ordens de Serviço":
            st.subheader("Gestão de Ordens de Serviço")
            with st.expander("➕ Nova O.S."):
                with st.form("os_form"):
                    col1, col2 = st.columns(2)
                    mod = col1.text_input("Veículo"); pla = col2.text_input("Placa")
                    diag = st.text_area("Laudo Técnico")
                    if st.form_submit_button("Abrir Serviço"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO ordens_servico (carro_modelo, carro_placa, descricao_problema, id_mecanico) VALUES (?,?,?,?)", (mod, pla, diag, st.session_state.nome))
                        conn.commit(); conn.close(); st.success("Serviço aberto!")

            conn = conectar()
            df_os = pd.read_sql_query("SELECT id, carro_modelo, carro_placa, status_solicitacao FROM ordens_servico", conn)
            st.dataframe(df_os, use_container_width=True, hide_index=True)
            conn.close()

        elif aba == "📦 Estoque":
            st.header("Inventário")
            with st.expander("➕ Adicionar Peça"):
                with st.form("est_form"):
                    p = st.text_input("Peça"); q = st.number_input("Qtd", min_value=0); qm = st.number_input("Mínimo", min_value=1)
                    if st.form_submit_button("Salvar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO estoque (peca, quantidade, quantidade_minima) VALUES (?,?,?)", (p, q, qm))
                        conn.commit(); conn.close(); st.rerun()

            conn = conectar()
            df_est = pd.read_sql_query("SELECT peca, quantidade, quantidade_minima FROM estoque", conn)
            st.dataframe(df_est, use_container_width=True)
            conn.close()

        elif aba == "💰 Financeiro":
            if st.session_state.perfil in ["Admin", "Gerente"]:
                st.header("Relatórios Financeiros")
                conn = conectar()
                df_fin = pd.read_sql_query("SELECT valor_total, valor_comissao FROM ordens_servico", conn)
                total = df_fin['valor_total'].sum()
                st.metric("Receita Bruta Total", f"R$ {total:,.2f}")
                st.bar_chart(df_fin)
                conn.close()
            else: st.error("Acesso restrito.")

        elif aba == "⚙️ Administração":
            if st.session_state.perfil == "Admin":
                t1, t2, t3 = st.tabs(["Usuários", "Reset Senha", "Backup"])
                with t1:
                    with st.form("cad_u"):
                        n = st.text_input("Nome"); e = st.text_input("E-mail"); c = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                        if st.form_submit_button("Registar"):
                            conn = conectar(); cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)", (n, e, c, c, hash_senha("123456")))
                            conn.commit(); conn.close(); st.success("Senha padrão: 123456")
                with t3:
                    if os.path.exists('oficina_mecanica.db'):
                        with open('oficina_mecanica.db', 'rb') as f:
                            st.download_button("📥 Baixar Backup", f, file_name="backup.db")
            else: st.error("Acesso negado.")

        if st.sidebar.button("🚪 Sair"):
            st.session_state.update({'logado': False}); st.rerun()
