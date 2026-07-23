
import datetime
import streamlit as st
import pandas as pd

from database import init_db, get_connection, get_cursor, agora
from auth import exigir_papel, sidebar_usuario, usuario_logado

st.set_page_config(page_title="Balança", page_icon="⚖️", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Operador de Balança")
sidebar_usuario()

st.title("⚖️ Operação de Balança")
st.caption(
    "Registre a pesagem (peso bruto) ao chegar e volte depois para lançar o peso tara."
)

conn = get_connection()

# ---------------------------------------------------------------------------
# FILTRO DE DATA (SLIDER)
# ---------------------------------------------------------------------------
st.subheader("📅 Filtro por período")

# Buscar datas mínima e máxima dos registros existentes
cur = get_cursor(conn)
cur.execute("SELECT MIN(data_pesagem_bruto), MAX(data_pesagem_bruto) FROM balanca")
datas_range = cur.fetchone()

hoje = datetime.date.today()

if datas_range["min"] is not None:
    data_min = datetime.datetime.strptime(datas_range["min"][:10], "%Y-%m-%d").date()
    data_max_db = datetime.datetime.strptime(datas_range["max"][:10], "%Y-%m-%d").date()
    data_max = max(data_max_db, hoje)
else:
    data_min = hoje - datetime.timedelta(days=30)
    data_max = hoje

# Garantir que o range tenha pelo menos 1 dia de diferença para o slider funcionar
if data_min >= data_max:
    data_min = data_max - datetime.timedelta(days=30)

filtro_datas = st.slider(
    "Período de pesagens",
    min_value=data_min,
    max_value=data_max,
    value=(data_min, data_max),
    format="DD/MM/YYYY",
    key="filtro_data_balanca"
)

data_inicio_filtro = filtro_datas[0].strftime("%Y-%m-%d")
data_fim_filtro = filtro_datas[1].strftime("%Y-%m-%d")

st.markdown("---")

tab_nova, tab_tara, tab_editar = st.tabs(["🆕 Nova pesagem (peso bruto)", "🔁 Lançar peso tara (finalizar)", "✏️ Editar lançamentos"])

# ---------------------------------------------------------------------------
# ABA 1 — Nova pesagem: programações que ainda não têm registro de balança
# ---------------------------------------------------------------------------
with tab_nova:
    programacoes_pendentes = pd.read_sql_query(
        """
        SELECT p.id, p.horario, p.fornecedor, p.deposito, p.qtd_sacos, p.tipo_contrato, p.tipo_cacau
        FROM programacoes p
        LEFT JOIN balanca b ON b.programacao_id = p.id
        WHERE b.id IS NULL
        ORDER BY p.horario
        """,
        conn,
    )

    if programacoes_pendentes.empty:
        st.info("Não há programações pendentes de pesagem.")
    else:
        opcoes = {
            f"#{row.id} — {row.horario} — {row.fornecedor} — {row.deposito} ({row.qtd_sacos} sacos)": row.id
            for row in programacoes_pendentes.itertuples()
        }
        escolha = st.selectbox("Selecione a programação", list(opcoes.keys()))
        programacao_id = opcoes[escolha]

        with st.form("form_balanca_bruto"):
            col1, col2 = st.columns(2)
            with col1:
                wb = st.text_input("Número da pesagem (WB)")
                nota_fiscal = st.text_input("Nota Fiscal")
            with col2:
                peso_bruto = st.number_input("Peso bruto (kg)", min_value=0, step=1)

            salvar = st.form_submit_button("💾 Registrar pesagem (bruto)", use_container_width=True)

            if salvar:
                if not wb.strip():
                    st.error("Informe o número da pesagem (WB).")
                else:
                    try:
                        cur = get_cursor(conn)
                        cur.execute(
                            """INSERT INTO balanca
                               (programacao_id, wb, nota_fiscal, peso_bruto, data_pesagem_bruto, operador)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (
                                programacao_id,
                                wb.strip(),
                                nota_fiscal.strip(),
                                float(peso_bruto),
                                agora(),
                                user["username"],
                            ),
                        )
                        conn.commit()
                        st.success("Peso bruto registrado! Volte na aba 'Lançar peso tara' ao final do processo.")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao salvar (WB pode já existir): {e}")

    st.markdown("---")
    st.subheader("Pesagens aguardando tara")
    pendentes_tara = pd.read_sql_query(
        """
        SELECT b.wb, b.nota_fiscal, b.peso_bruto, p.fornecedor, p.deposito
        FROM balanca b
        JOIN programacoes p ON p.id = b.programacao_id
        WHERE b.peso_tara IS NULL
        ORDER BY b.data_pesagem_bruto
        """,
        conn,
    )
    pendentes_tara.columns = ["WB", "Nota Fiscal", "Peso Bruto (kg)", "Fornecedor", "Depósito"]
    st.dataframe(pendentes_tara, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# ABA 2 — Lançar peso tara em um registro já existente
# ---------------------------------------------------------------------------
with tab_tara:
    pendentes = pd.read_sql_query(
        """
        SELECT b.id, b.wb, b.nota_fiscal, b.peso_bruto, p.fornecedor, p.deposito
        FROM balanca b
        JOIN programacoes p ON p.id = b.programacao_id
        WHERE b.peso_tara IS NULL
        ORDER BY b.data_pesagem_bruto
        """,
        conn,
    )

    if pendentes.empty:
        st.info("Não há pesagens pendentes de peso tara.")
    else:
        opcoes2 = {
            f"WB {row.wb} — {row.fornecedor} — {row.deposito} (Bruto: {row.peso_bruto} kg)": row.id
            for row in pendentes.itertuples()
        }
        escolha2 = st.selectbox("Selecione a pesagem para lançar a tara", list(opcoes2.keys()))
        balanca_id = opcoes2[escolha2]

        with st.form("form_balanca_tara"):
            peso_tara = st.number_input("Peso tara (kg)", min_value=0.0, step=0.5, format="%.2f")
            confirmar = st.form_submit_button("✅ Confirmar peso tara e finalizar pesagem", use_container_width=True)

            if confirmar:
                cur = get_cursor(conn)
                cur.execute("SELECT peso_bruto FROM balanca WHERE id=%s", (balanca_id,))
                peso_bruto_atual = cur.fetchone()["peso_bruto"]
                peso_liquido = round(peso_bruto_atual - float(peso_tara), 2)
                cur.execute(
                    "UPDATE balanca SET peso_tara=%s, peso_liquido=%s, data_pesagem_tara=%s WHERE id=%s",
                    (float(peso_tara), peso_liquido, agora(), balanca_id),
                )
                conn.commit()
                st.success(f"Peso tara registrado! Peso líquido calculado: {peso_liquido} kg")
                st.rerun()

# ---------------------------------------------------------------------------
# ABA 3 — Editar registro de balança
# ---------------------------------------------------------------------------
with tab_editar:
    todos_registros = pd.read_sql_query(
        """
        SELECT b.id, b.wb, b.nota_fiscal, b.peso_bruto, b.peso_tara, b.peso_liquido,
               p.fornecedor, p.deposito, p.id AS programacao_id
        FROM balanca b
        JOIN programacoes p ON p.id = b.programacao_id
        WHERE DATE(b.data_pesagem_bruto) >= %s AND DATE(b.data_pesagem_bruto) <= %s
        ORDER BY b.id DESC
        """,
        conn, params=[data_inicio_filtro, data_fim_filtro],
    )

    if todos_registros.empty:
        st.info("Não há registros de balança para editar.")
    else:
        opcoes_editar = {
            f"ID {row.id} — WB {row.wb} — {row.fornecedor} — {row.deposito} (Bruto: {row.peso_bruto} kg)": row.id
            for row in todos_registros.itertuples()
        }
        escolha_editar = st.selectbox(
            "Selecione o registro para editar",
            list(opcoes_editar.keys()),
            key="edit_balanca_select"
        )
        balanca_id_editar = opcoes_editar[escolha_editar]

        # Buscar dados atuais do registro selecionado
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, wb, nota_fiscal, peso_bruto, peso_tara, programacao_id
               FROM balanca WHERE id = %s""",
            (int(balanca_id_editar),),
        )
        registro = cur.fetchone()

        if registro:
            # Keys dinâmicas baseadas no ID para forçar atualização ao trocar registro
            suffix = f"_{balanca_id_editar}"

            with st.form(f"form_editar_balanca{suffix}", clear_on_submit=False):
                st.markdown(f"**Editando registro ID {registro['id']}**")

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_wb = st.text_input(
                        "Número da pesagem (WB)",
                        value=registro["wb"],
                        key=f"edit_wb{suffix}"
                    )
                    edit_nota_fiscal = st.text_input(
                        "Nota Fiscal",
                        value=registro["nota_fiscal"] if registro["nota_fiscal"] else "",
                        key=f"edit_nf{suffix}"
                    )
                with col_e2:
                    edit_peso_bruto = st.number_input(
                        "Peso bruto (kg)",
                        min_value=0.0,
                        step=0.5,
                        format="%.2f",
                        value=float(registro["peso_bruto"]),
                        key=f"edit_pb{suffix}"
                    )
                    edit_peso_tara = st.number_input(
                        "Peso tara (kg)",
                        min_value=0.0,
                        step=0.5,
                        format="%.2f",
                        value=float(registro["peso_tara"]) if registro["peso_tara"] is not None else 0.0,
                        key=f"edit_pt{suffix}"
                    )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_salvar = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                with col_btn2:
                    btn_excluir = st.form_submit_button("🗑️ Excluir registro", use_container_width=True)

                if btn_salvar:
                    if not edit_wb.strip():
                        st.error("O campo WB é obrigatório.")
                    else:
                        # Recalcular peso líquido se ambos os pesos estiverem preenchidos
                        novo_peso_liquido = None
                        if edit_peso_tara > 0 and edit_peso_bruto > 0:
                            novo_peso_liquido = round(edit_peso_bruto - edit_peso_tara, 2)

                        cur = get_cursor(conn)
                        cur.execute(
                            """UPDATE balanca
                               SET wb=%s, nota_fiscal=%s, peso_bruto=%s, peso_tara=%s, peso_liquido=%s
                               WHERE id=%s""",
                            (
                                edit_wb.strip(),
                                edit_nota_fiscal.strip(),
                                float(edit_peso_bruto),
                                float(edit_peso_tara) if edit_peso_tara > 0 else None,
                                novo_peso_liquido,
                                int(balanca_id_editar),
                            ),
                        )
                        conn.commit()
                        st.success(f"Registro ID {balanca_id_editar} atualizado com sucesso!")
                        if novo_peso_liquido is not None:
                            st.info(f"Peso líquido recalculado: {novo_peso_liquido} kg")
                        st.rerun()

                if btn_excluir:
                    cur = get_cursor(conn)
                    cur.execute("DELETE FROM balanca WHERE id=%s", (int(balanca_id_editar),))
                    conn.commit()
                    st.warning(f"Registro ID {balanca_id_editar} excluído.")
                    st.rerun()

# ---------------------------------------------------------------------------
# TABELA GERAL
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Todas as pesagens")
todas = pd.read_sql_query(
    """
    SELECT b.wb AS "WB", p.horario AS "Agendamento", p.fornecedor AS "Fornecedor", p.deposito AS "Depósito",
           b.nota_fiscal AS "Nota Fiscal", b.peso_bruto AS "Peso Bruto",
           b.peso_tara AS "Peso Tara", b.peso_liquido AS "Peso Líquido"
    FROM balanca b JOIN programacoes p ON p.id = b.programacao_id
    WHERE DATE(b.data_pesagem_bruto) >= %s AND DATE(b.data_pesagem_bruto) <= %s
    ORDER BY p.horario DESC
    """,
    conn, params=[data_inicio_filtro, data_fim_filtro],
)
st.dataframe(todas, use_container_width=True, hide_index=True)

