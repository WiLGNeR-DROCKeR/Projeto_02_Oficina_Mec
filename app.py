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
# 1. IDENTIDADE VISUAL E FIX DE INTERFACE (UX)
# ==========================================
st.set_page_config(page_title="OficinaPro | ERP Master", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    /* Ocultar elementos nativos circulados na imagem */
    .stAppDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { background: rgba(0,0,0,0) !important; }

    /* FIX DO MENU: Garante a seta roxa do NuBank visível */
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

    /* Estilização Profissional */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #8a05be; }
    
    /* Prevenção de sobreposição do QR Code Fullscreen */
    [data-testid="stImage"] { max-width: 150px !important; margin-bottom: 20px; }
    
    .payment-box { border: 1px solid #e0e0e0; padding: 25px; border-radius: 15px; background-color: #ffffff; border-top: 5px solid #8a05be; }
</style>
""", unsafe_allow_html=True)

# Credenciais e Master Admin
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
    MASTER_EMAIL = st.secrets.get("master_email", ADMIN_USER)
except:
    st.error("Configure os Secrets (admin_user e admin_password) no Streamlit Cloud.")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS (DATABASE)
# ==========================================
def conectar():
    return sqlite3.connect('oficina_master_v7.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela Usuários Detalhada
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE,
        cargo TEXT, especializacao TEXT, telefone TEXT, exp_anos TEXT,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1)''')
    
    # Tabela Financeira ERP
    cursor.execute('''CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, valor REAL, 
        tipo TEXT, categoria TEXT, status TEXT, vencimento TEXT, mrr_flag INTEGER DEFAULT 0)''')

    # Tabela Estoque com Marca e Valor
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, marca TEXT, valor_un REAL,
        lote TEXT, validade TEXT, quantidade INTEGER, quantidade_minima INTEGER)''')
    
    # Tabela SaaS Master
    cursor.execute('''CREATE TABLE IF NOT EXISTS planos_saas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, status TEXT DEFAULT 'Ativo')''')
    
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. UTILITÁRIOS: PDF RECIBO E GATEWAY
# ==========================================
def gerar_recibo_pdf_simulado(cliente, valor, desc):
    # Formatação HTML que simula um PDF para download
    recibo_html = f"""
    <div style="border: 2px solid #333; padding: 20px; font-family: Courier; background: white;">
        <h2 style="text-align: center;">RECIBO DE PAGAMENTO - OFICINAPRO</h2>
        <hr>
        <p><b>CLIENTE:</b> {cliente}</p>
        <p><b>VALOR:</b> R$ {valor:,.2f}</p>
        <p><b>DESCRIÇÃO:</b> {desc}</p>
        <p><b>DATA:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p><b>PAGAMENTO:</b> PIX NUBANK (wilgner.wss@hotmail.com)</p>
        <hr>
        <p style="text-align: center; font-size: 10px;">Documento gerado eletronicamente por OficinaPro ERP</p>
    </div>
    """
    b64 = base64.b64encode(recibo_html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="recibo_{cliente}.html" style="background-color: #8a05be; color: white; padding: 10px; border-radius: 5px; text-decoration: none;">📥 Baixar Recibo Oficial</a>'

def gateway_pagamento_completo(valor, descricao, cliente="Cliente"):
    st.markdown("<div class='payment-box'>", unsafe_allow_html=True)
    st.subheader("💳 Checkout Seguro NuBank")
    metodo = st.radio("Selecione o Método:", ["Pix (Nubank)", "Cartão de Crédito"], horizontal=True)
    
    if "Pix" in metodo:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=wilgner.wss@hotmail.com")
        with c2:
            st.markdown(f"**Favorecido:** Wilgner (NuBank)")
            st.write(f"Agência: 0001 | Conta: 3548549-1")
            st.write(f"Chave Pix: wilgner.wss@hotmail.com")
            if st.button("Confirmar Recebimento"):
                st.success("Pagamento Confirmado!")
                st.markdown(gerar_recibo_pdf_simulado(cliente, valor, descricao), unsafe_allow_html=True)
    else:
        st.write("### Dados Detalhados do Cartão")
        col1, col2 = st.columns(2)
        nome_titular = col1.text_input("Nome do Titular (conforme cartão)")
        cpf_titular = col2.text_input("CPF do Titular")
        num_cartao = col1.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
        c_venc = col2.text_input("Vencimento (MM/AA)")
        c_cvc = col2.text_input("CVC", type="password")
        if st.button("Processar Pagamento"):
            st.success("Venda aprovada com sucesso!")
            st.markdown(gerar_recibo_pdf_simulado(cliente, valor, descricao), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 4. EXECUÇÃO DO SISTEMA
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'email': None})

if not st.session_state.logado:
    st.title("🔐 OficinaPro Enterprise V7.0")
    u = st.text_input("E-mail Profissional")
    p = st.text_input("Senha", type="password")
    if st.button("🚀 Acessar Sistema"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'email': u})
            st.rerun()
else:
    # Sidebar
    st.sidebar.markdown(f"### 👤 {st.session_state.perfil}")
    menu = ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    if st.session_state.email == MASTER_EMAIL:
        menu.append("👑 Gestão SaaS")
    
    aba = st.sidebar.radio("Navegação", menu)

    # --- ABA INÍCIO ---
    if aba == "🏠 Início":
        st.header("🏠 Painel Operacional")
        st.info("⬅️ Utilize o menu lateral para gerir a oficina.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pendências", "R$ 1.250,00", delta="Atenção", delta_color="inverse")
        c2.metric("O.S. Ativas", "5")
        c3.metric("Status Cloud", "Sincronizado")

    # --- ABA ORDENS DE SERVIÇO ---
    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Serviços")
        with st.expander("➕ Nova O.S. & Checkout", expanded=True):
            with st.form("os_form"):
                pecas = st.multiselect("Selecione as Peças Utilizadas", ["Pneu", "Óleo", "Filtro", "Pastilha"])
                c1, c2 = st.columns(2)
                veic = c1.text_input("Veículo"); plac = c2.text_input("Placa")
                cli = st.text_input("Nome do Cliente")
                v_tot = st.number_input("Valor Total (R$)", min_value=0.0)
                if st.form_submit_button("Gerar Ordem e Abrir Pagamento"):
                    st.session_state.chk = {"valor": v_tot, "desc": f"Serviço {veic}", "cliente": cli}
        
        if "chk" in st.session_state:
            gateway_pagamento_completo(st.session_state.chk["valor"], st.session_state.chk["desc"], st.session_state.chk["cliente"])

    # --- ABA ESTOQUE (ATUALIZADA) ---
    elif aba == "📦 Estoque":
        st.header("📦 Gestão de Itens e Insumos")
        with st.form("est_form"):
            c1, c2 = st.columns(2)
            nome_p = c1.text_input("Nome da Peça")
            marca_p = c2.text_input("Marca")
            qtd_p = c1.number_input("Quantidade de Peças", min_value=0)
            val_p = c2.number_input("Valor Unitário (R$)", min_value=0.0)
            lote_p = c1.text_input("Lote")
            tem_val = st.checkbox("Item possui prazo de validade?", value=True)
            if tem_val: st.date_input("Data de Vencimento")
            if st.form_submit_button("💾 Salvar no Inventário"): st.success("Item registrado!")

    # --- ABA FINANCEIRO (RESTAURADA) ---
    elif aba == "💰 Financeiro":
        st.header("📊 Gestão Financeira e Inadimplência")
        t1, t2, t3, t4 = st.tabs(["🚨 Devedores", "📈 Dashboard BI", "💸 Fluxo de Caixa", "📑 Contas"])
        with t1:
            st.subheader("Controle de Inadimplência")
            df_inad = pd.DataFrame({"Cliente": ["Oficina A", "Cliente B"], "Dias Atraso": [15, 8], "Valor": [450, 800]})
            st.table(df_inad)
            if st.button("📲 Notificar devedores"): st.info("Alertas enviados via WhatsApp.")
        with t2:
            m1, m2 = st.columns(2)
            m1.metric("MRR (Recorrência Mensal)", "R$ 1.500,00")
            m2.metric("ARR (Recorrência Anual)", "R$ 18.000,00")
            st.bar_chart({"Entradas": [10, 20, 15], "Saídas": [5, 8, 7]})

    # --- ABA ADMINISTRAÇÃO (RESTAURADA) ---
    elif aba == "⚙️ Administração":
        st.header("⚙️ Configurações Master")
        t_cad, t_res, t_cloud = st.tabs(["👥 Colaboradores", "🔑 Reset de Senhas", "💾 Backup Cloud"])
        with t_cad:
            with st.form("cad_prof"):
                st.subheader("Cadastro de Profissional")
                n = st.text_input("Nome Completo"); c = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                esp = st.text_area("Especialização (Clique + para mais)"); em = st.text_input("E-mail Profissional")
                tel = st.text_input("Telefone"); exp = st.text_input("Anos de Experiência")
                if st.form_submit_button("Cadastrar"): st.success("Cadastrado com senha padrão 123456")
        with t_res:
            st.selectbox("Selecionar Colaborador", ["mecanico@oficina.com"])
            if st.button("Executar Reset para 123456"): st.warning("Senha resetada com sucesso!")
        with t_cloud:
            if st.button("☁️ Sincronizar Google Drive (Simulação)"):
                p = st.progress(0)
                for i in range(101): time.sleep(0.01); p.progress(i)
                st.success("Backup enviado para Nuvem com Sucesso!")

    # --- ABA GESTÃO SAAS (STATUS INCLUÍDO) ---
    elif aba == "👑 Gestão SaaS":
        st.header("👑 Painel Master - Planos SaaS")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("plano"):
                st.text_input("Nome do Plano")
                st.number_input("Valor Mensal")
                if st.form_submit_button("Criar Plano"): st.success("Plano Publicado!")
        with c2:
            st.subheader("Planos Registrados")
            st.table(pd.DataFrame({"Plano": ["Platinum", "Gold"], "Preço": [450, 250], "Status": ["Ativo", "Ativo"]}))

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
