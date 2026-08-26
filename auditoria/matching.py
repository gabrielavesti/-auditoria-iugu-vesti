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
        elif n == "diavencimento":
            idx["dia_vencimento"] = i
        elif n == "vencimento" and "dia_vencimento" not in idx:
            idx["dia_vencimento"] = i
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

        # Na aba "Vesti 08-2026", a maioria das linhas tem as colunas "CPF e
        # CNPJ" e "Vencimento" fisicamente trocadas na planilha (confirmado
        # celula a celula, sem merge envolvido - ex: Riquezzi Jeans, coluna U
        # com "26" e coluna W com o CNPJ de verdade). Em vez de depender de
        # qual coluna esta "certa", detecta pelo formato: CPF/CNPJ tem 11 ou
        # 14 digitos, dia de vencimento tem 1-2 digitos entre 1 e 31 - pega
        # cada valor de qualquer uma das duas colunas, o que bater o formato.
        cpf_col_cpf = apenas_digitos(get("cpfcnpj"))
        cpf_col_venc = apenas_digitos(get("dia_vencimento"))
        if len(cpf_col_cpf) in (11, 14):
            cpf = cpf_col_cpf
        elif len(cpf_col_venc) in (11, 14):
            cpf = cpf_col_venc
        else:
            cpf = ""
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

        def _como_dia(digitos):
            if digitos and 1 <= len(digitos) <= 2:
                n = int(digitos)
                if 1 <= n <= 31:
                    return n
            return None

        dia_vencimento = _como_dia(cpf_col_venc) or _como_dia(cpf_col_cpf)

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
                "dia_vencimento": dia_vencimento,
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
    if "Aguardando Vencimento" in tipos:
        return "Nenhuma acao necessaria - vencimento ainda nao chegou este mes"
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


def _montar_linha_auditoria(parceiro, cpfcnpj, iugu_recs, sheet_recs, subconta_nao_identificada=False, dia_atual=None):
    tipos = []

    # se a planilha nao tem fatura na Iugu mas o dia de vencimento deste mes
    # ainda nao chegou, ainda nao e um problema - a Iugu pode gerar a fatura
    # em qualquer momento ate o vencimento.
    dias_venc = [r.get("dia_vencimento") for r in sheet_recs if r.get("dia_vencimento")]
    vencimento_ja_passou = any(d < dia_atual for d in dias_venc) if (dias_venc and dia_atual is not None) else True
    aguardando_vencimento = (
        not subconta_nao_identificada
        and not iugu_recs
        and bool(sheet_recs)
        and bool(dias_venc)
        and not vencimento_ja_passou
    )

    if subconta_nao_identificada:
        tipos.append("Subconta nao identificada")
    if aguardando_vencimento:
        tipos.append("Aguardando Vencimento")
    if not sheet_recs:
        tipos.append("Ausente na Planilha")
    if not subconta_nao_identificada and not iugu_recs and not aguardando_vencimento:
        tipos.append("Ausente na Iugu")
    if len(iugu_recs) > 1 or len(sheet_recs) > 1:
        tipos.append("Multiplos Registros")

    valor_iugu = sum(i.get("total_cents") or 0 for i in iugu_recs) / 100
    valor_planilha = sum(r.get("valor") or 0 for r in sheet_recs)
    diferenca = round((valor_iugu - valor_planilha), 2)
    if not subconta_nao_identificada and not aguardando_vencimento and abs(diferenca) >= 0.01:
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
    if not subconta_nao_identificada and not aguardando_vencimento and abs(desconto_iugu - desconto_planilha) >= 0.01:
        tipos.append("Desconto Divergente")

    tipos_unicos = list(dict.fromkeys(tipos))
    tipos_reais = [t for t in tipos_unicos if t != "Aguardando Vencimento"]
    if tipos_unicos == ["Aguardando Vencimento"]:
        descricao = "Vencimento ainda nao chegou neste mes - nenhuma acao necessaria"
    elif not tipos_unicos:
        descricao = "Registro conciliado sem divergencias"
    else:
        descricao = f"Encontrado(s): {', '.join(tipos_unicos)}"

    return {
        "Marca": marca,
        "Plano": sheet0.get("plano") or iugu0.get("plano_descricao") or "",
        "Cliente": iugu0.get("customer_name") or iugu0.get("payer_name") or sheet0.get("marca") or "",
        "E-mail": iugu0.get("email") or sheet0.get("email") or "",
        "CPF/CNPJ": cpfcnpj or "",
        "Dia Vencimento": sheet0.get("dia_vencimento") if sheet0.get("dia_vencimento") is not None else "-",
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
        "_conciliado": len(tipos_reais) == 0,
    }


def _conciliar_faturas_com_planilha(
    faturas_conta, linhas_candidatas, dia_atual, parceiro, fallback_por_nome=True, exigir_linha_unica=False
):
    """Concilia um conjunto de faturas da Iugu contra um conjunto de linhas
    candidatas da planilha (por CPF/CNPJ exato, com fallback por nome de
    marca nos dois sentidos quando fallback_por_nome=True). Retorna
    (linhas_auditoria_geradas, linhas_candidatas_nao_usadas) - o chamador
    decide o que fazer com quem sobrou (virar "Ausente na Iugu" direto, ou
    voltar pro pool de outra conta, como no caso das contas globais).

    fallback_por_nome=False desliga o casamento por substring de nome -
    usado no passo global (contas tipo "Vesti Setup", que podem faturar
    marca de QUALQUER subconta): contra a planilha inteira, um nome curto
    pode coincidir por acaso com outra marca sem relacao (achado real:
    "Uezz" e substring de "riQUEZZi"), entao so aceita CPF/CNPJ exato.

    exigir_linha_unica=True (tambem so pro passo global) so fecha por
    CPF/CNPJ exato quando a planilha tem UMA SO linha com aquele CPF/CNPJ -
    uma empresa pode ter mais de uma linha com o mesmo CNPJ (plano normal +
    Oraculo, por ex.), e juntar as duas pra uma fatura avulsa so por
    coincidencia de CNPJ rouba a linha certa do match normal dela na propria
    subconta (achado real: Riquezzi Jeans - juntar as 2 linhas escondeu a
    mensalidade PRO, que devia ter fechado sozinha contra a fatura dela)."""
    linhas_auditoria = []

    iugu_by_cnpj = {}
    for inv in faturas_conta:
        if inv.get("cpf_cnpj"):
            iugu_by_cnpj.setdefault(inv["cpf_cnpj"], []).append(inv)

    sheet_by_cnpj = {}
    for row in linhas_candidatas:
        if row.get("cpfcnpj"):
            sheet_by_cnpj.setdefault(row["cpfcnpj"], []).append(row)

    # so fecha direto quem tem o MESMO CPF/CNPJ preenchido nos dois lados.
    # CPF preenchido so de um lado (ou faltando nos dois) vai pro fallback
    # por nome abaixo - fechar isso aqui direto criaria "Ausente na
    # Planilha"/"Ausente na Iugu" falsos sempre que so um dos dois
    # cadastros tem o CPF/CNPJ preenchido (caso real: Levitheo).
    cnpjs_em_comum = set(iugu_by_cnpj) & set(sheet_by_cnpj)
    if exigir_linha_unica:
        cnpjs_em_comum = {cpf for cpf in cnpjs_em_comum if len(sheet_by_cnpj[cpf]) == 1}
    for cpf in cnpjs_em_comum:
        linhas_auditoria.append(
            _montar_linha_auditoria(parceiro, cpf, iugu_by_cnpj[cpf], sheet_by_cnpj[cpf], dia_atual=dia_atual)
        )

    # grupos sem par exato de CPF/CNPJ: cada grupo mantem juntas todas as
    # faturas/linhas do mesmo CPF (preserva "Multiplos Registros" quando o
    # mesmo CPF tem varias faturas/linhas); quem nao tem CPF vira grupo de 1
    # item so, igual sempre foi.
    grupos_iugu_sem_par = [invs for cpf, invs in iugu_by_cnpj.items() if cpf not in cnpjs_em_comum]
    grupos_iugu_sem_par += [[inv] for inv in faturas_conta if not inv.get("cpf_cnpj")]

    grupos_planilha_sem_par = [rows for cpf, rows in sheet_by_cnpj.items() if cpf not in cnpjs_em_comum]
    grupos_planilha_sem_par += [[row] for row in linhas_candidatas if not row.get("cpfcnpj")]

    # fallback: casa por nome de marca quem nao fechou por CPF/CNPJ exato
    # (seja por falta do dado ou por CPF sem par do outro lado). Checa nos
    # dois sentidos porque o customer_name da Iugu costuma vir como "Marca =
    # Razao Social Completa" - mais longo que a Marca da planilha, entao so
    # caberia dentro dela no sentido planilha-em-iugu.
    usados_planilha = set()
    for grupo_iugu in grupos_iugu_sem_par:
        nome_iugu = normalizar_texto(grupo_iugu[0].get("customer_name") or grupo_iugu[0].get("payer_name") or "")
        match_idx = None
        for i, grupo_planilha in enumerate(grupos_planilha_sem_par):
            if not fallback_por_nome:
                break
            if i in usados_planilha:
                continue
            nome_planilha = normalizar_texto(grupo_planilha[0].get("marca") or "")
            if nome_iugu and nome_planilha and (nome_iugu in nome_planilha or nome_planilha in nome_iugu):
                match_idx = i
                break
        cpf_grupo = grupo_iugu[0].get("cpf_cnpj") or ""
        if match_idx is not None:
            usados_planilha.add(match_idx)
            linhas_auditoria.append(
                _montar_linha_auditoria(
                    parceiro, cpf_grupo, grupo_iugu, grupos_planilha_sem_par[match_idx], dia_atual=dia_atual
                )
            )
        else:
            linhas_auditoria.append(_montar_linha_auditoria(parceiro, cpf_grupo, grupo_iugu, [], dia_atual=dia_atual))

    linhas_nao_usadas = []
    for i, grupo_planilha in enumerate(grupos_planilha_sem_par):
        if i not in usados_planilha:
            linhas_nao_usadas.extend(grupo_planilha)

    return linhas_auditoria, linhas_nao_usadas


def conciliar_por_subconta(faturas_iugu, linhas_planilha, dia_atual=None):
    linhas_auditoria = []

    linhas_resolvidas = []
    for row in linhas_planilha:
        if not row.get("id_iugu"):
            linhas_auditoria.append(
                _montar_linha_auditoria(
                    None, row.get("cpfcnpj"), [], [row], subconta_nao_identificada=True, dia_atual=dia_atual
                )
            )
        else:
            linhas_resolvidas.append(row)

    # contas globais (ex: Vesti Setup/Oraculo) vendem servico avulso pra
    # marca de qualquer subconta - casam contra a planilha inteira antes do
    # particionamento normal por subconta, e quem casar sai do pool comum.
    faturas_globais = [f for f in faturas_iugu if f["_id_iugu"] in config.CONTAS_GLOBAIS]
    faturas_iugu = [f for f in faturas_iugu if f["_id_iugu"] not in config.CONTAS_GLOBAIS]
    if faturas_globais:
        parceiro_global = faturas_globais[0]["_parceiro"]
        linhas_globais, linhas_resolvidas = _conciliar_faturas_com_planilha(
            faturas_globais, linhas_resolvidas, dia_atual, parceiro_global,
            fallback_por_nome=False, exigir_linha_unica=True,
        )
        linhas_auditoria.extend(linhas_globais)

    ids_iugu = {f["_id_iugu"] for f in faturas_iugu} | {r["id_iugu"] for r in linhas_resolvidas}

    for id_iugu in ids_iugu:
        faturas_conta = [f for f in faturas_iugu if f["_id_iugu"] == id_iugu]
        linhas_conta = [r for r in linhas_resolvidas if r["id_iugu"] == id_iugu]
        parceiro = (faturas_conta[0]["_parceiro"] if faturas_conta else None) or (
            linhas_conta[0]["parceiro_resolvido"] if linhas_conta else None
        )

        linhas_conta_auditoria, sobras = _conciliar_faturas_com_planilha(
            faturas_conta, linhas_conta, dia_atual, parceiro
        )
        linhas_auditoria.extend(linhas_conta_auditoria)

        # reagrupa por CPF/CNPJ quem sobrou sem par (preserva "Multiplos
        # Registros" quando varias linhas do mesmo CPF ficam sem fatura).
        sobras_por_cpf = {}
        sobras_sem_cpf = []
        for row in sobras:
            if row.get("cpfcnpj"):
                sobras_por_cpf.setdefault(row["cpfcnpj"], []).append(row)
            else:
                sobras_sem_cpf.append(row)
        for cpf, rows in sobras_por_cpf.items():
            linhas_auditoria.append(_montar_linha_auditoria(parceiro, cpf, [], rows, dia_atual=dia_atual))
        for row in sobras_sem_cpf:
            linhas_auditoria.append(_montar_linha_auditoria(parceiro, "", [], [row], dia_atual=dia_atual))

    return linhas_auditoria
