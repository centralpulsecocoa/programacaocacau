
import streamlit as st
import pandas as pd
import datetime

from database import init_db, get_connection, get_cursor, agora
from auth import exigir_papel, sidebar_usuario, usuario_logado

st.set_page_config(page_title="Classificador", page_icon="🔬", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Classificador")
sidebar_usuario()

st.title("🔬 Classificação de Qualidade")
st.caption(
    "⚠️ Por política de sigilo comercial, o nome do fornecedor **não é exibido** nesta tela."
)

conn = get_connection()

# ---------------------------------------------------------------------------
# FILTRO DE DATA (SLIDER)
# ---------------------------------------------------------------------------
st.subheader("📅 Filtro por período")

cur = get_cursor(conn)
cur.execute("SELECT MIN(data_classificacao), MAX(data_classificacao) FROM classificacao")
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
    "Período de classificações",
    min_value=data_min,
    max_value=data_max,
    value=(data_min, data_max),
    format="DD/MM/YYYY",
    key="filtro_data_classificacao"
)

data_inicio_filtro = filtro_datas[0].strftime("%Y-%m-%d")
data_fim_filtro = filtro_datas[1].strftime("%Y-%m-%d")

st.markdown("---")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_nova, tab_editar = st.tabs(["🆕 Nova classificação", "✏️ Editar registro"])

# Apenas cargas com descarga concluída e ainda sem classificação.
# Note: a consulta NÃO traz o campo "fornecedor" em nenhum momento.

with tab_nova:
    pendentes = pd.read_sql_query(
        """
        SELECT d.id AS deposito_operacao_id, d.numero_carga, p.deposito, p.tipo_cacau,
            d.qtd_sacos_amostrados, d.data_fim_descarga
        FROM deposito_operacao d
        JOIN balanca b ON b.id = d.balanca_id
        JOIN programacoes p ON p.id = b.programacao_id
        LEFT JOIN classificacao c ON c.deposito_operacao_id = d.id
        WHERE d.data_fim_descarga IS NOT NULL AND c.id IS NULL
        ORDER BY d.data_fim_descarga
        """,
        conn,
    )

    if pendentes.empty:
        st.info("Não há cargas com descarga concluída aguardando classificação.")
    else:
        opcoes = {
            f"Carga {row.numero_carga} — {row.deposito} — {row.tipo_cacau} ({row.qtd_sacos_amostrados} sacos amostrados)": row.deposito_operacao_id
            for row in pendentes.itertuples()
        }
        escolha = st.selectbox("Selecione a carga para classificar", list(opcoes.keys()))
        deposito_operacao_id = opcoes[escolha]

        with st.form("form_classificacao"):
            col1, col2, col3 = st.columns(3)
            with col1:
                umidade = st.number_input("Umidade (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
                fumaca = st.number_input("Fumaça (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
                ardosia = st.number_input("Ardósia", min_value=0.0, step=0.1, format="%.1f")
                germinado = st.number_input("Germinado", min_value=0.0, step=0.1, format="%.1f")
            with col2:
                violeta = st.number_input("Violeta", min_value=0.0, step=0.1, format="%.1f")
                mofo_interno = st.number_input("Mofo interno", min_value=0.0, step=0.1, format="%.1f")
                mofo_externo = st.number_input("Mofo externo", min_value=0.0, step=0.1, format="%.1f")
                infestado = st.number_input("Infestado", min_value=0, step=1)
            with col3:
                bean_count = st.number_input("Bean count", min_value=0.0, step=1.0, format="%.1f")
                achatado = st.number_input("Achatado (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
                ffa = st.number_input("FFA", min_value=0.0, step=0.1, format="%.2f")
                teor_casca = st.number_input("Teor de casca", min_value=0.0, step=0.1, format="%.2f")

            tipo_classificacao = st.text_input("Tipo de classificação")
            salvar = st.form_submit_button("💾 Registrar classificação", use_container_width=True)

            if salvar:
                cur = get_cursor(conn)
                cur.execute(
                    """INSERT INTO classificacao
                    (
                        deposito_operacao_id, umidade, fumaca, ardosia, germinado, violeta,
                        mofo_interno, mofo_externo, infestado, bean_count, achatado,
                        ffa, teor_casca, tipo_cacau, classificador, data_classificacao
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        deposito_operacao_id,
                        float(umidade),
                        float(fumaca),
                        float(ardosia),
                        float(germinado),
                        float(violeta),
                        float(mofo_interno),
                        float(mofo_externo),
                        int(infestado),
                        float(bean_count),
                        float(achatado),
                        float(ffa),
                        float(teor_casca),
                        tipo_classificacao,
                        user["username"],
                        agora(),
                    ),
                )
                conn.commit()
                st.success("Classificação registrada com sucesso!")
                st.rerun()

# ---------------------------------------------------------------------------
# ABA 2 — Editar registro de classificação
# ---------------------------------------------------------------------------
with tab_editar:
    todos_registros = pd.read_sql_query(
        """
        SELECT c.id, d.numero_carga, p.deposito, p.tipo_cacau, c.data_classificacao,
               c.umidade, c.fumaca, c.ardosia, c.germinado, c.violeta,
               c.mofo_interno, c.mofo_externo, c.infestado, c.bean_count,
               c.achatado, c.ffa, c.teor_casca, c.tipo_cacau AS tipo_class
        FROM classificacao c
        JOIN deposito_operacao d ON d.id = c.deposito_operacao_id
        JOIN balanca b ON b.id = d.balanca_id
        JOIN programacoes p ON p.id = b.programacao_id
        WHERE DATE(c.data_classificacao) >= %s AND DATE(c.data_classificacao) <= %s
        ORDER BY c.id DESC
        """,
        conn,
        params=[data_inicio_filtro, data_fim_filtro],
    )

    if todos_registros.empty:
        st.info("Não há registros de classificação para editar no período selecionado.")
    else:
        opcoes_editar = {
            f"ID {row.id} — Carga {row.numero_carga} — {row.deposito} — {row.tipo_cacau}": row.id
            for row in todos_registros.itertuples()
        }
        escolha_editar = st.selectbox(
            "Selecione o registro para editar",
            list(opcoes_editar.keys()),
            key="edit_classif_select"
        )
        classif_id_editar = opcoes_editar[escolha_editar]

        # Buscar dados atuais do registro selecionado
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, umidade, fumaca, ardosia, germinado, violeta,
                      mofo_interno, mofo_externo, infestado, bean_count,
                      achatado, ffa, teor_casca, tipo_cacau
               FROM classificacao WHERE id = %s""",
            (int(classif_id_editar),),
        )
        registro = cur.fetchone()

        if registro:
            # Keys dinâmicas baseadas no ID para forçar atualização ao trocar registro
            suffix = f"_{classif_id_editar}"

            with st.form(f"form_editar_classif{suffix}", clear_on_submit=False):
                st.markdown(f"**Editando classificação ID {registro['id']}**")

                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    edit_umidade = st.number_input(
                        "Umidade (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
                        value=float(registro["umidade"]) if registro["umidade"] is not None else 0.0,
                        key=f"edit_umid{suffix}"
                    )
                    edit_fumaca = st.number_input(
                        "Fumaça (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
                        value=float(registro["fumaca"]) if registro["fumaca"] is not None else 0.0,
                        key=f"edit_fum{suffix}"
                    )
                    edit_ardosia = st.number_input(
                        "Ardósia", min_value=0.0, step=0.1, format="%.1f",
                        value=float(registro["ardosia"]) if registro["ardosia"] is not None else 0.0,
                        key=f"edit_ard{suffix}"
                    )
                    edit_germinado = st.number_input(
                        "Germinado", min_value=0.0, step=0.1, format="%.1f",
                        value=float(registro["germinado"]) if registro["germinado"] is not None else 0.0,
                        key=f"edit_germ{suffix}"
                    )
                with col_e2:
                    edit_violeta = st.number_input(
                        "Violeta", min_value=0.0, step=0.1, format="%.1f",
                        value=float(registro["violeta"]) if registro["violeta"] is not None else 0.0,
                        key=f"edit_viol{suffix}"
                    )
                    edit_mofo_interno = st.number_input(
                        "Mofo interno", min_value=0.0, step=0.1, format="%.1f",
                        value=float(registro["mofo_interno"]) if registro["mofo_interno"] is not None else 0.0,
                        key=f"edit_mfi{suffix}"
                    )
                    edit_mofo_externo = st.number_input(
                        "Mofo externo", min_value=0.0, step=0.1, format="%.1f",
                        value=float(registro["mofo_externo"]) if registro["mofo_externo"] is not None else 0.0,
                        key=f"edit_mfe{suffix}"
                    )
                    edit_infestado = st.number_input(
                        "Infestado", min_value=0, step=1,
                        value=int(registro["infestado"]) if registro["infestado"] is not None else 0,
                        key=f"edit_inf{suffix}"
                    )
                with col_e3:
                    edit_bean_count = st.number_input(
                        "Bean count", min_value=0.0, step=1.0, format="%.1f",
                        value=float(registro["bean_count"]) if registro["bean_count"] is not None else 0.0,
                        key=f"edit_bc{suffix}"
                    )
                    edit_achatado = st.number_input(
                        "Achatado (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
                        value=float(registro["achatado"]) if registro["achatado"] is not None else 0.0,
                        key=f"edit_ach{suffix}"
                    )
                    edit_ffa = st.number_input(
                        "FFA", min_value=0.0, step=0.1, format="%.2f",
                        value=float(registro["ffa"]) if registro["ffa"] is not None else 0.0,
                        key=f"edit_ffa{suffix}"
                    )
                    edit_teor_casca = st.number_input(
                        "Teor de casca", min_value=0.0, step=0.1, format="%.2f",
                        value=float(registro["teor_casca"]) if registro["teor_casca"] is not None else 0.0,
                        key=f"edit_tc{suffix}"
                    )

                edit_tipo_class = st.text_input(
                    "Tipo de classificação",
                    value=registro["tipo_cacau"] if registro["tipo_cacau"] else "",
                    key=f"edit_tipo{suffix}"
                )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_salvar = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                with col_btn2:
                    btn_excluir = st.form_submit_button("🗑️ Excluir registro", use_container_width=True)

                if btn_salvar:
                    cur = get_cursor(conn)
                    cur.execute(
                        """UPDATE classificacao
                           SET umidade=%s, fumaca=%s, ardosia=%s, germinado=%s, violeta=%s,
                               mofo_interno=%s, mofo_externo=%s, infestado=%s, bean_count=%s,
                               achatado=%s, ffa=%s, teor_casca=%s, tipo_cacau=%s
                           WHERE id=%s""",
                        (
                            float(edit_umidade),
                            float(edit_fumaca),
                            float(edit_ardosia),
                            float(edit_germinado),
                            float(edit_violeta),
                            float(edit_mofo_interno),
                            float(edit_mofo_externo),
                            int(edit_infestado),
                            float(edit_bean_count),
                            float(edit_achatado),
                            float(edit_ffa),
                            float(edit_teor_casca),
                            edit_tipo_class,
                            int(classif_id_editar),
                        ),
                    )
                    conn.commit()
                    st.success(f"Classificação ID {classif_id_editar} atualizada com sucesso!")
                    st.rerun()

                if btn_excluir:
                    cur = get_cursor(conn)
                    cur.execute("DELETE FROM classificacao WHERE id=%s", (int(classif_id_editar),))
                    conn.commit()
                    st.warning(f"Classificação ID {classif_id_editar} excluída.")
                    st.rerun()

# ---------------------------------------------------------------------------
# TABELA GERAL (filtrada pelo período)
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Classificações já registradas")
# A listagem também não inclui o fornecedor.
todas = pd.read_sql_query(
    """
    SELECT d.numero_carga AS "Nº Carga", c.data_classificacao AS "Data de classificação",
           c.classificador AS "Classificador", p.deposito AS "Depósito", c.tipo_cacau AS "Tipo Cacau", d.residuo AS "Resído (%%),
           c.umidade AS "Umidade (%%)", c.fumaca AS "Fumaça (%%)", c.ardosia AS "Ardósia",
           c.germinado AS "Germinado", c.violeta AS "Violeta",
           c.mofo_interno AS "Mofo Interno", c.mofo_externo AS "Mofo Externo",
           c.infestado AS "Infestado", c.bean_count AS "Bean Count",
           c.achatado AS "Achatado (%%)", c.ffa AS "FFA",
           c.teor_casca AS "Teor Casca"
    FROM classificacao c
    JOIN deposito_operacao d ON d.id = c.deposito_operacao_id
    JOIN balanca b ON b.id = d.balanca_id
    JOIN programacoes p ON p.id = b.programacao_id
    WHERE DATE(c.data_classificacao) >= %s AND DATE(c.data_classificacao) <= %s
    ORDER BY c.id DESC
    """,
    conn,
    params=[data_inicio_filtro, data_fim_filtro],
)
st.dataframe(todas, use_container_width=True, hide_index=True)


