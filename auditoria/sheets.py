"""Cliente do Google Sheets via conta de servico (google-api-python-client)."""

import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

from . import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_service = None


def _get_service():
    global _service
    if _service is None:
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        _service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _service


def ler_aba(spreadsheet_id, range_a1):
    svc = _get_service()
    resp = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_a1)
        .execute()
    )
    return resp.get("values", [])


def _titulos_abas(spreadsheet_id):
    svc = _get_service()
    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}


def garantir_abas_destino(spreadsheet_id, titulos=("Auditoria", "Resumo Executivo", "Resumo por Marca")):
    """Garante que as abas de destino existem (cria as que faltarem) e
    devolve {titulo: sheetId}."""
    svc = _get_service()
    existentes = _titulos_abas(spreadsheet_id)

    faltando = [t for t in titulos if t not in existentes]
    if faltando:
        requests_batch = [
            {"addSheet": {"properties": {"title": t, "gridProperties": {"frozenRowCount": 1}}}}
            for t in faltando
        ]
        resp = svc.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests_batch}
        ).execute()
        for reply in resp.get("replies", []):
            props = reply.get("addSheet", {}).get("properties")
            if props:
                existentes[props["title"]] = props["sheetId"]

    # remove a aba padrao "Sheet1"/"Página1" se sobrou vazia de uma planilha recem-criada
    for nome_padrao in ("Sheet1", "Página1", "Planilha1"):
        if nome_padrao in existentes and nome_padrao not in titulos:
            try:
                svc.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [{"deleteSheet": {"sheetId": existentes[nome_padrao]}}]},
                ).execute()
                del existentes[nome_padrao]
            except Exception:
                pass  # nao critico, so cosmetico

    return existentes


def limpar_e_escrever(spreadsheet_id, aba, range_a1_sem_aba, values):
    svc = _get_service()
    range_full = f"{aba}!{range_a1_sem_aba}"
    svc.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=range_full, body={}).execute()
    if values:
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{aba}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()


def formatar_divergencias(spreadsheet_id, gid_auditoria):
    """Aplica as regras de formatacao condicional (verde/amarelo/vermelho) na
    aba Auditoria, na coluna "Tipo da Divergencia" (coluna O). Sempre apaga as
    regras existentes antes de recriar, para nao acumular regras antigas
    apontando pra coluna errada se as colunas do relatorio mudarem no futuro."""
    svc = _get_service()

    meta = svc.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets(properties.sheetId,conditionalFormats)"
    ).execute()
    qtd_regras_existentes = 0
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["sheetId"] == gid_auditoria:
            qtd_regras_existentes = len(sheet.get("conditionalFormats") or [])
            break

    requests_batch = [
        {"deleteConditionalFormatRule": {"sheetId": gid_auditoria, "index": i}}
        for i in range(qtd_regras_existentes - 1, -1, -1)
    ]

    intervalo = [
        {
            "sheetId": gid_auditoria,
            "startRowIndex": 1,
            "startColumnIndex": 0,
            "endColumnIndex": 17,
            "endRowIndex": 5000,
        }
    ]

    regras = [
        # amarelo: pendente ou ainda aguardando o dia de vencimento deste mes
        (
            '=OR(REGEXMATCH($O2;"Pendente");REGEXMATCH($O2;"Aguardando Vencimento"))',
            {"red": 1, "green": 0.93, "blue": 0.6},
        ),
        # vermelho: qualquer outra divergencia real (inclui "Ausente na Iugu" -
        # vencimento ja passou e a fatura nao foi gerada)
        ('=AND($O2<>"Conciliado";$O2<>"")', {"red": 0.96, "green": 0.8, "blue": 0.8}),
        # verde: conciliado sem divergencias
        ('=$O2="Conciliado"', {"red": 0.8, "green": 0.94, "blue": 0.8}),
    ]
    for i, (formula, cor) in enumerate(regras):
        requests_batch.append(
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": intervalo,
                        "booleanRule": {
                            "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]},
                            "format": {"backgroundColor": cor},
                        },
                    },
                    "index": i,
                }
            }
        )

    svc.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests_batch}).execute()
