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
