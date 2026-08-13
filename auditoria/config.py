"""Configuracao central da auditoria: IDs de planilhas, subcontas ativas da Iugu.

Segredos (token da Iugu, credencial da conta de servico do Google) vem de
variaveis de ambiente / GitHub Secrets - nunca ficam hardcoded aqui.
"""

import os

IUGU_MASTER_TOKEN = os.environ["IUGU_MASTER_TOKEN"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

SHEET_ID_ORIGEM = os.environ.get("SHEET_ID_ORIGEM", "1gfo0ORs4ccD0yn13eCuNxHM9USoGH_vjuzytcS1-QyQ")
SHEET_ID_DESTINO = os.environ.get("SHEET_ID_DESTINO", "1iuFLk7gatsxheUa3ePXXgotstc4YPBy6TXwwQ2pc9vY")

# Subcontas ativas da Iugu (17 linhas no CSV original menos "Vesti Light" - duplicata
# inativa de "Vesti Starter" - e as duas linhas "Vesti Sete", nenhuma ativa).
CONTAS_IUGU = [
    {"parceiro": "Portal Textil Atta", "id_iugu": "75272D2A2643430FB7F8323A00338043", "chaves": ["textil"]},
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
    # generica, tem que ficar por ultimo (e substring de quase todo valor de Subconta)
    {"parceiro": "Vesti", "id_iugu": "4D9307142A324DC28B5A920B934E6BC5", "chaves": ["vesti"]},
]

CONTA_POR_ID = {c["id_iugu"]: c for c in CONTAS_IUGU}

# abas da planilha de origem que sao lidas e comparadas (uma por mes, nomeadas
# "<PREFIXO> MM-YYYY" - ex "Vesti 08-2026", "Starter 08-2026")
ABAS_ORIGEM = ["Vesti", "Starter"]
