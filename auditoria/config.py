"""Configuracao central da auditoria: IDs de planilhas, subcontas ativas da Iugu.

Segredos (token da Iugu, credencial da conta de servico do Google) vem de
variaveis de ambiente / GitHub Secrets - nunca ficam hardcoded aqui.
"""

import json
import os

# JSON com [{"parceiro", "id_iugu", "token"}, ...] - um token proprio por
# subconta (cada subconta e uma conta Iugu separada de verdade; um token
# master unico so enxerga a propria conta dele, nunca as subcontas filhas -
# ver historico do projeto para o diagnostico completo).
IUGU_TOKENS_JSON = os.environ["IUGU_TOKENS_JSON"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

TOKENS_POR_ID = {c["id_iugu"]: c["token"] for c in json.loads(IUGU_TOKENS_JSON)}

# Origem = a propria planilha de auditoria: o usuario mantem copias limpas
# (revisadas manualmente, sem linhas que na verdade nao existem/sao isentas na
# Iugu) das abas "Vesti MM-YYYY" / "Starter MM-YYYY" dentro dela mesma,
# atualizadas por ele ao fim de cada mes. Antes (ate 2026-08-18) a origem era
# a planilha "Marcas e Planos" (1gfo0ORs4ccD0yn13eCuNxHM9USoGH_vjuzytcS1-QyQ).
SHEET_ID_ORIGEM = os.environ.get("SHEET_ID_ORIGEM", "1iuFLk7gatsxheUa3ePXXgotstc4YPBy6TXwwQ2pc9vY")
SHEET_ID_DESTINO = os.environ.get("SHEET_ID_DESTINO", "1iuFLk7gatsxheUa3ePXXgotstc4YPBy6TXwwQ2pc9vY")

# Subcontas ativas da Iugu (2026-08-25: cada uma e uma conta Iugu separada de
# verdade, com seu proprio token em IUGU_TOKENS_JSON - "Portal Textil Atta"
# foi removida a pedido do usuario, nao e mais usada no projeto).
CONTAS_IUGU = [
    {"parceiro": "Vesti Multimarcas", "id_iugu": "72C32E7967E14D8CA4391F607686A096", "chaves": ["multimarcas"]},
    {"parceiro": "Vesti ProRoi", "id_iugu": "C35840FD3CBA4665B1724C8C0A16B127", "chaves": ["proroi"]},
    {"parceiro": "Vesti Tizzefy", "id_iugu": "9A0ABCF77B134ABE93E367E676BC54F4", "chaves": ["tizzefy"]},
    {"parceiro": "Vesti Uemtel", "id_iugu": "B8CDC77C2E3A48BF928F555D84C0D7ED", "chaves": ["uemtel"]},
    {"parceiro": "Vesti Vê Vantagens", "id_iugu": "0A652ECC26D74C3CB757165277294916", "chaves": ["vantagens"]},
    {"parceiro": "Vesti Atta", "id_iugu": "64F29324B0DD42949541CAA9CAF85AB8", "chaves": ["atta"]},
    {"parceiro": "Vesti - Comfio", "id_iugu": "BDD2CB7FA56C47CCAB16CB8C565D4CCB", "chaves": ["comfio"]},
    {"parceiro": "Vesti - Glads", "id_iugu": "0D7B7B8F0CC84AEBB3681137BF8013AE", "chaves": ["glads"]},
    {"parceiro": "Vesti - Renan de Abreu", "id_iugu": "4967C0F69EAD4E1B96AE363AF0C152E9", "chaves": ["renan"]},
    {"parceiro": "Vesti Setup", "id_iugu": "381FEEEA09BE4A17942BDA5888C94470", "chaves": ["setup"]},
    {"parceiro": "Vesti- Up Agency", "id_iugu": "EDB655C564C24E6BA9190607F0B1B229", "chaves": ["agency"]},
    {"parceiro": "Vesti Starter", "id_iugu": "A75417523A5040D399EB1D56E129DEE8", "chaves": ["starter"]},
    {"parceiro": "Vesti Portal", "id_iugu": "EFCEC6A16EF14FDB8C0A8C569E378C4F", "chaves": ["portal"]},
    {"parceiro": "Vesti Sete", "id_iugu": "2EE7187C12AA4FFDB6531DE6D35BA41D", "chaves": ["sete"]},
    {"parceiro": "Mensalidade Vesti", "id_iugu": "BD16B8EBD6A7479799D1B3464B56676A", "chaves": ["mensalidade"]},
    {"parceiro": "Vesti - SNAPFY.AI", "id_iugu": "8CB2BBA7CE00472B9A8D75B1DD9D71C2", "chaves": ["snapfy"]},
    {"parceiro": "Vesti - Vesti Go", "id_iugu": "50E8AB8BE7B7482F9AAB67DFA0D87F96", "chaves": ["vesti go", "vestigo"]},
    # generica, tem que ficar por ultimo (e substring de quase todo valor de Subconta)
    {"parceiro": "Vesti", "id_iugu": "4D9307142A324DC28B5A920B934E6BC5", "chaves": ["vesti"]},
]

# Contas que vendem um servico avulso (plus) pra marcas de QUALQUER
# subconta - ex: "Vesti Setup" fatura o Oraculo, que pode ser vendido pra
# uma marca da Atta, da Comfio, da Vesti generica, etc. Faturas dessas
# contas nao ficam presas a comparar so contra a mesma subconta (ao
# contrario do resto) - casam contra a planilha inteira por CPF/CNPJ ou
# nome (achado real: Riquezzi Jeans, setup faturado em "Vesti Setup" mas a
# marca em si e da subconta "Vesti").
CONTAS_GLOBAIS = {"381FEEEA09BE4A17942BDA5888C94470"}  # Vesti Setup

# abas da planilha de origem que sao lidas e comparadas (uma por mes, nomeadas
# "<PREFIXO> MM-YYYY" - ex "Vesti 08-2026", "Starter 08-2026")
ABAS_ORIGEM = ["Vesti", "Starter"]
