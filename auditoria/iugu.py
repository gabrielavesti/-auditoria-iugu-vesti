"""Cliente da API da Iugu: busca todas as faturas do mes corrente de todas as
subcontas ativas, usando o token master (retorna invoices de todas as
subcontas de uma vez, cada uma marcada com account_id)."""

from datetime import datetime, timezone
import requests

from . import config

LIMITE_PAGINA = 100


def buscar_faturas_do_mes(agora=None):
    """Retorna lista de dicts (uma fatura por item), ja filtrada para as
    subcontas ativas e enriquecida com _parceiro / _id_iugu."""
    agora = agora or datetime.now(timezone.utc)
    data_inicial = agora.replace(day=1).strftime("%Y-%m-%d")
    data_final = agora.strftime("%Y-%m-%d")

    resultado = []
    start = 0
    total_items = None

    while True:
        params = {
            "api_token": config.IUGU_MASTER_TOKEN,
            "created_at_from": data_inicial,
            "created_at_to": data_final,
            "limit": LIMITE_PAGINA,
            "start": start,
            "sortBy": "created_at",
            "sortType": "desc",
        }
        resp = requests.get("https://api.iugu.com/v1/invoices", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items") or []
        total_items = data.get("totalItems") if isinstance(data.get("totalItems"), int) else len(items)

        for inv in items:
            conta = config.CONTA_POR_ID.get(inv.get("account_id"))
            if not conta:
                continue  # subconta inativa/nao mapeada (Vesti Light, Vesti Sete) - ignora

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
        if len(items) < LIMITE_PAGINA or start >= total_items:
            break

    return resultado
