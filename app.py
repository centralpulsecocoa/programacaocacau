

import streamlit as st
from database import init_db
from auth import tela_login, usuario_logado, sidebar_usuario

st.set_page_config(
    page_title="Gestão de Depósito de Cacau",
    page_icon="🏭",
    layout="wide",
)

init_db()

user = usuario_logado()

if not user:
    tela_login()
else:
    sidebar_usuario()

    st.title("🏭 Gestão de Depósito de Cacau")
    st.markdown(f"### Bem-vindo(a), {user['nome_completo']}!")
    st.write(f"Seu papel de acesso: **{user['papel']}**")

    st.markdown("---")
    st.markdown(
        """
        Use o menu lateral (**Pages**) para navegar entre as telas do sistema:

        - 📅 **Programação** — cadastro de agendamentos de recebimento
        - ⚖️ **Balança** — registro de pesagens (bruto / tara)
        - 📦 **Depósito** — operação de descarga
        - 🔬 **Classificador** — análise de qualidade (sem visualizar o fornecedor)
        - 📊 **Acompanhamento** — painel em tempo real do processo
        - ⚙️ **Admin** — gestão de listas configuráveis e usuários (somente Admin)

        O acesso a cada tela é controlado pelo seu papel de usuário. O usuário **Admin**
        tem acesso a todas as telas.
        """
    )

