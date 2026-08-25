"""Cliente da API da Iugu: busca as faturas do mes corrente de cada subconta
ativa separadamente, usando o token proprio de cada uma.

Cada subconta configurada em config.CONTAS_IUGU e uma conta Iugu separada de
verdade (nao uma "subconta" visivel por um token master unico) - um token
master so enxerga as proprias faturas dele, nunca as das contas filhas. Por
isso a busca e feita conta por conta, com o token dela, em vez de uma unica
chamada agregada."""

import calendar
import time
from datetime import datetime, timezone

import requests

from . import config

LIMITE_PAGINA = 100
PAUSA_ENTRE_CONTAS = 1.5  # segundos - evita 429 da Iugu ao varrer varias subcontas em sequencia


def _buscar_pagina(token, params, tentativas=4):
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            resp = requests.get("https://api.iugu.com/v1/invoices", params={**params, "api_token": token}, timeout=30)
        except requests.exceptions.RequestException as exc:
            ultimo_erro = exc
            if tentativa < tentativas - 1:
                time.sleep(5)
                continue
            raise
        if resp.status_code in (429, 500, 502, 503, 504) and tentativa < tentativas - 1:
            time.sleep(5)
            continue
        resp.raise_for_status()
        return resp.json()
    raise ultimo_erro


def buscar_faturas_do_mes(agora=None):
    """Retorna lista de dicts (uma fatura por item) de todas as subcontas
    ativas, cada uma buscada com seu proprio token."""
    agora = agora or datetime.now(timezone.utc)
    ultimo_dia_mes = calendar.monthrange(agora.year, agora.month)[1]
    data_inicial = agora.replace(day=1).strftime("%Y-%m-%d")
    data_final = agora.replace(day=ultimo_dia_mes).strftime("%Y-%m-%d")

    resultado = []
    for conta in config.CONTAS_IUGU:
        token = config.TOKENS_POR_ID.get(conta["id_iugu"])
        if not token:
            continue  # subconta sem token configurado - ignora

        start = 0
        total_items = None
        while True:
            data = _buscar_pagina(
                token,
                {
                    # filtra por vencimento, nao por criacao: a Iugu costuma
                    # criar a fatura de um cliente alguns dias ANTES do
                    # vencimento (as vezes ainda no mes anterior) - filtrar
                    # por created_at perdia faturas ja pagas cujo vencimento
                    # cai neste mes mas foram criadas no ultimo dia do mes
                    # passado (achado real: Blitz Closet, criada 31/07,
                    # vencimento 15/08).
                    "due_date_from": data_inicial,
                    "due_date_to": data_final,
                    "limit": LIMITE_PAGINA,
                    "start": start,
                    "sortBy": "due_date",
                    "sortType": "desc",
                },
            )
            items = data.get("items") or []
            total_items = data.get("totalItems") if isinstance(data.get("totalItems"), int) else len(items)

            for inv in items:
                resultado.append(
                    {
                        "_parceiro": conta["parceiro"],
                        "_id_iugu": conta["id_iugu"],
                        "invoice_id": inv.get("id"),
                        "status": inv.get("status"),
                        "subscription_id": inv.get("subscription_id"),
                        "customer_id": inv.get("customer_id"),
                        "customer_name": inv.get("customer_name") or inv.get("payer_name") or "",
                        "payer_name": inv.get("payer_name") or "",
                        "email": inv.get("email") or inv.get("payer_email") or "",
                        "cpf_cnpj": "".join(ch for ch in str(inv.get("payer_cpf_cnpj") or "") if ch.isdigit()),
                        "total_cents": inv.get("total_cents") or 0,
                        "total_paid_cents": inv.get("total_paid_cents") or 0,
                        "discount_cents": inv.get("discount_cents") or 0,
                        "refunded_cents": inv.get("refunded_cents") or 0,
                        "tax_cents": inv.get("tax_cents") or 0,
                        "due_date": inv.get("due_date"),
                        "paid_at": inv.get("paid_at"),
                        "canceled_at": inv.get("canceled_at"),
                        "refunded_at": inv.get("refunded_at"),
                        "plano_descricao": (inv.get("items") or [{}])[0].get("description", "") if inv.get("items") else "",
                        "account_id": inv.get("account_id"),
                        "account_name": inv.get("account_name") or conta["parceiro"],
                    }
                )

            start += LIMITE_PAGINA
            if len(items) < LIMITE_PAGINA or (total_items is not None and start >= total_items):
                break

        time.sleep(PAUSA_ENTRE_CONTAS)

    return resultado
