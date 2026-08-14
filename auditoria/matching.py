"""Normaliza as linhas da planilha, resolve a subconta da Iugu de cada linha
pelo texto (sujo) da coluna "Subconta", e concilia contra as faturas da Iugu
particionando por subconta (evita falso-positivo de CPF batendo entre
subcontas diferentes)."""

from . import config
from .texto import apenas_digitos, normalizar_header, normalizar_texto, para_numero


def resolver_conta(subconta_raw):
    norm = normalizar_texto(subconta_raw)
    if not norm:
        return None
    for conta in config.CONTAS_IUGU:
        if any(chave in norm for chave in conta["chaves"]):
            return conta
    return None


def _mapa_colunas(header_row):
    idx = {}
    for i, h in enumerate(header_row):
        n = normalizar_header(h)
        if "marca" in n:
            idx["marca"] = i
        elif "subconta" in n:
            idx["subconta"] = i
        elif n == "plano":
            idx["plano"] = i
        elif "cpf" in n:
            idx["cpfcnpj"] = i
        elif "totalcobrado" in n:
            idx["total_cobrado"] = i
        elif "mensalidade" in n and "inicial" not in n:
            idx["mensalidade"] = i
        elif "email" in n:
            idx["email"] = i
        elif "desconto" in n:
            idx["descontos"] = i
    return idx


def linhas_da_aba(values):
    """values: lista de listas (como vem de spreadsheets.values.get)."""
    if len(values) < 2:
        return []
    header = values[0]
    idx = _mapa_colunas(header)
    linhas = []
    for r in range(1, len(values)):
        row = values[r]
        if not row:
            continue

        def get(campo, default=""):
            i = idx.get(campo)
            if i is None or i >= len(row):
                return default
            return row[i] or default

        marca = get("marca")
        cpf = apenas_digitos(get("cpfcnpj"))
        if not marca and not cpf:
            continue
        if marca and normalizar_header(marca) == "marca":
            continue  # linha de cabecalho repetida

        if idx.get("total_cobrado") is not None and get("total_cobrado"):
            valor = para_numero(get("total_cobrado"))
        else:
            valor = para_numero(get("mensalidade", 0))

        subconta_raw = get("subconta")
        conta_resolvida = resolver_conta(subconta_raw)

        linhas.append(
            {
                "linha": r + 1,
                "marca": marca,
                "subconta": subconta_raw,
                "id_iugu": conta_resolvida["id_iugu"] if conta_resolvida else None,
                "parceiro_resolvido": conta_resolvida["parceiro"] if conta_resolvida else None,
                "plano": get("plano"),
                "cpfcnpj": cpf,
                "email": get("email"),
                "descontos": para_numero(get("descontos", 0)),
                "valor": valor,
            }
        )
    return linhas


_STATUS_PT = {
    "pending": "Pendente",
    "paid": "Pago",
    "canceled": "Cancelado",
    "expired": "Expirado",
    "draft": "Rascunho",
    "in_protest": "Em Protesto",
}


def _status_iugu_pt(inv):
    base = _STATUS_PT.get(inv.get("status"), inv.get("status") or "Desconhecido")
    total_cents = inv.get("total_cents") or 0
    refunded_cents = inv.get("refunded_cents") or 0
    if refunded_cents > 0 and total_cents > 0 and refunded_cents >= total_cents:
        return "Totalmente Reembolsada"
    if refunded_cents > 0:
        return "Parcialmente Reembolsada"
    return base


def _acao_recomendada(tipos):
    if not tipos:
        return "Nenhuma acao necessaria"
    if "Subconta nao identificada" in tipos:
        return "Corrigir o nome da Subconta na planilha para bater com a Iugu"
    if "Ausente na Planilha" in tipos:
        return "Lancar fatura na planilha Marcas e Planos"
    if "Ausente na Iugu" in tipos:
        return "Verificar se a cobranca foi de fato criada na Iugu"
    if "Totalmente Reembolsada" in tipos:
        return "Confirmar motivo do reembolso total e ajustar faturamento"
    if "Parcialmente Reembolsada" in tipos:
        return "Confirmar motivo do reembolso parcial"
    if "Cancelado" in tipos:
        return "Verificar cancelamento e remover/ajustar cobranca na planilha"
    if "Diferenca de Valor" in tipos:
        return "Conferir valor cobrado x valor contratado e corrigir divergencia"
    if "Divergencia de Marca" in tipos:
        return "Confirmar nome da marca em ambos os sistemas"
    if "Divergencia de Plano" in tipos:
        return "Confirmar plano contratado x plano cobrado"
    if "Multiplos Registros" in tipos:
        return "Revisar manualmente - mais de uma fatura/linha para o mesmo cliente"
    return "Revisar manualmente"


def _montar_linha_auditoria(parceiro, cpfcnpj, iugu_recs, sheet_recs, subconta_nao_identificada=False):
    tipos = []

    if subconta_nao_identificada:
        tipos.append("Subconta nao identificada")
    if not sheet_recs:
        tipos.append("Ausente na Planilha")
    if not subconta_nao_identificada and not iugu_recs:
        tipos.append("Ausente na Iugu")
    if len(iugu_recs) > 1 or len(sheet_recs) > 1:
        tipos.append("Multiplos Registros")

    valor_iugu = sum(i.get("total_cents") or 0 for i in iugu_recs) / 100
    valor_planilha = sum(r.get("valor") or 0 for r in sheet_recs)
    diferenca = round((valor_iugu - valor_planilha), 2)
    if not subconta_nao_identificada and abs(diferenca) >= 0.01:
        tipos.append("Diferenca de Valor")

    statuses_iugu = list(dict.fromkeys(_status_iugu_pt(i) for i in iugu_recs))
    for s in statuses_iugu:
        if s in ("Pendente", "Cancelado", "Totalmente Reembolsada", "Parcialmente Reembolsada"):
            tipos.append(s)

    sheet0 = sheet_recs[0] if sheet_recs else {}
    iugu0 = iugu_recs[0] if iugu_recs else {}

    marca = sheet0.get("marca") or iugu0.get("customer_name") or iugu0.get("payer_name") or ""
    marca_iugu = normalizar_texto(iugu0.get("customer_name") or iugu0.get("payer_name") or "")
    marca_planilha = normalizar_texto(sheet0.get("marca") or "")
    if marca_iugu and marca_planilha and marca_iugu not in marca_planilha and marca_planilha not in marca_iugu:
        tipos.append("Divergencia de Marca")

    plano_iugu = normalizar_texto(iugu0.get("plano_descricao") or "")
    plano_planilha = normalizar_texto(sheet0.get("plano") or "")
    if plano_iugu and plano_planilha and plano_iugu not in plano_planilha and plano_planilha not in plano_iugu:
        tipos.append("Divergencia de Plano")

    desconto_iugu = sum(i.get("discount_cents") or 0 for i in iugu_recs) / 100
    desconto_planilha = sum(r.get("descontos") or 0 for r in sheet_recs)
    if not subconta_nao_identificada and abs(desconto_iugu - desconto_planilha) >= 0.01:
        tipos.append("Desconto Divergente")

    tipos_unicos = list(dict.fromkeys(tipos))
    descricao = "Registro conciliado sem divergencias" if not tipos_unicos else f"Encontrado(s): {', '.join(tipos_unicos)}"

    return {
        "Marca": marca,
        "Plano": sheet0.get("plano") or iugu0.get("plano_descricao") or "",
        "Cliente": iugu0.get("customer_name") or iugu0.get("payer_name") or sheet0.get("marca") or "",
        "E-mail": iugu0.get("email") or sheet0.get("email") or "",
        "CPF/CNPJ": cpfcnpj or "",
        "Invoice ID": "; ".join(str(i.get("invoice_id")) for i in iugu_recs if i.get("invoice_id")),
        "Subscription ID": "; ".join(
            dict.fromkeys(str(i.get("subscription_id")) for i in iugu_recs if i.get("subscription_id"))
        ),
        "Presente na Iugu": "Presente na Iugu" if iugu_recs else "-",
        "Status na Iugu": "; ".join(statuses_iugu) or "-",
        "Status na Planilha": "Presente na Planilha" if sheet_recs else "-",
        "Valor na Iugu": valor_iugu,
        "Valor na Planilha": valor_planilha,
        "Diferencas": diferenca,
        "Tipo da Divergencia": "; ".join(tipos_unicos) if tipos_unicos else "Conciliado",
        "Descricao do Problema": descricao,
        "Acao Recomendada": _acao_recomendada(tipos_unicos),
        "_grupo": parceiro or sheet0.get("subconta") or "-",
        "_conciliado": len(tipos_unicos) == 0,
    }


def conciliar_por_subconta(faturas_iugu, linhas_planilha):
    linhas_auditoria = []

    linhas_resolvidas = []
    for row in linhas_planilha:
        if not row.get("id_iugu"):
            linhas_auditoria.append(
                _montar_linha_auditoria(None, row.get("cpfcnpj"), [], [row], subconta_nao_identificada=True)
            )
        else:
            linhas_resolvidas.append(row)

    ids_iugu = {f["_id_iugu"] for f in faturas_iugu} | {r["id_iugu"] for r in linhas_resolvidas}

    for id_iugu in ids_iugu:
        faturas_conta = [f for f in faturas_iugu if f["_id_iugu"] == id_iugu]
        linhas_conta = [r for r in linhas_resolvidas if r["id_iugu"] == id_iugu]
        parceiro = (faturas_conta[0]["_parceiro"] if faturas_conta else None) or (
            linhas_conta[0]["parceiro_resolvido"] if linhas_conta else None
        )

        iugu_by_cnpj = {}
        sem_cnpj_iugu = []
        for inv in faturas_conta:
            if inv.get("cpf_cnpj"):
                iugu_by_cnpj.setdefault(inv["cpf_cnpj"], []).append(inv)
            else:
                sem_cnpj_iugu.append(inv)

        sheet_by_cnpj = {}
        sem_cnpj_planilha = []
        for row in linhas_conta:
            if row.get("cpfcnpj"):
                sheet_by_cnpj.setdefault(row["cpfcnpj"], []).append(row)
            else:
                sem_cnpj_planilha.append(row)

        todos_cnpjs = set(iugu_by_cnpj) | set(sheet_by_cnpj)
        for cpf in todos_cnpjs:
            iugu_recs = iugu_by_cnpj.get(cpf, [])
            sheet_recs = sheet_by_cnpj.get(cpf, [])
            linhas_auditoria.append(_montar_linha_auditoria(parceiro, cpf, iugu_recs, sheet_recs))

        # fallback: casa por nome de marca quem nao tem CPF/CNPJ em nenhum dos lados
        usados_planilha = set()
        for inv in sem_cnpj_iugu:
            nome_iugu = normalizar_texto(inv.get("customer_name") or inv.get("payer_name") or "")
            match_idx = None
            for i, row in enumerate(sem_cnpj_planilha):
                if i in usados_planilha:
                    continue
                if nome_iugu and nome_iugu in normalizar_texto(row.get("marca") or ""):
                    match_idx = i
                    break
            if match_idx is not None:
                usados_planilha.add(match_idx)
                linhas_auditoria.append(
                    _montar_linha_auditoria(parceiro, "", [inv], [sem_cnpj_planilha[match_idx]])
                )
            else:
                linhas_auditoria.append(_montar_linha_auditoria(parceiro, "", [inv], []))

        for i, row in enumerate(sem_cnpj_planilha):
            if i not in usados_planilha:
                linhas_auditoria.append(_montar_linha_auditoria(parceiro, "", [], [row]))

    return linhas_auditoria
