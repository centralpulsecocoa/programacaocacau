
import streamlit as st
import pandas as pd

from database import init_db, get_connection
from auth import sidebar_usuario, usuario_logado

st.set_page_config(page_title="Acompanhamento", page_icon="📊", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

# Tela de acompanhamento é visível para todos os papéis autenticados.
sidebar_usuario()

st.title("📊 Acompanhamento em Tempo Real")
st.caption("Visão geral do processo, do agendamento até a classificação.")

conn = get_connection()

df = pd.read_sql_query(
    """
    SELECT
        p.id AS programacao_id,
        p.horario,
        p.fornecedor,
        p.deposito,
        p.qtd_sacos,
        p.tipo_contrato,
        p.tipo_cacau,
        b.wb,
        b.nota_fiscal,
        b.peso_bruto,
        b.peso_tara,
        b.peso_liquido AS peso_liquido_balanca,
        d.numero_carga,
        d.data_inicio_descarga,
        d.data_fim_descarga,
        d.peso_balancinha,
        d.peso_liquido AS peso_liquido_deposito,
        d.peso_duplo,
        d.peso_po,
        d.qtd_sacos_amostrados,
        c.umidade,
        c.fumaca,
        c.ffa
    FROM programacoes p
    LEFT JOIN balanca b ON b.programacao_id = p.id
    LEFT JOIN deposito_operacao d ON d.balanca_id = b.id
    LEFT JOIN classificacao c ON c.deposito_operacao_id = d.id
    ORDER BY p.horario DESC
    """,
    conn,
)


def calcular_status(row):
    if pd.notna(row["ffa"]):
        return "✅ Finalizado"
    elif pd.notna(row["numero_carga"]) or pd.notna(row["wb"]):
        return "🟡 Em progresso"
    else:
        return "⚪ Não iniciado"


def calcular_etapa(row):
    if pd.notna(row["ffa"]):
        return "Classificado"
    if pd.notna(row["data_fim_descarga"]):
        return "Descarga concluída"
    if pd.notna(row["data_inicio_descarga"]):
        return "Em descarga"
    if pd.notna(row["peso_tara"]):
        return "Pesagem concluída"
    if pd.notna(row["peso_bruto"]):
        return "Peso bruto lançado"
    if pd.notna(row["wb"]):
        return "Pesagem iniciada"
    return "Aguardando pesagem"


df["status"] = df.apply(calcular_status, axis=1)
df["etapa_atual"] = df.apply(calcular_etapa, axis=1)

# --- Métricas resumo ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de programações", len(df))
col2.metric("⚪ Não iniciado", int((df["status"] == "⚪ Não iniciado").sum()))
col3.metric("🟡 Em progresso", int((df["status"] == "🟡 Em progresso").sum()))
col4.metric("✅ Finalizado", int((df["status"] == "✅ Finalizado").sum()))

st.markdown("---")

# --- Filtros ---
with st.expander("🔎 Filtros", expanded=True):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        status_sel = st.multiselect(
            "Status", ["⚪ Não iniciado", "🟡 Em progresso", "✅ Finalizado"], default=[]
        )
    with fc2:
        fornecedor_sel = st.multiselect("Fornecedor", sorted(df["fornecedor"].dropna().unique().tolist()))
    with fc3:
        deposito_sel = st.multiselect("Depósito", sorted(df["deposito"].dropna().unique().tolist()))
    with fc4:
        tipo_cacau_sel = st.multiselect("Tipo de cacau", sorted(df["tipo_cacau"].dropna().unique().tolist()))

df_filtrado = df.copy()
if status_sel:
    df_filtrado = df_filtrado[df_filtrado["status"].isin(status_sel)]
if fornecedor_sel:
    df_filtrado = df_filtrado[df_filtrado["fornecedor"].isin(fornecedor_sel)]
if deposito_sel:
    df_filtrado = df_filtrado[df_filtrado["deposito"].isin(deposito_sel)]
if tipo_cacau_sel:
    df_filtrado = df_filtrado[df_filtrado["tipo_cacau"].isin(tipo_cacau_sel)]

st.markdown("---")
st.subheader(f"Detalhamento do processo ({len(df_filtrado)} registros)")

colunas_exibir = {
    "status": "Status",
    "etapa_atual": "Etapa Atual",
    "horario": "Horário Programado",
    "fornecedor": "Fornecedor",
    "deposito": "Depósito",
    "qtd_sacos": "Qtd. Sacos (Prog.)",
    "tipo_contrato": "Tipo Contrato",
    "tipo_cacau": "Tipo Cacau",
    "wb": "WB",
    "nota_fiscal": "Nota Fiscal",
    "peso_bruto": "Peso Bruto",
    "peso_tara": "Peso Tara",
    "peso_liquido_balanca": "Peso Líquido (Balança)",
    "numero_carga": "Nº Carga",
    "data_inicio_descarga": "Início Descarga",
    "data_fim_descarga": "Fim Descarga",
    "peso_balancinha": "Peso Balancinha",
    "peso_liquido_deposito": "Peso Líquido (Depósito)",
    "peso_duplo": "Peso Duplo",
    "peso_po": "Peso Pó",
    "qtd_sacos_amostrados": "Sacos Amostrados",
    "umidade": "Umidade (%)",
    "fumaca": "Fumaça (%)",
    "ffa": "FFA",
}

df_exibicao = df_filtrado[list(colunas_exibir.keys())].rename(columns=colunas_exibir)

st.dataframe(
    df_exibicao,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.TextColumn(width="small"),
    },
)

st.caption(
    "Legenda: ⚪ Não iniciado (sem pesagem) · 🟡 Em progresso (pesagem/descarga em andamento) "
    "· ✅ Finalizado (classificação registrada). Campos de classificação detalhados "
    "(ardósia, violeta, mofo, bean count, achatado) ficam disponíveis apenas na tela do Classificador."
)

