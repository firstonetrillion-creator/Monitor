"""Parser determinístico, sanitização LGPD e cálculo do Custo da Estrutura do Mandato (Fase 2 — CENTI 2026)."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from cerrado_aberto_coleta import NOTA_OFICIAL_CEAP
from cerrado_aberto_coleta.custo_mandato import (
    DiariaItem,
    FolhaServidorItem,
    calcular_custo_estrutura_mandato,
)
from cerrado_aberto_coleta.entidades import (
    VEREADORES_MESTRE_INHUMAS,
    ResolvedorVereadores,
)
from cerrado_aberto_coleta.normalizacao import (
    gerar_chave_busca,
    mascarar_documento_lgpd,
    normalizar_texto,
    parse_data_iso,
    parse_valor_brl,
)
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto
from cerrado_aberto_coleta.transparencia.schemas import (
    CustoEstruturaMandatoMensalRegistro,
    DeclaracaoTransparenciaRegistro,
    DespesaEmpenhoRegistro,
    DiariaRegistro,
    DuodecimoRegistro,
    FolhaPagamentoRegistro,
    FornecedorRegistro,
)

MESES_PORTUGUES: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def extrair_ano_mes_referencia(referencia: str) -> tuple[int, int]:
    """Extrai `(ano, mes)` de strings como `'Outubro/2026'` ou `'10/2026'`."""
    limpo = (referencia or "").strip()
    if "/" not in limpo:
        raise ValueError(f"Referência de competência inválida: {referencia!r}")
    parte_mes, parte_ano = [p.strip() for p in limpo.split("/", 1)]
    ano = int(parte_ano)
    if parte_mes.isdigit():
        mes = int(parte_mes)
    else:
        chave_mes = parte_mes.lower()
        if chave_mes not in MESES_PORTUGUES:
            raise ValueError(f"Mês desconhecido na referência: {referencia!r}")
        mes = MESES_PORTUGUES[chave_mes]
    return ano, mes


def gerar_slug_tipo_folha(tipo_folha: str) -> str:
    chave = gerar_chave_busca(tipo_folha)
    return chave.replace(" ", "-") or "mensal"


def _coletado_em_dt(valor: datetime | str) -> datetime:
    if isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor)


def sanitizar_csv_despesas_lgpd(conteudo_bytes: bytes) -> tuple[bytes, int]:
    """Sanitiza a coluna `CPF/CNPJ` do CSV bruto de despesas antes do armazenamento em disco.

    Garante que qualquer CPF parcial (`050.xxx.xxx-63`) ou integral de Pessoa Física
    seja substituído por `'***.***.***-**'`, preservando CNPJs públicos de 14 dígitos.
    Retorna `(bytes_sanitizados, total_cpfs_mascarados)`.
    """
    texto = conteudo_bytes.decode("utf-8-sig")
    linhas = texto.splitlines()
    if len(linhas) < 2:
        return conteudo_bytes, 0

    linha_totais = linhas[0]
    leitor = csv.DictReader(linhas[1:], delimiter=";")
    colunas = list(leitor.fieldnames or [])

    saida_io = io.StringIO()
    saida_io.write(linha_totais + "\n")
    escritor = csv.DictWriter(
        saida_io,
        fieldnames=colunas,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    escritor.writeheader()

    cpfs_mascarados = 0
    for row in leitor:
        doc_bruto = row.get("CPF/CNPJ")
        _doc_tratado, tipo_doc = mascarar_documento_lgpd(doc_bruto)
        if tipo_doc in ("CPF_MASCARADO", "DOCUMENTO_MASCARADO"):
            row["CPF/CNPJ"] = "***.***.***-**"
            cpfs_mascarados += 1
        elif tipo_doc in ("CNPJ", "CNPJ_INVALIDO") and doc_bruto:
            row["CPF/CNPJ"] = doc_bruto.strip()
        escritor.writerow(row)

    return saida_io.getvalue().encode("utf-8"), cpfs_mascarados


def parse_folha_csv(
    conteudo_bytes: bytes,
    meta: MetadadosDocumentoBruto,
    *,
    resolvedor: ResolvedorVereadores | None = None,
) -> list[FolhaPagamentoRegistro]:
    """Converte um arquivo CSV mensal de folha (`servidores_cnt`) em registros tipados."""
    resolvedor = resolvedor or ResolvedorVereadores(municipio_id=meta.municipio_id)
    texto = conteudo_bytes.decode("utf-8-sig")
    linhas = [ln for ln in texto.splitlines() if ln.strip()]
    leitor = csv.DictReader(linhas, delimiter=";")

    registros: list[FolhaPagamentoRegistro] = []
    for row in leitor:
        referencia = normalizar_texto(row.get("Referência")) or ""
        ano, mes = extrair_ano_mes_referencia(referencia)
        matricula = (normalizar_texto(row.get("Matrícula")) or "").strip()
        nome_servidor = normalizar_texto(row.get("Nome")) or ""
        cargo = normalizar_texto(row.get("Cargo")) or ""
        lotacao = normalizar_texto(row.get("Lotação")) or ""
        tipo_folha = normalizar_texto(row.get("Tipo Pagamento")) or "MENSAL"

        eh_vereador = cargo.upper() == "VEREADOR"
        vereador_id: str | None = None
        gabinete_vereador_id: str | None = None

        if eh_vereador:
            res_ver = resolvedor.resolver_por_nome_ou_lotacao(nome_servidor)
            if res_ver.vereador_id is None:
                res_ver = resolvedor.resolver_por_nome_ou_lotacao(lotacao)
            vereador_id = res_ver.vereador_id
        elif lotacao.upper().startswith("GAB"):
            res_gab = resolvedor.resolver_por_nome_ou_lotacao(lotacao)
            gabinete_vereador_id = res_gab.vereador_id

        slug_tp = gerar_slug_tipo_folha(tipo_folha)
        folha_id = f"{meta.municipio_id}-folha-{ano}-{mes:02d}-{matricula}-{slug_tp}"

        registros.append(
            FolhaPagamentoRegistro(
                folha_id=folha_id,
                municipio_id=meta.municipio_id,
                ano=ano,
                mes=mes,
                referencia=referencia,
                matricula=matricula,
                nome_servidor=nome_servidor,
                cpf_mascarado="***.***.***-**",
                situacao=normalizar_texto(row.get("Situação")),
                orgao=normalizar_texto(row.get("Órgão")) or "CAMARA MUNICIPAL DE INHUMAS",
                cargo=cargo,
                funcao=normalizar_texto(row.get("Função")),
                lotacao=lotacao,
                local_trabalho=normalizar_texto(row.get("Local de Trabalho")),
                decreto_nomeacao=normalizar_texto(row.get("Decreto Nomeação")),
                possui_estabilidade=normalizar_texto(row.get("Estabilidade")),
                data_admissao=parse_data_iso(row.get("Data Admissão")),
                data_exoneracao=parse_data_iso(row.get("Data Exoneração")),
                tipo_admissao=normalizar_texto(row.get("Tipo de Admissão")),
                carga_horaria=normalizar_texto(row.get("Carga Horária")),
                tipo_folha=tipo_folha,
                movimentacao=normalizar_texto(row.get("Movimentação")),
                salario_base=parse_valor_brl(row.get("Salário Base")),
                remuneracao_bruta=parse_valor_brl(row.get("Proventos")),
                descontos=parse_valor_brl(row.get("Descontos")),
                remuneracao_liquida=parse_valor_brl(row.get("Liquido")),
                eh_vereador=eh_vereador,
                vereador_id=vereador_id,
                gabinete_vereador_id=gabinete_vereador_id,
                fonte_id=meta.fonte_id,
                fonte_url=meta.fonte_url,
                coletado_em=_coletado_em_dt(meta.coletado_em),
                hash_conteudo=meta.hash_conteudo,
                versao_coletor=meta.versao_coletor,
            )
        )

    return registros


def parse_despesas_e_diarias_csv(
    conteudo_bytes: bytes,
    meta: MetadadosDocumentoBruto,
    *,
    registros_folha: list[FolhaPagamentoRegistro] | None = None,
    resolvedor: ResolvedorVereadores | None = None,
) -> tuple[list[FornecedorRegistro], list[DespesaEmpenhoRegistro], list[DiariaRegistro]]:
    """Converte o CSV sanitizado de despesas (`cntdespesas`) em fornecedores, empenhos e diárias."""
    resolvedor = resolvedor or ResolvedorVereadores(municipio_id=meta.municipio_id)
    texto = conteudo_bytes.decode("utf-8-sig")
    linhas = [ln for ln in texto.splitlines() if ln.strip()]
    # A linha 0 contém os somatórios de rodapé/cabeçalho ("Valor Empenhado (Soma):...")
    inicio_tabela = 1 if linhas and "Valor Empenhado (Soma)" in linhas[0] else 0
    leitor = csv.DictReader(linhas[inicio_tabela:], delimiter=";")

    # Mapeia servidores da folha por chave de nome para identificar cargo/gabinete em diárias
    mapa_servidor_folha: dict[str, tuple[str, str | None]] = {}
    if registros_folha:
        for rf in registros_folha:
            ch = gerar_chave_busca(rf.nome_servidor)
            if ch and not rf.eh_vereador:
                mapa_servidor_folha[ch] = (rf.cargo, rf.gabinete_vereador_id)

    fornecedores_por_id: dict[str, FornecedorRegistro] = {}
    empenhos: list[DespesaEmpenhoRegistro] = []
    diarias: list[DiariaRegistro] = []

    for row in leitor:
        numero_emp = (normalizar_texto(row.get("Empenho")) or "").strip()
        data_emp = parse_data_iso(row.get("Data"))
        if not numero_emp or data_emp is None:
            continue

        favorecido_nome = (normalizar_texto(row.get("Favorecido")) or "").rstrip(".").strip()
        chave_fav = gerar_chave_busca(favorecido_nome)
        doc_tratado, tipo_doc = mascarar_documento_lgpd(row.get("CPF/CNPJ"))
        doc_final = doc_tratado or "***.***.***-**"

        if tipo_doc in ("CNPJ", "CNPJ_INVALIDO"):
            tipo_pessoa = "PESSOA_JURIDICA"
            cnpj_valido: bool | None = tipo_doc == "CNPJ"
            sufixo_forn = doc_final
        else:
            tipo_pessoa = "PESSOA_FISICA"
            cnpj_valido = None
            doc_final = "***.***.***-**"
            sufixo_forn = hashlib.sha256(chave_fav.encode("utf-8")).hexdigest()[:12]

        fornecedor_id = f"{meta.municipio_id}-forn-{sufixo_forn}"
        if fornecedor_id not in fornecedores_por_id:
            fornecedores_por_id[fornecedor_id] = FornecedorRegistro(
                fornecedor_id=fornecedor_id,
                municipio_id=meta.municipio_id,
                nome=favorecido_nome,
                chave_busca=chave_fav,
                documento_mascarado_ou_cnpj=doc_final,
                tipo_pessoa=tipo_pessoa,
                cnpj_valido=cnpj_valido,
                fonte_id=meta.fonte_id,
                fonte_url=meta.fonte_url,
                coletado_em=_coletado_em_dt(meta.coletado_em),
                hash_conteudo=meta.hash_conteudo,
                versao_coletor=meta.versao_coletor,
            )

        val_emp_bruto = parse_valor_brl(row.get("Empenhado")) or Decimal("0.00")
        val_anulacao = parse_valor_brl(row.get("Anulação")) or Decimal("0.00")
        val_emp_liquido = (val_emp_bruto - val_anulacao).quantize(Decimal("0.01"))
        val_liquidado = parse_valor_brl(row.get("Liquidado")) or Decimal("0.00")
        val_pago = parse_valor_brl(row.get("Pago")) or Decimal("0.00")
        val_saldo = parse_valor_brl(row.get("Saldo a Pagar")) or Decimal("0.00")

        elemento = normalizar_texto(row.get("Elemento"))
        subelemento = normalizar_texto(row.get("Subelemento"))
        historico = normalizar_texto(row.get("Descrição / Histórico")) or ""

        eh_diaria = bool(
            (elemento and "14" in elemento and "di" in elemento.lower())
            or (subelemento and "diaria" in gerar_chave_busca(subelemento))
        )

        res_ver = resolvedor.resolver_por_nome_ou_lotacao(favorecido_nome)
        vereador_beneficiario_id = res_ver.vereador_id if tipo_pessoa == "PESSOA_FISICA" else None

        empenho_id = f"{meta.municipio_id}-emp-2026-{numero_emp}"
        empenho_reg = DespesaEmpenhoRegistro(
            empenho_id=empenho_id,
            municipio_id=meta.municipio_id,
            numero_empenho=numero_emp,
            ano=data_emp.year,
            mes=data_emp.month,
            data_empenho=data_emp,
            fornecedor_id=fornecedor_id,
            favorecido_nome=favorecido_nome,
            documento_favorecido=doc_final,
            tipo_pessoa_favorecido=tipo_pessoa,
            valor_empenhado_bruto=val_emp_bruto,
            valor_anulacao=val_anulacao,
            valor_empenhado_liquido=val_emp_liquido,
            valor_liquidado=val_liquidado,
            valor_pago=val_pago,
            saldo_pagar=val_saldo,
            historico=historico,
            orgao=normalizar_texto(row.get("Órgao")),
            processo_licitatorio=normalizar_texto(row.get("Processos Licitatórios")),
            destinacao_recurso=normalizar_texto(row.get("Destinação do Recurso")),
            unidade=normalizar_texto(row.get("Unidade")),
            funcao=normalizar_texto(row.get("Função")),
            subfuncao=normalizar_texto(row.get("Subfunção")),
            programa=normalizar_texto(row.get("Programa")),
            acao=normalizar_texto(row.get("Ação")),
            categoria_economica=normalizar_texto(row.get("Categoria Econômica")),
            grupo_despesa=normalizar_texto(row.get("Grupo")),
            modalidade_aplicacao=normalizar_texto(row.get("Modalidade de Aplicação")),
            elemento_despesa=elemento,
            subelemento_despesa=subelemento,
            fonte_recurso=normalizar_texto(row.get("Fonte")),
            eh_diaria=eh_diaria,
            vereador_beneficiario_id=vereador_beneficiario_id,
            fonte_id=meta.fonte_id,
            fonte_url=meta.fonte_url,
            coletado_em=_coletado_em_dt(meta.coletado_em),
            hash_conteudo=meta.hash_conteudo,
            versao_coletor=meta.versao_coletor,
        )
        empenhos.append(empenho_reg)

        if eh_diaria:
            cargo_benef: str | None = None
            gab_ver_id: str | None = None
            if vereador_beneficiario_id is not None:
                tipo_benef = "VEREADOR"
                cargo_benef = "VEREADOR"
            elif chave_fav in mapa_servidor_folha:
                cargo_benef, gab_ver_id = mapa_servidor_folha[chave_fav]
                tipo_benef = (
                    "SERVIDOR_GABINETE" if gab_ver_id is not None else "SERVIDOR_ADMINISTRATIVO"
                )
            else:
                tipo_benef = "SERVIDOR_ADMINISTRATIVO"

            diarias.append(
                DiariaRegistro(
                    diaria_id=f"{meta.municipio_id}-diaria-2026-{numero_emp}",
                    municipio_id=meta.municipio_id,
                    empenho_id=empenho_id,
                    numero_empenho=numero_emp,
                    ano=data_emp.year,
                    mes=data_emp.month,
                    data_concessao=data_emp,
                    beneficiario_nome=favorecido_nome,
                    cpf_mascarado="***.***.***-**",
                    tipo_beneficiario=tipo_benef,
                    vereador_id_verificado=vereador_beneficiario_id,
                    gabinete_vereador_id=gab_ver_id,
                    cargo_beneficiario=cargo_benef,
                    identificacao_documental_verificavel=True,
                    destino_ou_finalidade=historico,
                    valor_empenhado_liquido=val_emp_liquido,
                    valor_liquidado=val_liquidado,
                    valor_pago=val_pago,
                    origem_registro="EMPENHO_ELEMENTO_14_CNTDESPESAS",
                    fonte_id=meta.fonte_id,
                    fonte_url=meta.fonte_url,
                    coletado_em=meta.coletado_em,
                    hash_conteudo=meta.hash_conteudo,
                    versao_coletor=meta.versao_coletor,
                )
            )

    return list(fornecedores_por_id.values()), empenhos, diarias


def parse_duodecimo_json(
    payload: dict[str, Any],
    meta: MetadadosDocumentoBruto,
) -> list[DuodecimoRegistro]:
    """Converte o JSON de `sgduodecimo` em registros tipados."""
    dados = payload.get("dados", [])
    registros: list[DuodecimoRegistro] = []
    for item in dados:
        id_origem = str(item["id"]).strip()
        ano = int(item["ano"])
        mes = int(item["mes"])
        data_lanc = parse_data_iso(item.get("data"))
        if data_lanc is None:
            continue
        tipo_cod = str(item.get("tipo", "1")).strip()
        tipo_nat = "RECEITA_REPASSE" if tipo_cod == "1" else "DEVOLUCAO_DUODECIMO"
        valor = parse_valor_brl(item.get("valor"))
        if valor is None:
            continue
        registros.append(
            DuodecimoRegistro(
                duodecimo_id=f"{meta.municipio_id}-duodecimo-{id_origem}",
                municipio_id=meta.municipio_id,
                id_origem=id_origem,
                ano=ano,
                mes=mes,
                data_lancamento=data_lanc,
                tipo_codigo=tipo_cod,
                tipo_natureza=tipo_nat,
                descricao=normalizar_texto(item.get("descricao")) or "",
                valor=valor,
                arquivo_nome=normalizar_texto(item.get("file")),
                fonte_id=meta.fonte_id,
                fonte_url=meta.fonte_url,
                coletado_em=_coletado_em_dt(meta.coletado_em),
                hash_conteudo=meta.hash_conteudo,
                versao_coletor=meta.versao_coletor,
            )
        )
    return registros


def parse_declaracoes_json(
    payload_ceap: dict[str, Any],
    meta_ceap: MetadadosDocumentoBruto,
    payload_diarias: dict[str, Any],
    meta_diarias: MetadadosDocumentoBruto,
) -> list[DeclaracaoTransparenciaRegistro]:
    """Extrai as declarações formais de inexistência de cota parlamentar e de diárias."""
    ceap_item = payload_ceap["dados"][0]
    reg_ceap = DeclaracaoTransparenciaRegistro(
        declaracao_id=f"{meta_ceap.municipio_id}-decl-ceap-2020-2026",
        municipio_id=meta_ceap.municipio_id,
        tipo_declaracao="INEXISTENCIA_COTA_PARLAMENTAR",
        titulo_oficial=normalizar_texto(ceap_item.get("titulo"))
        or "Inexistência de cotas e gastos parlamentares",
        texto_integral=normalizar_texto(ceap_item.get("descricao")) or NOTA_OFICIAL_CEAP,
        data_inicio_cobertura=parse_data_iso(ceap_item.get("data_inicio")) or parse_data_iso("2020-01-01"),  # type: ignore[arg-type]
        data_fim_cobertura=parse_data_iso(ceap_item.get("data_fim")) or parse_data_iso("2026-10-22"),  # type: ignore[arg-type]
        data_atualizacao=parse_data_iso(ceap_item.get("data_atualizacao")),
        signatario_presidente=normalizar_texto(ceap_item.get("presidente")),
        signatario_certificador=normalizar_texto(ceap_item.get("certificador")),
        observacao_cruzamento=(
            "Confirmado no módulo sggastosparlamentares e em /cidadao/p/declaracao/11: "
            "a Câmara Municipal de Inhumas não possui legislação vigente nem previsão de "
            "cota para exercício da atividade parlamentar (CEAP) ou verbas indenizatórias."
        ),
        fonte_id=meta_ceap.fonte_id,
        fonte_url=meta_ceap.fonte_url,
        coletado_em=_coletado_em_dt(meta_ceap.coletado_em),
        hash_conteudo=meta_ceap.hash_conteudo,
        versao_coletor=meta_ceap.versao_coletor,
    )

    decl_d = payload_diarias["declaracao_oficial_nao_concessao"]
    reg_diarias = DeclaracaoTransparenciaRegistro(
        declaracao_id=f"{meta_diarias.municipio_id}-decl-diarias-2026",
        municipio_id=meta_diarias.municipio_id,
        tipo_declaracao="NAO_CONCESSAO_DIARIAS",
        titulo_oficial=normalizar_texto(decl_d.get("titulo"))
        or 'Declaração de "Não Concessão de Diárias"',
        texto_integral=normalizar_texto(decl_d.get("texto_declaracao")) or "",
        data_inicio_cobertura=parse_data_iso("2026-03-01"),  # type: ignore[arg-type]
        data_fim_cobertura=parse_data_iso("2026-10-22"),  # type: ignore[arg-type]
        data_atualizacao=parse_data_iso("2026-10-22"),
        signatario_presidente=normalizar_texto(decl_d.get("presidente")),
        signatario_certificador=normalizar_texto(decl_d.get("certificador")),
        observacao_cruzamento=(
            "Embora o submódulo específico cntdiarias (acao=diarias) retorne 0 registros para 2026, "
            "o cruzamento contábil com o módulo de empenhos (cntdespesas, Elemento 14 - Diárias – Civil) "
            "identificou 14 empenhos de diárias em 2026 (R$ 6.600,00 pagos), sendo 4 diretamente em nome "
            "de vereadores (jan e fev/2026, totalizando R$ 1.600,00) e 10 em nome de servidores."
        ),
        fonte_id=meta_diarias.fonte_id,
        fonte_url=meta_diarias.fonte_url,
        coletado_em=_coletado_em_dt(meta_diarias.coletado_em),
        hash_conteudo=meta_diarias.hash_conteudo,
        versao_coletor=meta_diarias.versao_coletor,
    )
    return [reg_ceap, reg_diarias]


def gerar_custo_estrutura_mandato_2026(
    *,
    municipio_id: str,
    registros_folha: list[FolhaPagamentoRegistro],
    registros_diarias: list[DiariaRegistro],
    meta_referencia: MetadadosDocumentoBruto,
    ano: int = 2026,
) -> list[CustoEstruturaMandatoMensalRegistro]:
    """Calcula a série mensal (meses 1..12 de 2026) do Custo da Estrutura do Mandato para os 15 vereadores titulares.

    Regras de negócio aplicadas (ADR-005):
    - Competências fechadas no portal (`01/2026` a `10/2026`): calcula Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis.
    - Para o Presidente da Câmara (`inhumas-go-ver-81`, Hugo Pessoni), que está lotado na unidade institucional
      `'PRESIDENCIA'` sem lotação apartada `'GAB. DO VEREADOR ...'` no sistema CENTI, preserva `folha_bruta_gabinete = None`
      e `custo_estrutura_mandato_total = None` (status `'LACUNA_PARCIAL_LOTACAO'`), nunca atribuindo indevidamente a folha
      institucional da Presidência nem convertendo a ausência de gabinete individual em zero.
    - Competências ainda abertas/sem publicação (`11/2026` e `12/2026`): preserva todos os valores como `None` (`NULL`),
      com `competencia_status = 'ABERTA_SEM_PUBLICACAO'`.
    """
    # Vereadores titulares da 20ª Legislatura (exceto suplente de 2025 Weber Enxovais, que não exerceu em 2026)
    vereadores_2026 = [
        seed.vereador_id
        for seed in VEREADORES_MESTRE_INHUMAS
        if seed.vereador_id != "inhumas-go-ver-246"
    ]

    meses_com_folha = {rf.mes for rf in registros_folha if rf.ano == ano}

    # Agrupa folhas de vereador e de gabinete
    folhas_vereador_por_mes: dict[tuple[str, int], list[FolhaPagamentoRegistro]] = defaultdict(list)
    itens_gabinete_por_mes: dict[int, list[FolhaServidorItem]] = defaultdict(list)
    folhas_gabinete_raw_por_ver_mes: dict[tuple[str, int], list[FolhaPagamentoRegistro]] = (
        defaultdict(list)
    )

    for rf in registros_folha:
        if rf.ano != ano:
            continue
        if rf.eh_vereador and rf.vereador_id:
            folhas_vereador_por_mes[(rf.vereador_id, rf.mes)].append(rf)
        elif not rf.eh_vereador and rf.gabinete_vereador_id:
            folhas_gabinete_raw_por_ver_mes[(rf.gabinete_vereador_id, rf.mes)].append(rf)
            itens_gabinete_por_mes[rf.mes].append(
                FolhaServidorItem(
                    matricula=rf.matricula,
                    nome_servidor=rf.nome_servidor,
                    lotacao=rf.lotacao,
                    vereador_id_atribuido=rf.gabinete_vereador_id,
                    competencia_ano=rf.ano,
                    competencia_mes=rf.mes,
                    proventos_brutos=rf.remuneracao_bruta,
                    vigencia_inicio=rf.data_admissao,
                    vigencia_fim=rf.data_exoneracao,
                    tipo_folha=rf.tipo_folha,
                )
            )

    itens_diarias_all: list[DiariaItem] = [
        DiariaItem(
            diaria_id=d.diaria_id,
            beneficiario_nome=d.beneficiario_nome,
            vereador_id_verificado=d.vereador_id_verificado,
            identificacao_documental_verificavel=d.identificacao_documental_verificavel,
            data_pagamento=d.data_concessao,
            valor_empenhado_liquido=d.valor_empenhado_liquido,
            valor_liquidado=d.valor_liquidado,
            valor_pago=d.valor_pago,
        )
        for d in registros_diarias
        if d.ano == ano
    ]

    resultados: list[CustoEstruturaMandatoMensalRegistro] = []

    for vereador_id in vereadores_2026:
        eh_presidente_sem_gabinete_individual = vereador_id == "inhumas-go-ver-81"

        for mes in range(1, 13):
            custo_id = f"{municipio_id}-custo-{vereador_id}-{ano}-{mes:02d}"

            if mes not in meses_com_folha:
                # Competência ainda não encerrada/publicada no portal: preserva NULL em todos os valores
                res_aberta = calcular_custo_estrutura_mandato(
                    municipio_id=municipio_id,
                    vereador_id=vereador_id,
                    competencia_ano=ano,
                    competencia_mes=mes,
                    subsidio_bruto_vereador=None,
                    itens_folha_gabinete=None,
                    itens_diarias=None,
                    fonte_url=meta_referencia.fonte_url,
                )
                resultados.append(
                    CustoEstruturaMandatoMensalRegistro(
                        custo_mensal_id=custo_id,
                        municipio_id=municipio_id,
                        vereador_id=vereador_id,
                        ano=ano,
                        mes=mes,
                        competencia_status="ABERTA_SEM_PUBLICACAO",
                        subsidio_bruto_vereador=None,
                        subsidio_mensal_base=None,
                        adicionais_ferias_decimo_terceiro_vereador=None,
                        folha_bruta_gabinete=None,
                        folha_mensal_gabinete=None,
                        adicionais_ferias_decimo_terceiro_gabinete=None,
                        quantidade_servidores_gabinete=None,
                        diarias_atribuiveis_empenhadas=None,
                        diarias_atribuiveis_liquidadas=None,
                        diarias_atribuiveis_pagas=None,
                        custo_estrutura_mandato_total=None,
                        nota_cota_parlamentar=res_aberta.nota_cota_parlamentar,
                        periodo_declaracao_ceap=res_aberta.periodo_declaracao_ceap,
                        metodologia_resumo=res_aberta.metodologia_resumo,
                        limitacoes_dados=(
                            f"Competência {mes:02d}/{ano} ainda não encerrada/publicada no Portal da Transparência CENTI "
                            "até a data da coleta (12/11/2026). Valores mantidos como NULL (nunca convertidos em zero)."
                        ),
                        avisos=res_aberta.avisos,
                        fonte_id=meta_referencia.fonte_id,
                        fonte_url=meta_referencia.fonte_url,
                        coletado_em=_coletado_em_dt(meta_referencia.coletado_em),
                        hash_conteudo=meta_referencia.hash_conteudo,
                        versao_coletor=meta_referencia.versao_coletor,
                    )
                )
                continue

            folhas_ver = folhas_vereador_por_mes.get((vereador_id, mes), [])
            if not folhas_ver:
                subsidio_bruto: Decimal | None = None
                subsidio_mensal: Decimal | None = None
                adicionais_ver: Decimal | None = None
            else:
                subsidio_bruto = sum(
                    ((f.remuneracao_bruta or Decimal("0.00")) for f in folhas_ver),
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
                subsidio_mensal = sum(
                    (
                        (f.remuneracao_bruta or Decimal("0.00"))
                        for f in folhas_ver
                        if f.tipo_folha.upper() == "MENSAL"
                    ),
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
                adicionais_ver = sum(
                    (
                        (f.remuneracao_bruta or Decimal("0.00"))
                        for f in folhas_ver
                        if f.tipo_folha.upper() != "MENSAL"
                    ),
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))

            itens_gab_input: list[FolhaServidorItem] | None = (
                None if eh_presidente_sem_gabinete_individual else itens_gabinete_por_mes.get(mes, [])
            )

            res_calc = calcular_custo_estrutura_mandato(
                municipio_id=municipio_id,
                vereador_id=vereador_id,
                competencia_ano=ano,
                competencia_mes=mes,
                subsidio_bruto_vereador=subsidio_bruto,
                itens_folha_gabinete=itens_gab_input,
                itens_diarias=itens_diarias_all,
                fonte_url=meta_referencia.fonte_url,
            )

            if eh_presidente_sem_gabinete_individual:
                folha_mensal_gab: Decimal | None = None
                adicionais_gab: Decimal | None = None
                status_comp = "LACUNA_PARCIAL_LOTACAO"
                limitacoes = (
                    "No sistema CENTI da Câmara Municipal de Inhumas, o Presidente da Câmara "
                    "(Hugo Leonardo Pessoni) está lotado na unidade institucional 'PRESIDENCIA' "
                    "(junto à Assessoria Jurídica, Comunicação e Chefia da Presidência), sem "
                    "lotação apartada 'GAB. DO VEREADOR HUGO PESSONI'. Para evitar atribuir a "
                    "estrutura administrativa da Presidência ao mandato individual ou converter "
                    "dado ausente em zero, a Folha Bruta do Gabinete e o Custo Total permanecem NULL."
                )
                avisos_finais = [
                    *res_calc.avisos,
                    (
                        "Lotação individual de gabinete ausente para o Presidente da Câmara ('PRESIDENCIA'); "
                        "folha_bruta_gabinete preservada como NULL."
                    ),
                ]
            else:
                folhas_gab_raw = folhas_gabinete_raw_por_ver_mes.get((vereador_id, mes), [])
                folha_mensal_gab = sum(
                    (
                        (f.remuneracao_bruta or Decimal("0.00"))
                        for f in folhas_gab_raw
                        if f.tipo_folha.upper() == "MENSAL"
                    ),
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
                adicionais_gab = sum(
                    (
                        (f.remuneracao_bruta or Decimal("0.00"))
                        for f in folhas_gab_raw
                        if f.tipo_folha.upper() != "MENSAL"
                    ),
                    Decimal("0.00"),
                ).quantize(Decimal("0.01"))
                status_comp = "FECHADA"
                limitacoes = (
                    "Inclui proventos brutos registrados na folha oficial (mensal, férias em jan/2026 e "
                    "adiantamentos de 13º salário quando ocorridos na competência). Não inclui encargos "
                    "patronais (INSS patronal) por serem contabilizados de forma agregada pela Câmara. "
                    "Diárias apuradas pelo cruzamento contábil com os empenhos do Elemento 14 (Diárias - Civil)."
                )
                avisos_finais = list(res_calc.avisos)

            resultados.append(
                CustoEstruturaMandatoMensalRegistro(
                    custo_mensal_id=custo_id,
                    municipio_id=municipio_id,
                    vereador_id=vereador_id,
                    ano=ano,
                    mes=mes,
                    competencia_status=status_comp,
                    subsidio_bruto_vereador=res_calc.subsidio_bruto_vereador,
                    subsidio_mensal_base=subsidio_mensal,
                    adicionais_ferias_decimo_terceiro_vereador=adicionais_ver,
                    folha_bruta_gabinete=res_calc.folha_bruta_gabinete,
                    folha_mensal_gabinete=folha_mensal_gab,
                    adicionais_ferias_decimo_terceiro_gabinete=adicionais_gab,
                    quantidade_servidores_gabinete=res_calc.quantidade_servidores_gabinete,
                    diarias_atribuiveis_empenhadas=res_calc.diarias_atribuiveis_empenhadas,
                    diarias_atribuiveis_liquidadas=res_calc.diarias_atribuiveis_liquidadas,
                    diarias_atribuiveis_pagas=res_calc.diarias_atribuiveis_pagas,
                    custo_estrutura_mandato_total=res_calc.custo_estrutura_mandato_total,
                    nota_cota_parlamentar=res_calc.nota_cota_parlamentar,
                    periodo_declaracao_ceap=res_calc.periodo_declaracao_ceap,
                    metodologia_resumo=res_calc.metodologia_resumo,
                    limitacoes_dados=limitacoes,
                    avisos=avisos_finais,
                    fonte_id=meta_referencia.fonte_id,
                    fonte_url=meta_referencia.fonte_url,
                    coletado_em=_coletado_em_dt(meta_referencia.coletado_em),
                    hash_conteudo=meta_referencia.hash_conteudo,
                    versao_coletor=meta_referencia.versao_coletor,
                )
            )

    return resultados
