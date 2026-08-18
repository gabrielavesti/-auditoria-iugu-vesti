# Auditoria Iugu x Marcas e Planos

Compara diariamente as faturas da Iugu (mes corrente) com as abas "Vesti
MM-YYYY" / "Starter MM-YYYY" mantidas dentro da propria planilha de
auditoria (copia limpa, atualizada manualmente todo fim de mes a partir da
planilha "Marcas e Planos") e escreve divergencias + resumos nas outras
abas da mesma planilha. Roda sozinho todo dia as 5h (Brasilia) via GitHub
Actions.

## O que precisa estar configurado

### 1. Secrets do repositorio (Settings -> Secrets and variables -> Actions)

| Secret | O que e | Onde pegar |
|---|---|---|
| `IUGU_MASTER_TOKEN` | Token master da conta Iugu | Ja configurado pelo Claude via API do GitHub |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Conteudo inteiro do arquivo `.json` da chave da conta de servico do Google | Ver passo a passo abaixo |

### 2. Criar a conta de servico do Google (uma vez so)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com), crie um projeto novo (ou use um existente).
2. Menu -> "APIs e servicos" -> "Biblioteca" -> procure **Google Sheets API** -> Ativar.
3. Menu -> "IAM e administrador" -> "Contas de servico" -> "Criar conta de servico".
   - Nome: qualquer um (ex: `auditoria-iugu`).
   - Nao precisa dar nenhum papel/role especial.
4. Depois de criada, clique nela -> aba "Chaves" -> "Adicionar chave" -> "Criar nova chave" -> formato **JSON** -> baixa um arquivo `.json`.
5. Abra esse arquivo, copie o email `client_email` de dentro dele (algo como `auditoria-iugu@SEU-PROJETO.iam.gserviceaccount.com`).
6. **Compartilhe a planilha com esse e-mail** (como editor):
   - "Auditoria Iugu x Marcas e Planos" (serve de origem e destino ao mesmo tempo)
7. Copie o **conteudo inteiro** do arquivo `.json` (abra num bloco de notas, selecione tudo) e cole como o secret `GOOGLE_SERVICE_ACCOUNT_JSON` no GitHub (Settings -> Secrets and variables -> Actions -> New repository secret).

### 3. IDs das planilhas

Ja configurados com valor padrao em `auditoria/config.py` (podem ser sobrescritos com as
variaveis de ambiente `SHEET_ID_ORIGEM` / `SHEET_ID_DESTINO` se precisar trocar):

- Origem e destino, mesma planilha ("Auditoria Iugu x Marcas e Planos"): `1iuFLk7gatsxheUa3ePXXgotstc4YPBy6TXwwQ2pc9vY`
  - Origem: abas "Vesti MM-YYYY" / "Starter MM-YYYY" (o usuario atualiza a copia limpa todo fim de mes, ex "Vesti 09-2026")
  - Destino: abas "Auditoria", "Resumo Executivo", "Resumo por Marca"

## Rodar manualmente (sem esperar as 5h)

Aba "Actions" do repositorio no GitHub -> "Auditoria diaria Iugu x Marcas e Planos" -> "Run workflow".

## Rodar localmente (para testar)

```bash
pip install -r requirements.txt
set IUGU_MASTER_TOKEN=...
set GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
python main.py
```

## Como funciona a comparacao

Cada linha das abas de origem tem uma coluna "Subconta" que diz a qual
subconta da Iugu ela pertence (o texto varia bastante: "Vesti - Atta",
"Vesti- Atta", "Vesti(assinatura)" etc). O script resolve esse texto para
a subconta certa (`auditoria/matching.py`) e só compara aquela linha contra
as faturas da MESMA subconta na Iugu - evita bater CPF de um cliente com
outro por acaso, em subcontas diferentes.

Linhas cuja Subconta nao bate com nenhuma subconta conhecida da Iugu entram
na auditoria com o tipo de divergencia "Subconta nao identificada", para
correcao manual do nome na planilha.
