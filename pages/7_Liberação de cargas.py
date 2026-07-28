
import datetime
import streamlit as st
import pandas as pd

from database import init_db, get_connection, get_cursor, agora
from auth import exigir_papel, sidebar_usuario, usuario_logado

st.set_page_config(page_title="Liberação de cargas", page_icon="🚦", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Classificador")
sidebar_usuario()

st.title("🚦 Liberação de cargas")
st.caption("Atrelar pesagem e lotes ao número de carga.")

conn = get_connection()

# ---------------------------------------------------------
# Funções
# ---------------------------------------------------------

def listar_cargas():
    conn = get_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT
            id,
            numero_carga
        FROM deposito_operacao
        ORDER BY numero_carga
    """)

    cargas = cur.fetchall()

    conn.close()

    return cargas


def salvar_liberacao(
    deposito_operacao_id,
    wb,
    lote,
    usuario
):
    conn = get_connection()
    cur = get_cursor(conn)

    try:
        cur.execute("""
            INSERT INTO liberacao_cargas (
                deposito_operacao_id,
                wb,
                lote,
                status,
                solicitado_por,
                solicitado_em
            )
            VALUES (
                %s,
                %s,
                %s,
                'PENDENTE',
                %s,
                %s
            )
        """, (
            deposito_operacao_id,
            wb,
            lote,
            usuario,
            agora()
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def listar_pendentes():
    conn = get_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT
            lc.id,
            do.numero_carga,
            lc.wb,
            lc.lote,
            lc.status,
            lc.solicitado_por,
            lc.solicitado_em
        FROM liberacao_cargas lc
        INNER JOIN deposito_operacao do
            ON do.id = lc.deposito_operacao_id
        ORDER BY lc.solicitado_em DESC
    """)

    dados = cur.fetchall()

    conn.close()

    return dados

# ---------------------------------------------------------
# Cadastro
# ---------------------------------------------------------

st.subheader("Nova solicitação")

cargas = listar_cargas()

if cargas:

    carga = st.selectbox(
        "Número da carga",
        cargas,
        format_func=lambda x: x["numero_carga"]
    )

    col1, col2 = st.columns(2)

    with col1:
        wb = st.text_input("WB")

    with col2:
        lote = st.text_input("LOTE")

    if st.button("Salvar solicitação", type="primary"):

        if not wb.strip():
            st.error("Informe o WB.")
        elif not lote.strip():
            st.error("Informe o LOTE.")
        else:

            salvar_liberacao(
                deposito_operacao_id=carga["id"],
                wb=wb.strip(),
                lote=lote.strip(),
                usuario=user["nome_completo"]
            )

            st.success("Solicitação registrada com sucesso.")
            st.rerun()

else:
    st.info("Nenhuma carga encontrada.")

# ---------------------------------------------------------
# Pendências
# ---------------------------------------------------------

st.divider()

st.subheader("Solicitações registradas")

dados = listar_pendentes()

if dados:

    df = pd.DataFrame(dados)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("Nenhuma solicitação encontrada.")