
import datetime
import streamlit as st
import pandas as pd

from database import init_db, get_connection, get_cursor, agora
from auth import exigir_papel, sidebar_usuario, usuario_logado

st.set_page_config(page_title="Depósito", page_icon="📦", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Operador de Depósito")
sidebar_usuario()

st.title("📦 Operação de Depósito")
st.caption("Registro da descarga: início, fim, pesos e amostragem.")

conn = get_connection()

# ---------------------------------------------------------------------------
# FILTRO DE DATA (SLIDER)
# ---------------------------------------------------------------------------
st.subheader("📅 Filtro por período")

cur = get_cursor(conn)
cur.execute("SELECT MIN(data_inicio_descarga), MAX(data_inicio_descarga) FROM deposito_operacao")
datas_range = cur.fetchone()

hoje = datetime.date.today()

if datas_range["min"] is not None:
    data_min = datetime.datetime.strptime(datas_range["min"][:10], "%Y-%m-%d").date()
    data_max_db = datetime.datetime.strptime(datas_range["max"][:10], "%Y-%m-%d").date()
    data_max = max(data_max_db, hoje)
else:
    data_min = hoje - datetime.timedelta(days=30)
    data_max = hoje

if data_min >= data_max:
    data_min = data_max - datetime.timedelta(days=30)

filtro_datas = st.slider(
    "Período de operações",
    min_value=data_min,
    max_value=data_max,
    value=(data_min, data_max),
    format="DD/MM/YYYY",
    key="filtro_data_deposito"
)

data_inicio_filtro = filtro_datas[0].strftime("%Y-%m-%d")
data_fim_filtro = filtro_datas[1].strftime("%Y-%m-%d")

st.markdown("---")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_nova, tab_editar = st.tabs(["🆕 Nova operação de descarga", "✏️ Editar registro"])

with tab_nova:
    pendentes = pd.read_sql_query(
        """
        SELECT b.id AS balanca_id, b.wb, p.fornecedor, p.deposito, p.qtd_sacos, b.peso_liquido
        FROM balanca b
        JOIN programacoes p ON p.id = b.programacao_id
        LEFT JOIN deposito_operacao d ON d.balanca_id = b.id
        WHERE b.peso_tara IS NOT NULL AND d.id IS NULL
        ORDER BY b.data_pesagem_tara
        """,
        conn,
    )
    if pendentes.empty:
        st.info("Não há pesagens concluídas aguardando operação de depósito.")
    else:
        opcoes = {
            f"WB {row.wb} — {row.fornecedor} — {row.deposito} ({row.qtd_sacos} sacos, líquido {row.peso_liquido} kg)": row.balanca_id
            for row in pendentes.itertuples()
        }
        escolha = st.selectbox("Selecione a pesagem finalizada para dar entrada na descarga", list(opcoes.keys()))
        balanca_id = opcoes[escolha]

        with st.form("form_deposito"):
            numero_carga = st.text_input("Número de carga")

            col1, col2, col3 = st.columns(3)
            with col1:
                data_inicio = st.date_input("Data de início da descarga", format="DD/MM/YYYY", value=datetime.date.today())
                hora_inicio = st.time_input("Hora de início da descarga", value=datetime.time(8, 0))
                data_fim = st.date_input("Data de fim da descarga", format="DD/MM/YYYY", value=datetime.date.today())
                hora_fim = st.time_input("Hora de fim da descarga", value=datetime.time(9, 0))
            with col2:
                peso_balancinha = st.number_input("Peso balancinha (kg)", min_value=0, step=1)
                peso_liquido = st.number_input("Peso líquido (kg)", min_value=0, step=1)
                peso_duplo = st.number_input("Peso de duplo (kg)", min_value=0, step=1)
                peso_po = st.number_input("Peso de pó (kg)", min_value=0, step=1)
            with col3:
                peso_nibs = st.number_input("Peso nibs (kg)", min_value=0, step=1)
                qtd_sacos_amostrados = st.number_input("Quantidade de sacos amostrados", min_value=0, step=1)

            salvar = st.form_submit_button("💾 Registrar operação de depósito", use_container_width=True)

            if salvar:
                if not numero_carga.strip():
                    st.error("Informe o número de carga.")
                else:
                    inicio_dt = datetime.datetime.combine(data_inicio, hora_inicio)
                    fim_dt = datetime.datetime.combine(data_fim, hora_fim)
                    cur = get_cursor(conn)
                    cur.execute(
                        """INSERT INTO deposito_operacao
                        (balanca_id, numero_carga, data_inicio_descarga, data_fim_descarga,
                            peso_balancinha, peso_liquido, peso_duplo, peso_po,
                            qtd_sacos_amostrados, operador, peso_nibs)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            balanca_id,
                            numero_carga.strip(),
                            inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            fim_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            float(peso_balancinha),
                            float(peso_liquido),
                            float(peso_duplo),
                            float(peso_po),
                            int(qtd_sacos_amostrados),
                            user["username"],
                            float(peso_nibs),
                        ),
                    )
                    conn.commit()
                    st.success("Operação de depósito registrada com sucesso!")
                    st.rerun()

# ---------------------------------------------------------------------------
# ABA 2 — Editar registro de depósito
# ---------------------------------------------------------------------------
with tab_editar:
    todos_registros = pd.read_sql_query(
        """
        SELECT d.id, d.numero_carga, d.data_inicio_descarga, d.data_fim_descarga,
               d.peso_balancinha, d.peso_liquido, d.peso_duplo, d.peso_po,
               d.qtd_sacos_amostrados, p.fornecedor, p.deposito, b.wb
        FROM deposito_operacao d
        JOIN balanca b ON b.id = d.balanca_id
        JOIN programacoes p ON p.id = b.programacao_id
        WHERE DATE(d.data_inicio_descarga) >= %s AND DATE(d.data_inicio_descarga) <= %s
        ORDER BY d.id DESC
        """,
        conn,
        params=[data_inicio_filtro, data_fim_filtro],
    )

    if todos_registros.empty:
        st.info("Não há registros de depósito para editar no período selecionado.")
    else:
        opcoes_editar = {
            f"ID {row.id} — Carga {row.numero_carga} — WB {row.wb} — {row.fornecedor} — {row.deposito}": row.id
            for row in todos_registros.itertuples()
        }
        escolha_editar = st.selectbox(
            "Selecione o registro para editar",
            list(opcoes_editar.keys()),
            key="edit_deposito_select"
        )
        deposito_id_editar = opcoes_editar[escolha_editar]

        # Buscar dados atuais do registro selecionado
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, numero_carga, data_inicio_descarga, data_fim_descarga,
                      peso_balancinha, peso_liquido, peso_duplo, peso_po, peso_nibs, qtd_sacos_amostrados
               FROM deposito_operacao WHERE id = %s""",
            (int(deposito_id_editar),),
        )
        registro = cur.fetchone()

        if registro:
            # Keys dinâmicas baseadas no ID para forçar atualização ao trocar registro
            suffix = f"_{deposito_id_editar}"

            # Parsear datas existentes
            inicio_atual = datetime.datetime.strptime(registro["data_inicio_descarga"], "%Y-%m-%d %H:%M:%S")
            fim_atual = datetime.datetime.strptime(registro["data_fim_descarga"], "%Y-%m-%d %H:%M:%S")

            with st.form(f"form_editar_deposito{suffix}", clear_on_submit=False):
                st.markdown(f"**Editando registro ID {registro['id']} — Carga {registro['numero_carga']}**")

                edit_numero_carga = st.text_input("Número de carga", value=registro["numero_carga"], key=f"edit_ncarga{suffix}")

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_data_inicio = st.date_input("Data de início da descarga", value=inicio_atual.date(), format="DD/MM/YYYY", key=f"edit_di{suffix}")
                    edit_hora_inicio = st.time_input("Hora de início da descarga", value=inicio_atual.time(), key=f"edit_hi{suffix}")
                    edit_data_fim = st.date_input("Data de fim da descarga", value=fim_atual.date(), format="DD/MM/YYYY", key=f"edit_df{suffix}")
                    edit_hora_fim = st.time_input("Hora de fim da descarga", value=fim_atual.time(), key=f"edit_hf{suffix}")
                    edit_qtd_sacos = st.number_input("Quantidade de sacos amostrados", min_value=0, step=1, value=int(registro["qtd_sacos_amostrados"]), key=f"edit_sacos{suffix}")
                with col_e2:
                    edit_peso_balancinha = st.number_input("Peso balancinha (kg)", min_value=0, step=1, value=int(registro["peso_balancinha"]), key=f"edit_pbal{suffix}")
                    edit_peso_liquido = st.number_input("Peso líquido (kg)", min_value=0, step=1, value=int(registro["peso_liquido"]), key=f"edit_pliq{suffix}")
                    edit_peso_duplo = st.number_input("Peso de duplo (kg)", min_value=0, step=1, value=int(registro["peso_duplo"]), key=f"edit_pdup{suffix}")
                    edit_peso_po = st.number_input("Peso de pó (kg)", min_value=0, step=1, value=int(registro["peso_po"]), key=f"edit_ppo{suffix}")
                    edit_peso_nibs = st.number_input("Peso de nibs (kg)", min_value=0, step=1, value=int(registro["peso_nibs"]), key=f"edit_pnb{suffix}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_salvar = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                with col_btn2:
                    btn_excluir = st.form_submit_button("🗑️ Excluir registro", use_container_width=True)

                if btn_salvar:
                    if not edit_numero_carga.strip():
                        st.error("O campo Número de carga é obrigatório.")
                    else:
                        novo_inicio = datetime.datetime.combine(edit_data_inicio, edit_hora_inicio)
                        novo_fim = datetime.datetime.combine(edit_data_fim, edit_hora_fim)
                        cur = get_cursor(conn)
                        cur.execute(
                            """UPDATE deposito_operacao
                               SET numero_carga=%s, data_inicio_descarga=%s, data_fim_descarga=%s,
                                   peso_balancinha=%s, peso_liquido=%s, peso_duplo=%s, peso_po=%s,
                                   qtd_sacos_amostrados=%s, peso_nibs=%s
                               WHERE id=%s""",
                            (
                                edit_numero_carga.strip(),
                                novo_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                                novo_fim.strftime("%Y-%m-%d %H:%M:%S"),
                                float(edit_peso_balancinha),
                                float(edit_peso_liquido),
                                float(edit_peso_duplo),
                                float(edit_peso_po),
                                int(edit_qtd_sacos),
                                float(edit_peso_nibs),
                                int(deposito_id_editar),
                            ),
                        )
                        conn.commit()
                        st.success(f"Registro ID {deposito_id_editar} atualizado com sucesso!")
                        st.rerun()

                if btn_excluir:
                    cur = get_cursor(conn)
                    cur.execute("DELETE FROM deposito_operacao WHERE id=%s", (int(deposito_id_editar),))
                    conn.commit()
                    st.warning(f"Registro ID {deposito_id_editar} excluído.")
                    st.rerun()

# ---------------------------------------------------------------------------
# TABELA GERAL
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Operações de depósito registradas")
todas = pd.read_sql_query(
    """
    SELECT d.numero_carga AS "Nº Carga", p.fornecedor AS "Fornecedor", p.deposito AS "Depósito",
           d.data_inicio_descarga AS "Início Descarga", d.data_fim_descarga AS "Fim Descarga",
           d.peso_balancinha AS "Peso Balancinha", d.peso_liquido AS "Peso Líquido",
           d.peso_duplo AS "Peso Duplo", d.peso_po AS "Peso Pó", d.peso_nibs AS "Peso Nibs",
           d.qtd_sacos_amostrados AS "Sacos Amostrados"
    FROM deposito_operacao d
    JOIN balanca b ON b.id = d.balanca_id
    JOIN programacoes p ON p.id = b.programacao_id
    WHERE DATE(d.data_inicio_descarga) >= %s AND DATE(d.data_inicio_descarga) <= %s
    ORDER BY d.id DESC
    """,
    conn,
    params=[data_inicio_filtro, data_fim_filtro],
)
st.dataframe(todas, use_container_width=True, hide_index=True)

