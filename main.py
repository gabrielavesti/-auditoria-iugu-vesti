"""Auditoria diaria: compara as faturas da Iugu com a planilha 'Marcas e
Planos' e escreve divergencias + resumos na planilha de auditoria.

Le as abas "Vesti MM-YYYY" e "Starter MM-YYYY" (mes/ano atual) da planilha de
origem, e concilia cada linha contra a subconta da Iugu indicada na propria
coluna "Subconta" (nao existe correspondencia fixa aba-subconta - ver
auditoria/matching.py).
"""

import sys
from datetime import datetime, timezone

from auditoria import config, iugu, sheets
from auditoria.matching import conciliar_por_subconta, linhas_da_aba
from auditoria.resumo import montar_resumo_executivo, montar_resumo_por_marca, montar_valores_auditoria


def main():
    agora = datetime.now(timezone.utc)
    sufixo_mes = agora.strftime("%m-%Y")

    print(f"[{agora.isoformat()}] Iniciando auditoria - periodo ate {sufixo_mes}")

    print("Buscando faturas na Iugu (todas as subcontas ativas)...")
    faturas = iugu.buscar_faturas_do_mes(agora)
    print(f"  {len(faturas)} faturas encontradas.")

    linhas_planilha = []
    for prefixo in config.ABAS_ORIGEM:
        aba = f"{prefixo} {sufixo_mes}"
        print(f"Lendo aba '{aba}' da planilha de origem...")
        try:
            values = sheets.ler_aba(config.SHEET_ID_ORIGEM, f"'{aba}'!A1:AZ3000")
        except Exception as exc:
            print(f"  AVISO: falha ao ler aba '{aba}': {exc}", file=sys.stderr)
            continue
        linhas = linhas_da_aba(values)
        print(f"  {len(linhas)} linhas validas.")
        linhas_planilha.extend(linhas)

    print(f"Total de linhas da planilha (Vesti + Starter): {len(linhas_planilha)}")

    print("Conciliando por subconta...")
    linhas_auditoria = conciliar_por_subconta(faturas, linhas_planilha)
    print(f"  {len(linhas_auditoria)} linhas de auditoria geradas.")

    valores_auditoria = montar_valores_auditoria(linhas_auditoria)
    resumo_executivo = montar_resumo_executivo(linhas_auditoria, agora)
    resumo_por_marca = montar_resumo_por_marca(linhas_auditoria)

    print("Garantindo abas de destino...")
    gids = sheets.garantir_abas_destino(config.SHEET_ID_DESTINO)

    print("Escrevendo aba 'Auditoria'...")
    sheets.limpar_e_escrever(config.SHEET_ID_DESTINO, "Auditoria", "A1:O5000", valores_auditoria)

    print("Escrevendo aba 'Resumo Executivo'...")
    sheets.limpar_e_escrever(config.SHEET_ID_DESTINO, "Resumo Executivo", "A1:B50", resumo_executivo)

    print("Escrevendo aba 'Resumo por Marca'...")
    sheets.limpar_e_escrever(config.SHEET_ID_DESTINO, "Resumo por Marca", "A1:F500", resumo_por_marca)

    print("Aplicando formatacao condicional...")
    sheets.formatar_divergencias(config.SHEET_ID_DESTINO, gids["Auditoria"])

    print("Auditoria concluida com sucesso.")


if __name__ == "__main__":
    main()
