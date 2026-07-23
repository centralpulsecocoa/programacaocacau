# 🍫 Gestão de Depósito de Cacau — Streamlit

Aplicativo web para gerenciar entradas e saídas de cacau em depósito, com controle
de acesso por papel e acompanhamento em tempo real do processo.

## Como executar

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

2. Rode o aplicativo:
   ```
   streamlit run app.py
   ```

3. Acesse `http://localhost:8501` no navegador.

O banco de dados SQLite é criado automaticamente na primeira execução em
`data/deposito.db`, já com usuários e listas de demonstração.

## Usuários padrão

| Usuário | Senha | Papel |
|---|---|---|
| admin | admin123 | Admin (acesso total) |
| programacao | 123456 | Programação |
| balanca | 123456 | Operador de Balança |
| deposito | 123456 | Operador de Depósito |
| classificador | 123456 | Classificador |

⚠️ **Troque essas senhas** (ou crie novos usuários e desative os padrão) antes
de usar em produção — vá em ⚙️ **Admin → Usuários**.

## Estrutura das telas

| Página | Papel(éis) com acesso | Função |
|---|---|---|
| 📅 Programação | Programação, Admin | Cadastro de agendamentos de recebimento |
| ⚖️ Balança | Operador de Balança, Admin | Registro de WB, nota fiscal, peso bruto e (depois) peso tara |
| 📦 Depósito | Operador de Depósito, Admin | Início/fim de descarga, pesos e amostragem |
| 🔬 Classificador | Classificador, Admin | Análise de qualidade — **fornecedor oculto** |
| 📊 Acompanhamento | Todos os papéis | Painel em tempo real com filtros |
| ⚙️ Admin | Admin | Gestão das listas suspensas (fornecedores, depósitos, tipos de contrato/cacau) e usuários |

## Fluxo do processo

1. **Programação** cadastra o agendamento (fornecedor, depósito, sacos, contrato, tipo de cacau).
2. **Balança** seleciona a programação, lança WB + nota fiscal + peso bruto.
   Ao final do processo, volta na aba "Lançar peso tara" para fechar a pesagem
   (o sistema calcula o peso líquido automaticamente).
3. **Depósito** seleciona uma pesagem já finalizada (com tara) e registra a
   descarga: datas/horas de início e fim, número de carga, pesos (balancinha,
   líquido, duplo, pó) e sacos amostrados.
4. **Classificador** seleciona uma carga com descarga concluída (vê apenas o
   número de carga, depósito e tipo de cacau — **nunca o fornecedor**) e
   registra os parâmetros de qualidade.
5. **Acompanhamento** mostra todas as programações com status
   (⚪ não iniciado / 🟡 em progresso / ✅ finalizado), a etapa atual, e todos
   os campos das etapas anteriores + Umidade, Fumaça e FFA da classificação,
   com filtros por status, fornecedor, depósito e tipo de cacau.

## Personalização

- As listas suspensas de **Fornecedor**, **Depósito**, **Tipo de contrato** e
  **Tipo de cacau** são 100% configuráveis pelo Admin (ativar/desativar/excluir/adicionar),
  sem precisar mexer no código.
- O banco é SQLite (arquivo único `data/deposito.db`), fácil de trocar por
  Postgres/Snowflake no futuro caso o volume cresça — a camada `database.py`
  concentra todo o acesso a dados, então a migração fica localizada ali.

## Próximos passos sugeridos

- Trocar a autenticação simples por algo mais robusto (ex.: `streamlit-authenticator`
  com cookies, ou SSO corporativo) se for usar fora de uma rede confiável.
- Adicionar exportação para Excel/CSV nas telas de Acompanhamento e Admin.
- Adicionar edição/estorno de registros (hoje o fluxo é apenas de inclusão).
