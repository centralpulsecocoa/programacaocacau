"""
Funções auxiliares de autenticação e controle de acesso por papel (RBAC).
"""

import streamlit as st
from database import autenticar

PAPEIS = [
    "Programação",
    "Operador de Balança",
    "Operador de Depósito",
    "Classificador",
    "Admin",
]


def usuario_logado():
    return st.session_state.get("usuario")


def fazer_logout():
    for chave in ["usuario"]:
        if chave in st.session_state:
            del st.session_state[chave]


def tela_login():
    st.title("🍫 Gestão de Depósito de Cacau")
    st.caption("Faça login para continuar")

    with st.form("login_form"):
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        user = autenticar(username, senha)
        if user:
            st.session_state["usuario"] = user
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos, ou usuário inativo.")

    # with st.expander("ℹ️ Usuários padrão de demonstração"):
    #     st.markdown(
    #         """
    #         | Usuário | Senha | Papel |
    #         |---|---|---|
    #         | admin | admin123 | Admin (acesso total) |
    #         | programacao | 123456 | Programação |
    #         | balanca | 123456 | Operador de Balança |
    #         | deposito | 123456 | Operador de Depósito |
    #         | classificador | 123456 | Classificador |
    #         """
    #     )


def exigir_papel(*papeis_permitidos):
    """Bloqueia o acesso à página caso o usuário não tenha um dos papéis permitidos.
    Admin sempre tem acesso a tudo."""
    user = usuario_logado()
    if not user:
        st.warning("Você precisa fazer login para acessar esta página.")
        st.stop()
    if user["papel"] != "Admin" and user["papel"] not in papeis_permitidos:
        st.error(
            f"🔒 Acesso restrito. Esta tela é destinada a: {', '.join(papeis_permitidos)}."
        )
        st.stop()
    return user


def sidebar_usuario():
    user = usuario_logado()
    if user:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**👤 {user['nome_completo']}**")
            st.caption(f"Papel: {user['papel']}")
            if st.button("Sair", use_container_width=True):
                fazer_logout()
                st.rerun()
