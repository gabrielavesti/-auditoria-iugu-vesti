"""Script temporario de diagnostico: busca um CNPJ/CPF em TODAS as
subcontas da Iugu, numa janela ampla de datas, e imprime onde ele aparece
(subconta, invoice_id, status, valor, vencimento). Uso: python
debug_busca_cnpj.py <cnpj_ou_cpf>."""

import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from auditoria import config

CNPJ = "".join(ch for ch in sys.argv[1] if ch.isdigit())
agora = datetime.now(timezone.utc)
data_inicial = (agora - timedelta(days=365)).strftime("%Y-%m-%d")
data_final = agora.strftime("%Y-%m-%d")

print(f"Buscando CNPJ/CPF {CNPJ} entre {data_inicial} e {data_final} em todas as subcontas...\n")

for conta in config.CONTAS_IUGU:
    token = config.TOKENS_POR_ID.get(conta["id_iugu"])
    if not token:
        continue
    start = 0
    achou = False
    while True:
        resp = requests.get(
            "https://api.iugu.com/v1/invoices",
            params={
                "api_token": token,
                "due_date_from": data_inicial,
                "due_date_to": data_final,
                "limit": 100,
                "start": start,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") or []
        for inv in items:
            cpf_inv = "".join(ch for ch in str(inv.get("payer_cpf_cnpj") or "") if ch.isdigit())
            if cpf_inv == CNPJ:
                achou = True
                print(f"[{conta['parceiro']}] invoice {inv.get('id')} status={inv.get('status')} "
                      f"total={inv.get('total_cents')/100} due_date={inv.get('due_date')} "
                      f"customer={inv.get('customer_name')}")
        total_items = data.get("totalItems") if isinstance(data.get("totalItems"), int) else len(items)
        start += 100
        if len(items) < 100 or start >= total_items:
            break
    if not achou:
        print(f"[{conta['parceiro']}] nada encontrado")
    time.sleep(1)

print("\nFim.")
