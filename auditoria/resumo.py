"""Monta o resumo executivo e o resumo por marca a partir das linhas de
auditoria ja conciliadas, e os valores prontos para escrever nas 3 abas."""

from datetime import datetime, timezone

COLUNAS_AUDITORIA = [
    "Marca", "Plano", "Cliente", "E-mail", "CPF/CNPJ", "Invoice ID", "Subscription ID",
    "Presente na Iugu", "Status na Iugu", "Status na Planilha", "Valor na Iugu", "Valor na Planilha",
    "Diferencas", "Tipo da Divergencia", "Descricao do Problema", "Acao Recomendada",
]


def montar_valores_auditoria(linhas):
    return [COLUNAS_AUDITORIA] + [[l.get(c, "") for c in COLUNAS_AUDITORIA] for l in linhas]


def montar_resumo_executivo(linhas, agora=None):
    agora = agora or datetime.now(timezone.utc)
    total = len(linhas)
    conciliadas = sum(1 for l in linhas if l.get("_conciliado"))
    divergentes = total - conciliadas
    pendentes = sum(1 for l in linhas if "Pendente" in str(l.get("Status na Iugu", "")))
    canceladas = sum(1 for l in linhas if "Cancelado" in str(l.get("Status na Iugu", "")))
    reembolsadas_total = sum(1 for l in linhas if "Totalmente Reembolsada" in str(l.get("Status na Iugu", "")))
    reembolsadas_parcial = sum(1 for l in linhas if "Parcialmente Reembolsada" in str(l.get("Status na Iugu", "")))
    inexistentes_iugu = sum(1 for l in linhas if "Ausente na Iugu" in str(l.get("Tipo da Divergencia", "")))
    inexistentes_planilha = sum(1 for l in linhas if "Ausente na Planilha" in str(l.get("Tipo da Divergencia", "")))

    valor_total_iugu = round(sum(l.get("Valor na Iugu") or 0 for l in linhas), 2)
    valor_total_planilha = round(sum(l.get("Valor na Planilha") or 0 for l in linhas), 2)
    diferenca_financeira = round(valor_total_iugu - valor_total_planilha, 2)
    percentual_divergencia = round((divergentes / total) * 100, 2) if total > 0 else 0

    return [
        ["Metrica", "Valor"],
        ["Data/Hora da Execucao", agora.strftime("%d/%m/%Y %H:%M")],
        ["Total de Invoices Analisadas", total],
        ["Total Conciliadas", conciliadas],
        ["Total Divergentes", divergentes],
        ["Total Pendentes", pendentes],
        ["Total Canceladas", canceladas],
        ["Total Reembolsadas (Total)", reembolsadas_total],
        ["Total Parcialmente Reembolsadas", reembolsadas_parcial],
        ["Total Inexistentes na Iugu", inexistentes_iugu],
        ["Total Inexistentes na Planilha", inexistentes_planilha],
        ["Valor Total na Iugu (R$)", valor_total_iugu],
        ["Valor Total na Planilha (R$)", valor_total_planilha],
        ["Diferenca Financeira (R$)", diferenca_financeira],
        ["Percentual de Divergencia (%)", percentual_divergencia],
    ]


def montar_resumo_por_marca(linhas):
    por_marca = {}
    for l in linhas:
        marca = l.get("Marca") or "(sem marca)"
        acc = por_marca.setdefault(marca, {"valor_iugu": 0.0, "valor_planilha": 0.0, "divergencias": 0})
        acc["valor_iugu"] += l.get("Valor na Iugu") or 0
        acc["valor_planilha"] += l.get("Valor na Planilha") or 0
        if not l.get("_conciliado"):
            acc["divergencias"] += 1

    linhas_marca = []
    for marca, acc in por_marca.items():
        diferenca = round(acc["valor_iugu"] - acc["valor_planilha"], 2)
        status = "Conciliado" if abs(diferenca) < 0.01 and acc["divergencias"] == 0 else "Divergente"
        linhas_marca.append(
            (marca, round(acc["valor_iugu"], 2), round(acc["valor_planilha"], 2), diferenca, acc["divergencias"], status)
        )

    linhas_marca.sort(key=lambda x: abs(x[3]), reverse=True)

    return [
        ["Marca", "Valor Total Iugu (R$)", "Valor Total Planilha (R$)", "Diferenca (R$)", "Qtd. Divergencias", "Status da Conciliacao"]
    ] + [list(l) for l in linhas_marca]
