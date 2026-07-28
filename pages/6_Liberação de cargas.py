
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
            dep.numero_carga,
            lc.wb,
            lc.lote,
            lc.status,
            lc.solicitado_por,
            lc.solicitado_em
        FROM liberacao_cargas lc
        INNER JOIN deposito_operacao dep
            ON dep.id = lc.deposito_operacao_id
        ORDER BY lc.solicitado_em DESC
    """)

    dados = cur.fetchall()

    conn.close()

    return dados

def aprovar_liberacao(id_liberacao, usuario):
    conn = get_connection()
    cur = get_cursor(conn)

    try:
        cur.execute("""
            UPDATE liberacao_cargas
            SET
                status = 'APROVADO',
                aprovado_por = %s,
                aprovado_em = %s
            WHERE id = %s
        """, (
            usuario,
            agora(),
            id_liberacao
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def atualizar_liberacao(id_liberacao, wb, lote):
    conn = get_connection()
    cur = get_cursor(conn)

    try:
        cur.execute("""
            UPDATE liberacao_cargas
               SET wb=%s,
                   lote=%s
             WHERE id=%s
        """, (
            wb,
            lote,
            id_liberacao
        ))

        conn.commit()

    except:
        conn.rollback()
        raise

    finally:
        conn.close()

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

dias_filtro = st.slider(
    "Exibir registros dos últimos (dias)",
    min_value=1,
    max_value=365,
    value=30
)

dados = listar_pendentes()


if dados:

    df = pd.DataFrame(dados)

    df["solicitado_em"] = pd.to_datetime(df["solicitado_em"])

    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias_filtro)

    df = df[df["solicitado_em"] >= data_limite]

    df["solicitado_em"] = df["solicitado_em"].dt.strftime("%d/%m/%Y %H:%M")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Somente Classificador ou Admin podem alterar
    if user["papel"] in ["Classificador", "Admin"]:

        st.subheader("Aprovar solicitação")

        solicitacao = st.selectbox(
            "Selecione uma solicitação",
            dados,
            format_func=lambda x: (
                f'Carga {x["numero_carga"]} | '
                f'WB {x["wb"]} | '
                f'LOTE {x["lote"]}'
            )
        )

        if st.button("✅ Aprovar"):
            aprovar_liberacao(
                solicitacao["id"],
                user["nome_completo"]
            )
            st.success("Solicitação aprovada.")
            st.rerun()

else:
    st.info("Nenhuma solicitação encontrada.")

# ---------------------------------------------------------
# Edição
# ---------------------------------------------------------

if user["papel"] in ["Classificador", "Admin"] and dados:
    st.subheader("Editar solicitação")

    solicitacao_edicao = st.selectbox(
        "Selecione para editar",
        dados,
        key="editar",
        format_func=lambda x: (
            f'Carga {x["numero_carga"]} | '
            f'WB {x["wb"]} | '
            f'LOTE {x["lote"]}'
        )
    )

    novo_wb = st.text_input(
        "WB",
        value=solicitacao_edicao["wb"]
    )

    novo_lote = st.text_input(
        "LOTE",
        value=solicitacao_edicao["lote"]
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Salvar Alterações"):

            atualizar_liberacao(
                solicitacao_edicao["id"],
                novo_wb,
                novo_lote
            )

            st.success("Registro atualizado.")
            st.rerun()

