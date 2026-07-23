
import datetime
import streamlit as st
import pandas as pd

from database import init_db, get_connection, get_cursor, get_lista, agora
from auth import exigir_papel, sidebar_usuario, usuario_logado

st.set_page_config(page_title="Programação", page_icon="📅", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Programação")
sidebar_usuario()

st.title("📅 Programação de Recebimento")
st.caption("Cadastro e edição de agendamentos de recebimento de cacau nos depósitos.")

fornecedores = get_lista("fornecedor")
depositos = get_lista("deposito")
tipos_contrato = get_lista("tipo_contrato")
tipos_cacau = get_lista("tipo_cacau")

if not fornecedores or not depositos or not tipos_contrato or not tipos_cacau:
    st.warning(
        "Alguma lista configurável (fornecedor, depósito, tipo de contrato ou tipo de "
        "cacau) está vazia. Peça a um Admin para cadastrar em ⚙️ Admin."
    )

# ─────────────────────────────────────────────
# FORMULÁRIO DE INSERÇÃO
# ─────────────────────────────────────────────
with st.expander("➕ Nova Programação", expanded=True):
    with st.form("form_programacao", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_agendamento = st.date_input("Data do agendamento", format="DD/MM/YYYY", value=datetime.date.today())
            hora_agendamento = st.time_input("Horário do agendamento", value=datetime.time(8, 0))
            fornecedor = st.selectbox("Fornecedor", fornecedores, key="novo_forn") if fornecedores else st.text_input("Fornecedor")
            deposito = st.selectbox("Depósito", depositos, key="novo_dep") if depositos else st.text_input("Depósito")
        with col2:
            qtd_sacos = st.number_input("Quantidade de sacos", min_value=1, step=1)
            tipo_contrato = st.selectbox("Tipo de contrato", tipos_contrato, key="novo_tc") if tipos_contrato else st.text_input("Tipo de contrato")
            tipo_cacau = st.selectbox("Tipo de cacau", tipos_cacau, key="novo_tca") if tipos_cacau else st.text_input("Tipo de cacau")

        enviado = st.form_submit_button("➕ Adicionar programação", use_container_width=True)

        if enviado:
            horario = datetime.datetime.combine(data_agendamento, hora_agendamento)
            conn = get_connection()
            cur = get_cursor(conn)
            cur.execute(
                """INSERT INTO programacoes
                   (horario, fornecedor, deposito, qtd_sacos, tipo_contrato, tipo_cacau, criado_por, criado_em)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    horario.strftime("%Y-%m-%d %H:%M:%S"),
                    fornecedor,
                    deposito,
                    int(qtd_sacos),
                    tipo_contrato,
                    tipo_cacau,
                    user["username"],
                    agora(),
                ),
            )
            conn.commit()
            st.success("Programação adicionada com sucesso!")
            st.rerun()

st.markdown("---")

# ─────────────────────────────────────────────
# FILTROS POR DATA E DEPÓSITO
# ─────────────────────────────────────────────
st.subheader("📋 Programações cadastradas")

col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
with col_filtro1:
    filtro_data_inicio = st.date_input("Data início", value=datetime.date.today() - datetime.timedelta(days=30), format="DD/MM/YYYY", key="filtro_di")
with col_filtro2:
    filtro_data_fim = st.date_input("Data fim", value=datetime.date.today() + datetime.timedelta(days=30), format="DD/MM/YYYY", key="filtro_df")
with col_filtro3:
    opcoes_deposito = ["Todos"] + (depositos if depositos else [])
    filtro_deposito = st.selectbox("Filtrar por depósito", opcoes_deposito, key="filtro_dep")

# Montar query com filtros
query = """
    SELECT id, horario, fornecedor, deposito, qtd_sacos, tipo_contrato, tipo_cacau
    FROM programacoes
    WHERE DATE(horario) >= %s AND DATE(horario) <= %s
"""
params = [filtro_data_inicio.strftime("%Y-%m-%d"), filtro_data_fim.strftime("%Y-%m-%d")]

if filtro_deposito != "Todos":
    query += " AND deposito = %s"
    params.append(filtro_deposito)

query += " ORDER BY horario DESC"

conn = get_connection()
df = pd.read_sql_query(query, conn, params=params)

if df.empty:
    st.info("Nenhuma programação encontrada para os filtros selecionados.")
else:
    df.columns = [
        "ID", "Horário", "Fornecedor", "Depósito", "Qtd. Sacos", "Tipo de Contrato", "Tipo de Cacau"
    ]
    st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# EDIÇÃO DE PROGRAMAÇÃO
# ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("✏️ Editar Programação")

    ids_disponiveis = df["ID"].tolist()
    id_editar = st.selectbox("Selecione o ID da programação para editar", ids_disponiveis, key="edit_id")

    if id_editar:
        cur = get_cursor(conn)
        cur.execute(
            "SELECT horario, fornecedor, deposito, qtd_sacos, tipo_contrato, tipo_cacau FROM programacoes WHERE id = %s",
            (int(id_editar),),
        )
        registro = cur.fetchone()

        if registro:
            horario_atual = datetime.datetime.strptime(registro["horario"], "%Y-%m-%d %H:%M:%S")

            # ✅ CHAVE: usar o ID como parte da key de cada widget
            suffix = f"_{id_editar}"

            with st.form(f"form_editar{suffix}", clear_on_submit=False):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_data = st.date_input("Data do agendamento", value=horario_atual.date(), format="DD/MM/YYYY", key=f"edit_data{suffix}")
                    edit_hora = st.time_input("Horário do agendamento", value=horario_atual.time(), key=f"edit_hora{suffix}")
                    edit_fornecedor = st.selectbox(
                        "Fornecedor", fornecedores,
                        index=fornecedores.index(registro["fornecedor"]) if registro["fornecedor"] in fornecedores else 0,
                        key=f"edit_forn{suffix}"
                    ) if fornecedores else st.text_input("Fornecedor", value=registro["fornecedor"])
                    edit_deposito = st.selectbox(
                        "Depósito", depositos,
                        index=depositos.index(registro["deposito"]) if registro["deposito"] in depositos else 0,
                        key=f"edit_dep{suffix}"
                    ) if depositos else st.text_input("Depósito", value=registro["deposito"])
                with col_e2:
                    edit_qtd = st.number_input("Quantidade de sacos", min_value=1, step=1, value=int(registro["qtd_sacos"]), key=f"edit_qtd{suffix}")
                    edit_tipo_contrato = st.selectbox(
                        "Tipo de contrato", tipos_contrato,
                        index=tipos_contrato.index(registro["tipo_contrato"]) if registro["tipo_contrato"] in tipos_contrato else 0,
                        key=f"edit_tc{suffix}"
                    ) if tipos_contrato else st.text_input("Tipo de contrato", value=registro["tipo_contrato"])
                    edit_tipo_cacau = st.selectbox(
                        "Tipo de cacau", tipos_cacau,
                        index=tipos_cacau.index(registro["tipo_cacau"]) if registro["tipo_cacau"] in tipos_cacau else 0,
                        key=f"edit_tca{suffix}"
                    ) if tipos_cacau else st.text_input("Tipo de cacau", value=registro["tipo_cacau"])

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_salvar = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                with col_btn2:
                    btn_excluir = st.form_submit_button("🗑️ Excluir programação", use_container_width=True)

                if btn_salvar:
                    novo_horario = datetime.datetime.combine(edit_data, edit_hora)
                    cur = get_cursor(conn)
                    cur.execute(
                        """UPDATE programacoes
                           SET horario=%s, fornecedor=%s, deposito=%s, qtd_sacos=%s, tipo_contrato=%s, tipo_cacau=%s
                           WHERE id=%s""",
                        (
                            novo_horario.strftime("%Y-%m-%d %H:%M:%S"),
                            edit_fornecedor,
                            edit_deposito,
                            int(edit_qtd),
                            edit_tipo_contrato,
                            edit_tipo_cacau,
                            int(id_editar),
                        ),
                    )
                    conn.commit()
                    st.success(f"Programação ID {id_editar} atualizada com sucesso!")
                    st.rerun()

                if btn_excluir:
                    cur = get_cursor(conn)
                    cur.execute("DELETE FROM programacoes WHERE id=%s", (int(id_editar),))
                    conn.commit()
                    st.warning(f"Programação ID {id_editar} excluída.")
                    st.rerun()

