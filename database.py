
"""
Módulo de acesso ao banco de dados (PostgreSQL / Supabase) do sistema de Gestão de Depósito de Cacau.
"""

import hashlib
import datetime
import streamlit as st
import psycopg2
import psycopg2.extras

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DO SUPABASE
# ─────────────────────────────────────────────

DB_CONFIG = {
    "host": st.secrets["postgres"]["host"],
    "database": st.secrets["postgres"]["database"],
    "user": st.secrets["postgres"]["user"],
    "password": st.secrets["postgres"]["password"],
    "port": st.secrets["postgres"]["port"],
}


def get_connection():
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        port=DB_CONFIG["port"],
        sslmode="require"
    )
    conn.autocommit = False
    return conn


def get_cursor(conn):
    """Retorna um cursor que devolve dicionários (como sqlite3.Row)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def init_db():
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome_completo TEXT NOT NULL,
                papel TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
            )
        """)
    
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config_listas (
                id SERIAL PRIMARY KEY,
                tipo TEXT NOT NULL,
                valor TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                UNIQUE(tipo, valor)
            )
        """)
    
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programacoes (
                id SERIAL PRIMARY KEY,
                horario TEXT NOT NULL,
                fornecedor TEXT NOT NULL,
                deposito TEXT NOT NULL,
                qtd_sacos INTEGER NOT NULL,
                tipo_contrato TEXT NOT NULL,
                tipo_cacau TEXT NOT NULL,
                criado_por TEXT,
                criado_em TEXT
            )
        """)
    
        cur.execute("""
            CREATE TABLE IF NOT EXISTS balanca (
                id SERIAL PRIMARY KEY,
                programacao_id INTEGER NOT NULL UNIQUE REFERENCES programacoes(id),
                wb TEXT UNIQUE NOT NULL,
                nota_fiscal TEXT,
                peso_bruto REAL,
                peso_tara REAL,
                peso_liquido REAL,
                data_pesagem_bruto TEXT,
                data_pesagem_tara TEXT,
                operador TEXT
            )
        """)
    
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deposito_operacao (
                id SERIAL PRIMARY KEY,
                balanca_id INTEGER NOT NULL UNIQUE REFERENCES balanca(id),
                numero_carga TEXT NOT NULL,
                data_inicio_descarga TEXT,
                data_fim_descarga TEXT,
                peso_balancinha REAL,
                peso_liquido REAL,
                peso_duplo REAL,
                peso_po REAL,
                qtd_sacos_amostrados INTEGER,
                residuo NUMERIC GENERATED ALWAYS AS (
                    (peso_balancinha + peso_po) * 100.0 / NULLIF(qtd_sacos_amostrados * 60, 0)
                ) STORED,
                operador TEXT
            )
        """)
    
        cur.execute("""
            CREATE TABLE IF NOT EXISTS classificacao (
                id SERIAL PRIMARY KEY,
                deposito_operacao_id INTEGER NOT NULL UNIQUE REFERENCES deposito_operacao(id),
                umidade REAL,
                fumaca REAL,
                ardosia REAL,
                violeta REAL,
                mofo_interno REAL,
                mofo_externo REAL,
                bean_count REAL,
                achatado REAL,
                ffa REAL,
                teor_casca REAL,
                infestado INTEGER,
                germinado REAL,
                tipo_cacau TEXT,
                classificador TEXT,
                data_classificacao TEXT
            )
        """)

        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(str(e))
        raise

    # --- seed inicial ---
    cur.execute("SELECT COUNT(*) AS c FROM usuarios")
    if cur.fetchone()["c"] == 0:
        usuarios_padrao = [
            ("admin", "admin123", "Administrador(a)", "Admin"),
            ("programacao", "123456", "Usuário Programação", "Programação"),
            ("balanca", "123456", "Usuário Balança", "Operador de Balança"),
            ("deposito", "123456", "Usuário Depósito", "Operador de Depósito"),
            ("classificador", "123456", "Usuário Classificador", "Classificador"),
        ]
        for username, senha, nome, papel in usuarios_padrao:
            cur.execute(
                "INSERT INTO usuarios (username, senha_hash, nome_completo, papel) VALUES (%s,%s,%s,%s)",
                (username, hash_senha(senha), nome, papel),
            )

    cur.execute("SELECT COUNT(*) AS c FROM config_listas")
    if cur.fetchone()["c"] == 0:
        listas_padrao = [
            ("fornecedor", "Fazenda Boa Esperança"),
            ("fornecedor", "Fazenda Santa Rita"),
            ("fornecedor", "Cooperativa Cacau Sul da Bahia"),
            ("deposito", "Depósito 01 - Itabuna"),
            ("deposito", "Depósito 02 - Ilhéus"),
            ("tipo_contrato", "RPF"),
            ("tipo_contrato", "TIPO1"),
            ("tipo_contrato", "RF"),
            ("tipo_cacau", "CVN"),
            ("tipo_cacau", "EUDR"),
        ]
        for tipo, valor in listas_padrao:
            cur.execute(
                "INSERT INTO config_listas (tipo, valor) VALUES (%s,%s)", (tipo, valor)
            )

    conn.commit()


# ---------------------------------------------------------------------------
# Helpers genéricos
# ---------------------------------------------------------------------------

def agora() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_lista(tipo: str, apenas_ativos: bool = True):
    conn = get_connection()
    cur = get_cursor(conn)
    if apenas_ativos:
        cur.execute(
            "SELECT valor FROM config_listas WHERE tipo=%s AND ativo=1 ORDER BY valor",
            (tipo,),
        )
        return [row["valor"] for row in cur.fetchall()]
    else:
        cur.execute(
            "SELECT valor, ativo FROM config_listas WHERE tipo=%s ORDER BY valor", (tipo,)
        )
        return [dict(row) for row in cur.fetchall()]


def autenticar(username: str, senha: str):
    conn = get_connection()
    cur = get_cursor(conn)
    cur.execute(
        "SELECT * FROM usuarios WHERE username=%s AND ativo=1", (username.strip(),)
    )
    row = cur.fetchone()
    if row and row["senha_hash"] == hash_senha(senha):
        return dict(row)
    return None

