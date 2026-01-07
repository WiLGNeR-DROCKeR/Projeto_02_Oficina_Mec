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
            st.session_state.update({'logado': True, 'perfil': "Admin", 'nome': "Proprietário"})
            st.rerun()
        else:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email FROM usuarios WHERE email=? AND senha_hash=?", (u, hash_senha(p)))
            res = cursor.fetchone()
            conn.close()
            if res:
                st.session_state.update({'logado': True, 'perfil': res[0], 'nome': res[1], 'p_acesso': res[2], 'email_u': res[3]})
                st.rerun()
            else:
                st.error("Dados incorretos.")

else:
    # --- MENU LATERAL ---
    st.sidebar.markdown(f"### 🛠️ {st.session_state.perfil}")
    aba = st.sidebar.radio("Menu", ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"])

    # --- ABA FINANCEIRO ---
    if aba == "💰 Financeiro":
        st.header("💰 Inteligência Financeira e Lucratividade")
        
        if st.session_state.perfil in ["Admin", "Gerente"]:
            conn = conectar()
            df = pd.read_sql_query("SELECT valor_pecas, valor_mao_de_obra, valor_comissao, data FROM ordens_servico", conn)
            conn.close()

            if not df.empty:
                receita_bruta = df['valor_pecas'].sum() + df['valor_mao_de_obra'].sum()
                custo_pecas = df['valor_pecas'].sum()
                total_comissoes = df['valor_comissao'].sum()
                lucro_liquido = receita_bruta - custo_pecas - total_comissoes

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Receita Total", f"R$ {receita_bruta:,.2f}")
                m2.metric("Custo Peças", f"R$ {custo_pecas:,.2f}", delta="-Custo", delta_color="inverse")
                m3.metric("Comissões", f"R$ {total_comissoes:,.2f}", delta="-Custo", delta_color="inverse")
                m4.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", delta="Resultado Final")

                st.write("---")
                st.subheader("📊 Comparativo de Fluxo")
                chart_data = pd.DataFrame({
                    'Categoria': ['Receita Bruta', 'Custos (Peças + Comissões)', 'Lucro Real'],
                    'Valores (R$)': [receita_bruta, (custo_pecas + total_comissoes), lucro_liquido]
                })
                st.bar_chart(chart_data.set_index('Categoria'))

                st.subheader("📈 Distribuição Financeira")
                fig = px.pie(chart_data, names='Categoria', values='Valores (R$)', title="Proporção de Custos vs Lucro")
                st.plotly_chart(fig, use_container_width=True)

                st.download_button("📤 Exportar Financeiro CSV", df.to_csv(index=False), "financeiro.csv")
            else:
                st.info("Sem dados financeiros registrados.")
        else:
            st.error("Acesso restrito.")

    # --- ABA ORDENS DE SERVIÇO ---
    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Serviços")
        with st.expander("➕ Nova O.S. (Preenchimento Administrativo)"):
            with st.form("os_financeiro"):
                col1, col2 = st.columns(2)
                veiculo = col1.text_input("Veículo")
                placa = col2.text_input("Placa")
                v_pecas = col1.number_input("Valor total das Peças (R$)", min_value=0.0)
                v_servico = col2.number_input("Valor da Mão de Obra (R$)", min_value=0.0)
                comis = st.number_input("Comissão do Mecânico (R$)", min_value=0.0)
                
                submitted = st.form_submit_button("Finalizar e Lançar no Financeiro")
                if submitted:
                    conn = conectar()
                    cursor = conn.cursor()
                    cursor.execute("""INSERT INTO ordens_servico 
                        (carro_modelo, carro_placa, valor_pecas, valor_mao_de_obra, valor_comissao, id_mecanico) 
                        VALUES (?,?,?,?,?,?)""", (veiculo, placa, v_pecas, v_servico, comis, st.session_state.nome))
                    conn.commit()
                    conn.close()
                    st.success("Lançamento concluído!")

        conn = conectar()
        df_list = pd.read_sql_query("SELECT id, carro_modelo, carro_placa, valor_pecas + valor_mao_de_obra as Total FROM ordens_servico", conn)
        st.dataframe(df_list, use_container_width=True, hide_index=True)
        conn.close()

    # --- ABA ESTOQUE ---
    elif aba == "📦 Estoque":
        st.header("📦 Inventário")
        conn = conectar()
        df_estoque = pd.read_sql_query("SELECT * FROM estoque", conn)
        conn.close()
        if not df_estoque.empty:
            criticas = df_estoque[df_estoque['quantidade'] <= df_estoque['quantidade_minima']]
            if not criticas.empty:
                st.error("⚠️ Atenção: peças em linha vermelha!")
                st.dataframe(criticas, use_container_width=True)
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Nenhuma peça cadastrada.")

    # --- ABA ADMINISTRAÇÃO ---
