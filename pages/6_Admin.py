
import streamlit as st
import pandas as pd

from database import init_db, get_connection, get_cursor, hash_senha
from auth import exigir_papel, sidebar_usuario, usuario_logado, PAPEIS

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")
init_db()

if not usuario_logado():
    st.warning("Faça login na página inicial para continuar.")
    st.stop()

user = exigir_papel("Admin")
sidebar_usuario()

st.title("⚙️ Administração")
st.caption("Gestão de listas configuráveis (dropdowns) e usuários do sistema.")

conn = get_connection()

tab_listas, tab_usuarios = st.tabs(["📋 Listas configuráveis", "👥 Usuários"])

# ---------------------------------------------------------------------------
# Listas configuráveis
# ---------------------------------------------------------------------------
with tab_listas:
    tipos = {
        "fornecedor": "Fornecedores",
        "deposito": "Depósitos",
        "tipo_contrato": "Tipos de contrato",
        "tipo_cacau": "Tipos de cacau",
    }

    tipo_escolhido = st.selectbox("Selecione a lista para gerenciar", list(tipos.values()))
    tipo_key = [k for k, v in tipos.items() if v == tipo_escolhido][0]

    col1, col2 = st.columns([2, 1])
    with col1:
        novo_valor = st.text_input(f"Adicionar novo valor em '{tipo_escolhido}'")
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Adicionar", use_container_width=True):
            if novo_valor.strip():
                try:
                    cur = get_cursor(conn)
                    cur.execute(
                        "INSERT INTO config_listas (tipo, valor) VALUES (%s,%s)",
                        (tipo_key, novo_valor.strip()),
                    )
                    conn.commit()
                    st.success("Adicionado!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Não foi possível adicionar (já existe?): {e}")

    st.markdown("---")
    itens = pd.read_sql_query(
        "SELECT id, valor, ativo FROM config_listas WHERE tipo=%s ORDER BY valor",
        conn,
        params=(tipo_key,),
    )

    if itens.empty:
        st.info("Nenhum item cadastrado ainda nesta lista.")
    else:
        for row in itens.itertuples():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(row.valor)
            ativo_atual = bool(row.ativo)
            novo_ativo = c2.toggle("Ativo", value=ativo_atual, key=f"toggle_{tipo_key}_{row.id}")
            if novo_ativo != ativo_atual:
                cur = get_cursor(conn)
                cur.execute("UPDATE config_listas SET ativo=%s WHERE id=%s", (int(novo_ativo), row.id))
                conn.commit()
                st.rerun()
            if c3.button("🗑️ Excluir", key=f"del_{tipo_key}_{row.id}"):
                cur = get_cursor(conn)
                cur.execute("DELETE FROM config_listas WHERE id=%s", (row.id,))
                conn.commit()
                st.rerun()

# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------
with tab_usuarios:
    st.subheader("Cadastrar novo usuário")
    with st.form("form_novo_usuario", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            novo_username = st.text_input("Usuário (login)")
            novo_nome = st.text_input("Nome completo")
        with c2:
            nova_senha = st.text_input("Senha", type="password")
            novo_papel = st.selectbox("Papel", PAPEIS)

        criar = st.form_submit_button("➕ Criar usuário", use_container_width=True)
        if criar:
            if not novo_username.strip() or not nova_senha:
                st.error("Usuário e senha são obrigatórios.")
            else:
                try:
                    cur = get_cursor(conn)
                    cur.execute(
                        "INSERT INTO usuarios (username, senha_hash, nome_completo, papel) VALUES (%s,%s,%s,%s)",
                        (novo_username.strip(), hash_senha(nova_senha), novo_nome.strip(), novo_papel),
                    )
                    conn.commit()
                    st.success("Usuário criado com sucesso!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Não foi possível criar (usuário já existe?): {e}")

    st.markdown("---")
    st.subheader("Usuários cadastrados")
    usuarios = pd.read_sql_query(
        "SELECT id, username, nome_completo, papel, ativo FROM usuarios ORDER BY nome_completo", conn
    )
    for row in usuarios.itertuples():
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{row.username}**")
        c2.write(row.nome_completo)
        c3.write(row.papel)
        ativo_atual = bool(row.ativo)
        novo_ativo = c4.toggle("Ativo", value=ativo_atual, key=f"user_toggle_{row.id}")
        if novo_ativo != ativo_atual:
            cur = get_cursor(conn)
            cur.execute("UPDATE usuarios SET ativo=%s WHERE id=%s", (int(novo_ativo), row.id))
            conn.commit()
            st.rerun()

