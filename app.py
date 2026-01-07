import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os

# ==========================================
# 1. CONFIGURAÇÕES E IDENTIDADE VISUAL
# ==========================================
st.set_page_config(page_title="OficinaPro | Inteligência de Negócio", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. BANCO DE DADOS (DATABASE)
# ==========================================
def conectar():
    # Nome atualizado conforme sua correção para evitar erros de esquema
    return sqlite3.connect('oficina_mecanica_V2.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela de usuários com controle de primeiro acesso
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, 
        cargo TEXT, nivel_acesso TEXT, senha_hash TEXT, primeiro_acesso INTEGER DEFAULT 1)''')
    
    # Tabela de estoque
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL)''')

    # Tabela de OS completa com campos financeiros
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_placa TEXT, 
        id_mecanico TEXT, status_solicitacao TEXT DEFAULT 'Pendente',
        valor_pecas REAL DEFAULT 0.0, valor_mao_de_obra REAL DEFAULT 0.0, 
        valor_comissao REAL DEFAULT 0.0)''')
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. LÓGICA DE ACESSO E SEGURANÇA
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None})

if not st.session_state.logado:
    st.title("🔐 Login OficinaPro")
    u = st.text_input("E-mail"); p = st.text_input("Senha", type="password")
    if st.button("Aceder"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'nome': "Proprietário", 'p_acesso': 0})
            st.rerun()
        else:
            conn = conectar(); cursor = conn.cursor()
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email FROM usuarios WHERE email=? AND senha_hash=?", (u, hash_senha(p)))
            res = cursor.fetchone(); conn.close()
            if res:
                st.session_state.update({'logado': True, 'perfil': res[0], 'nome': res[1], 'p_acesso': res[2], 'email_u': res[3]})
                st.rerun()
            else: st.error("Dados incorretos.")

else:
    # --- TROCA DE SENHA OBRIGATÓRIA ---
    if st.session_state.get('p_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🔒 Alteração de Senha Obrigatória")
        st.info("Primeiro acesso detectado. Por favor, escolha uma senha segura.")
        with st.form("form_nova_senha"):
            n_senha = st.text_input("Nova Senha", type="password")
            c_senha = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                if n_senha == c_senha and len(n_senha) >= 6:
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 0 WHERE email = ?", 
                                   (hash_senha(n_senha), st.session_state.email_u))
                    conn.commit(); conn.close()
                    st.session_state.p_acesso = 0
                    st.success("Senha atualizada! Entrando..."); st.rerun()
                else: st.error("Senhas inválidas ou curtas (min 6 carac).")
    
    else:
        # --- MENU LATERAL ---
        st.sidebar.markdown(f"### 🛠️ {st.session_state.perfil}")
        aba = st.sidebar.radio("Menu", ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"])

        # 🏠 INÍCIO
        if aba == "🏠 Início":
            st.header(f"Olá, {st.session_state.nome}!")
            c1, c2, c3 = st.columns(3)
            conn = conectar()
            pendentes = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status_solicitacao='Pendente'", conn).iloc[0,0]
            alertas = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
            conn.close()
            c1.metric("Serviços Pendentes", pendentes)
            c2.metric("Alertas de Estoque", alertas, delta_color="inverse", delta=-alertas if alertas > 0 else 0)
            c3.metric("Sistema", "Online")

        # 💰 FINANCEIRO
        elif aba == "💰 Financeiro":
            st.header("💰 Inteligência Financeira")
            if st.session_state.perfil in ["Admin", "Gerente"]:
                conn = conectar()
                df = pd.read_sql_query("SELECT valor_pecas, valor_mao_de_obra, valor_comissao FROM ordens_servico", conn)
                conn.close()
                if not df.empty:
                    receita = df['valor_pecas'].sum() + df['valor_mao_de_obra'].sum()
                    lucro = receita - df['valor_pecas'].sum() - df['valor_comissao'].sum()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Receita Bruta", f"R$ {receita:,.2f}")
                    m2.metric("Comissões", f"R$ {df['valor_comissao'].sum():,.2f}", delta_color="inverse")
                    m3.metric("Lucro Líquido", f"R$ {lucro:,.2f}")
                    st.bar_chart(df)
                else: st.info("Sem dados financeiros.")

        # 📋 ORDENS DE SERVIÇO
        elif aba == "📋 Ordens de Serviço":
            st.header("📋 Gestão de Serviços")
            with st.expander("➕ Lançar Nova O.S. Financeira"):
                with st.form("os_fin"):
                    col1, col2 = st.columns(2)
                    v_mod = col1.text_input("Veículo"); v_pla = col2.text_input("Placa")
                    v_p = col1.number_input("Total Peças (R$)", min_value=0.0)
                    v_m = col2.number_input("Mão de Obra (R$)", min_value=0.0)
                    com = st.number_input("Comissão (R$)", min_value=0.0)
                    if st.form_submit_button("Lançar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO ordens_servico (carro_modelo, carro_placa, valor_pecas, valor_mao_de_obra, valor_comissao, id_mecanico) VALUES (?,?,?,?,?,?)",
                                       (v_mod, v_pla, v_p, v_m, com, st.session_state.nome))
                        conn.commit(); conn.close(); st.success("Lançado!")
            conn = conectar()
            df_os = pd.read_sql_query("SELECT id, carro_modelo, carro_placa, (valor_pecas + valor_mao_de_obra) as Total FROM ordens_servico", conn)
            st.dataframe(df_os, use_container_width=True, hide_index=True); conn.close()

        # 📦 ESTOQUE
        elif aba == "📦 Estoque":
            st.header("📦 Inventário")
            with st.expander("➕ Cadastrar Peça"):
                with st.form("est"):
                    n = st.text_input("Peça"); q = st.number_input("Qtd", min_value=0); m = st.number_input("Mín", min_value=1)
                    if st.form_submit_button("Salvar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO estoque (peca, quantidade, quantidade_minima) VALUES (?,?,?)", (n, q, m))
                        conn.commit(); conn.close(); st.success("Salvo!"); st.rerun()

        # ⚙️ ADMINISTRAÇÃO
        elif aba == "⚙️ Administração":
            if st.session_state.perfil == "Admin":
                st.header("⚙️ Ferramentas Master")
                t1, t2, t3 = st.tabs(["👥 Colaboradores", "🔑 Reset", "💾 Backup"])
                with t1:
                    with st.form("u"):
                        n = st.text_input("Nome"); e = st.text_input("E-mail"); c = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                        if st.form_submit_button("Cadastrar"):
                            conn = conectar(); cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)", (n, e, c, c, hash_senha("123456")))
                                conn.commit(); st.success("Cadastrado! Senha padrão: 123456")
                            except: st.error("E-mail já existe.")
                            finally: conn.close()
                with t2:
                    conn = conectar(); usrs = pd.read_sql_query("SELECT email FROM usuarios", conn); conn.close()
                    target = st.selectbox("E-mail para Reset", usrs['email']) if not usrs.empty else None
                    if st.button("Resetar Senha") and target:
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET senha_hash=?, primeiro_acesso=1 WHERE email=?", (hash_senha("123456"), target))
                        conn.commit(); conn.close(); st.warning(f"Senha de {target} resetada!")
                with t3:
                    if os.path.exists('oficina_mecanica_V2.db'):
                        with open('oficina_mecanica_V2.db', 'rb') as f:
                            st.download_button("📥 Baixar Backup", f, file_name="backup_oficina.db")
            else: st.error("Acesso restrito.")

        if st.sidebar.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()
