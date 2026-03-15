import sqlite3

def conectar():
    return sqlite3.connect("farmacia.db")

def criar_tabelas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT UNIQUE,
        senha TEXT,
        tipo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        categoria TEXT,
        preco_compra REAL,
        preco_venda REAL,
        quantidade INTEGER,
        validade TEXT
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE usuario='admin'")

    if cursor.fetchone():

        cursor.execute("""
        INSERT INTO usuarios (nome,usuario,senha,tipo)
        VALUES ('Administrador','Estanislau','112233','admin')
        """)

    conn.commit()
    conn.close()