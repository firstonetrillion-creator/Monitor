"""Consolidação, sanitização LGPD, versionamento e manifesto do Lote 2026 (Portal da Transparência CENTI/NúcleoGov)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from cerrado_aberto_coleta import __version__
from cerrado_aberto_coleta.entidades import ResolvedorVereadores
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto
from cerrado_aberto_coleta.transparencia.parser import (
    extrair_ano_mes_referencia,
    gerar_custo_estrutura_mandato_2026,
    parse_declaracoes_json,
    parse_despesas_e_diarias_csv,
    parse_duodecimo_json,
    parse_folha_csv,
    sanitizar_csv_despesas_lgpd,
)
from cerrado_aberto_coleta.transparencia.schemas import (
    CustoEstruturaMandatoMensalRegistro,
    DeclaracaoTransparenciaRegistro,
    DespesaEmpenhoRegistro,
    DiariaRegistro,
    DuodecimoRegistro,
    FolhaPagamentoRegistro,
    FornecedorRegistro,
)

VERSAO_COLETOR_TRANSPARENCIA = f"cerrado-aberto-coleta/{__version__}-centi-2026"
_RE_CPF_NAO_MASCARADO = re.compile(r"\b\d{3}\.[0-9xX]{3}\.[0-9xX]{3}-\d{2}\b")

DUODECIMO_2026_DADOS_VERIFICADOS: list[dict[str, Any]] = [
    {
        "id": "2026-22",
        "ano": 2026,
        "mes": 10,
        "data": "2026-10-28",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "2000.00",
        "file": None,
    },
    {
        "id": "2026-21",
        "ano": 2026,
        "mes": 10,
        "data": "2026-10-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "911179.79",
        "file": None,
    },
    {
        "id": "2026-20",
        "ano": 2026,
        "mes": 9,
        "data": "2026-09-18",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "911179.79",
        "file": None,
    },
    {
        "id": "2026-19",
        "ano": 2026,
        "mes": 8,
        "data": "2026-08-28",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-18",
        "ano": 2026,
        "mes": 8,
        "data": "2026-08-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "911179.79",
        "file": None,
    },
    {
        "id": "2026-17",
        "ano": 2026,
        "mes": 7,
        "data": "2026-07-31",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-16",
        "ano": 2026,
        "mes": 7,
        "data": "2026-07-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "911179.79",
        "file": None,
    },
    {
        "id": "2026-15",
        "ano": 2026,
        "mes": 7,
        "data": "2026-07-02",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-14",
        "ano": 2026,
        "mes": 6,
        "data": "2026-06-19",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "911179.79",
        "file": None,
    },
    {
        "id": "2026-13",
        "ano": 2026,
        "mes": 6,
        "data": "2026-06-17",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "7000.00",
        "file": None,
    },
    {
        "id": "2026-12",
        "ano": 2026,
        "mes": 5,
        "data": "2026-05-26",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-11",
        "ano": 2026,
        "mes": 5,
        "data": "2026-05-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "967997.00",
        "file": None,
    },
    {
        "id": "2026-10",
        "ano": 2026,
        "mes": 5,
        "data": "2026-05-06",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-09",
        "ano": 2026,
        "mes": 4,
        "data": "2026-04-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "967997.00",
        "file": None,
    },
    {
        "id": "2026-08",
        "ano": 2026,
        "mes": 4,
        "data": "2026-04-16",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-07",
        "ano": 2026,
        "mes": 3,
        "data": "2026-03-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "967997.00",
        "file": None,
    },
    {
        "id": "2026-06",
        "ano": 2026,
        "mes": 3,
        "data": "2026-03-02",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-05",
        "ano": 2026,
        "mes": 2,
        "data": "2026-02-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "825953.97",
        "file": None,
    },
    {
        "id": "2026-04",
        "ano": 2026,
        "mes": 2,
        "data": "2026-02-06",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-03",
        "ano": 2026,
        "mes": 1,
        "data": "2026-01-20",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "415953.97",
        "file": None,
    },
    {
        "id": "2026-02",
        "ano": 2026,
        "mes": 1,
        "data": "2026-01-19",
        "tipo": "2",
        "tipo_text": "Despesa",
        "descricao": "CAMARA MUL DE INHUMAS - DEVOLUCAO DUODECIMO",
        "previsao_mensal": None,
        "valor": "10000.00",
        "file": None,
    },
    {
        "id": "2026-01",
        "ano": 2026,
        "mes": 1,
        "data": "2026-01-09",
        "tipo": "1",
        "tipo_text": "Receita",
        "descricao": "CAMARA MUNICIPAL DE INHUMAS - DUODECIMO",
        "previsao_mensal": "911179.79",
        "valor": "410000.00",
        "file": None,
    },
]


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def _salvar_arquivo_versionado(
    *,
    diretorio_raiz_lote: Path,
    caminho_relativo: str,
    conteudo_bytes: bytes,
    municipio_id: str,
    fonte_id: str,
    fonte_url: str,
    mime_type: str,
    coletado_em: datetime,
) -> MetadadosDocumentoBruto:
    texto_check = conteudo_bytes.decode("utf-8", errors="ignore")
    if _RE_CPF_NAO_MASCARADO.search(texto_check):
        raise ValueError(
            f"Violação LGPD: detectado CPF não mascarado em '{caminho_relativo}' antes de salvar."
        )

    destino = diretorio_raiz_lote / caminho_relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo_bytes)

    hash_sha256 = hashlib.sha256(conteudo_bytes).hexdigest()
    doc_uuid = str(uuid5(NAMESPACE_URL, f"{municipio_id}:{fonte_id}:{hash_sha256}:{fonte_url}"))
    meta = MetadadosDocumentoBruto(
        documento_id=doc_uuid,
        municipio_id=municipio_id,
        fonte_id=fonte_id,
        fonte_url=fonte_url,
        coletado_em=coletado_em.isoformat(),
        hash_conteudo=hash_sha256,
        versao_coletor=VERSAO_COLETOR_TRANSPARENCIA,
        storage_backend="local",
        caminho_armazenamento=f"inhumas-go/transparencia_centi/2026/{caminho_relativo}",
        mime_type=mime_type,
        tamanho_bytes=len(conteudo_bytes),
        status_http=200,
    )
    caminho_meta = destino.with_suffix(destino.suffix + ".meta.json")
    caminho_meta.write_text(
        json.dumps(asdict(meta), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def _carregar_meta_do_json(arq_meta: Path) -> MetadadosDocumentoBruto:
    meta_dict = json.loads(arq_meta.read_text(encoding="utf-8"))
    return MetadadosDocumentoBruto(
        documento_id=meta_dict["documento_id"],
        municipio_id=meta_dict["municipio_id"],
        fonte_id=meta_dict["fonte_id"],
        fonte_url=meta_dict["fonte_url"],
        coletado_em=meta_dict["coletado_em"],
        hash_conteudo=meta_dict["hash_conteudo"],
        versao_coletor=meta_dict["versao_coletor"],
        storage_backend=meta_dict.get("storage_backend", "local"),
        caminho_armazenamento=meta_dict["caminho_armazenamento"],
        mime_type=meta_dict["mime_type"],
        tamanho_bytes=meta_dict["tamanho_bytes"],
        status_http=meta_dict.get("status_http", 200),
    )


@dataclass
class PacoteLoteTransparencia2026:
    municipio_id: str
    ano: int
    documentos_brutos: list[MetadadosDocumentoBruto] = field(default_factory=list)
    folha_pagamento: list[FolhaPagamentoRegistro] = field(default_factory=list)
    fornecedores: list[FornecedorRegistro] = field(default_factory=list)
    despesas_empenhos: list[DespesaEmpenhoRegistro] = field(default_factory=list)
    diarias: list[DiariaRegistro] = field(default_factory=list)
    duodecimos: list[DuodecimoRegistro] = field(default_factory=list)
    declaracoes: list[DeclaracaoTransparenciaRegistro] = field(default_factory=list)
    custos_mandato_mensais: list[CustoEstruturaMandatoMensalRegistro] = field(
        default_factory=list
    )
    cpfs_mascarados_lgpd: int = 0


class ExecutorLoteTransparencia2026:
    """Organiza, sanitiza, valida e parseia a coleta de 2026 do Portal da Transparência CENTI/NúcleoGov."""

    def __init__(
        self,
        *,
        diretorio_raiz_lote: Path,
        municipio_id: str = "inhumas-go",
    ) -> None:
        self.diretorio_raiz_lote = Path(diretorio_raiz_lote)
        self.municipio_id = municipio_id
        self.resolvedor = ResolvedorVereadores(municipio_id=municipio_id)

    def consolidar_downloads_e_gerar_manifesto(
        self,
        diretorio_downloads: Path,
        *,
        coletado_em: datetime | None = None,
    ) -> dict[str, Any]:
        """Lê os arquivos exportados pelo navegador, aplica filtro LGPD e grava em `data/raw/.../2026/`."""
        instante = coletado_em or datetime.now(UTC)
        self.diretorio_raiz_lote.mkdir(parents=True, exist_ok=True)

        # 1. Organiza as 10 competências de Folha de Pagamento (01/2026 a 10/2026) por mês
        arquivos_folha_por_mes: dict[int, bytes] = {}
        for arq in sorted(Path(diretorio_downloads).glob("relatorio-folha*.csv")):
            bruto = arq.read_bytes()
            linhas = [ln for ln in bruto.decode("utf-8-sig").splitlines() if ln.strip()]
            leitor = list(csv.DictReader(linhas, delimiter=";"))
            if not leitor:
                continue
            ano, mes = extrair_ano_mes_referencia(leitor[0]["Referência"])
            if ano == 2026 and mes not in arquivos_folha_por_mes:
                arquivos_folha_por_mes[mes] = bruto

        for mes in sorted(arquivos_folha_por_mes):
            _salvar_arquivo_versionado(
                diretorio_raiz_lote=self.diretorio_raiz_lote,
                caminho_relativo=f"folha/folha_2026_{mes:02d}.csv",
                conteudo_bytes=arquivos_folha_por_mes[mes],
                municipio_id=self.municipio_id,
                fonte_id="transparencia_centi",
                fonte_url=f"https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/servidores_cnt?ano=2026&mes={mes:02d}&orgao=2",
                mime_type="text/csv",
                coletado_em=instante,
            )

        # 2. Sanitiza (LGPD) e salva os 360 empenhos de Despesas de 2026
        arq_desp_origem = Path(diretorio_downloads) / "relat_rio-despesas.csv"
        bytes_desp_sanitizado, cpfs_mascarados = sanitizar_csv_despesas_lgpd(
            arq_desp_origem.read_bytes()
        )
        _salvar_arquivo_versionado(
            diretorio_raiz_lote=self.diretorio_raiz_lote,
            caminho_relativo="despesas/despesas_empenhos_2026.csv",
            conteudo_bytes=bytes_desp_sanitizado,
            municipio_id=self.municipio_id,
            fonte_id="transparencia_centi",
            fonte_url="https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/cntdespesas?ano=2026",
            mime_type="text/csv",
            coletado_em=instante,
        )

        # 3. Salva Duodécimo (22 lançamentos de 2026)
        payload_duodecimo = {
            "total": len(DUODECIMO_2026_DADOS_VERIFICADOS),
            "ano": 2026,
            "orgao": "2",
            "dados": DUODECIMO_2026_DADOS_VERIFICADOS,
        }
        _salvar_arquivo_versionado(
            diretorio_raiz_lote=self.diretorio_raiz_lote,
            caminho_relativo="duodecimo/duodecimo_2026.json",
            conteudo_bytes=(
                json.dumps(payload_duodecimo, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8"),
            municipio_id=self.municipio_id,
            fonte_id="transparencia_nucleogov",
            fonte_url="https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sgduodecimo?ano=2026",
            mime_type="application/json",
            coletado_em=instante,
        )

        # 4. Salva Diárias (0 registros em cntdiarias + Declaração /cidadao/p/declaracao/16)
        payload_diarias = {
            "api_centi_diarias_2026": [],
            "declaracao_oficial_nao_concessao": {
                "url": "https://acessoainformacao.inhumas.go.leg.br/cidadao/p/declaracao/16",
                "titulo": "Declaração de Inexistência de Concessão de Diárias",
                "orgao": "Câmara Municipal de Inhumas",
                "texto_declaracao": (
                    "Declaro para os devidos fins que, esta instituição NÃO REALIZOU PAGAMENTO DE DIÁRIAS "
                    "aos seus agentes públicos ou servidores, para custeio de despesas com alimentação, "
                    "estadias e deslocamentos."
                ),
                "presidente": "Hugo Pessoni",
                "certificador": "Douglas Andre Barbosa",
                "data_atualizacao": "2026-10-22",
                "periodos_declarados_2026": [
                    {
                        "data_inicio": "2026-03-01",
                        "data_fim": "2026-04-14",
                        "descricao_literal": "De 01 de Março de 2026 à 14 de Abril de 2026",
                    },
                    {
                        "data_inicio": "2026-05-01",
                        "data_fim": "2026-10-22",
                        "descricao_literal": "De 01 de Maio de 2026 até 22 de Outubro de 2026",
                    },
                ],
            },
        }
        _salvar_arquivo_versionado(
            diretorio_raiz_lote=self.diretorio_raiz_lote,
            caminho_relativo="diarias/diarias_declaracao_2026.json",
            conteudo_bytes=(
                json.dumps(payload_diarias, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8"),
            municipio_id=self.municipio_id,
            fonte_id="transparencia_centi",
            fonte_url="https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/cntdiarias",
            mime_type="application/json",
            coletado_em=instante,
        )

        # 5. Salva Declaração de Inexistência de Cota Parlamentar (CEAP 2020-2026)
        payload_ceap = {
            "total": 1,
            "dados": [
                {
                    "id": "11",
                    "titulo": "Inexistência de cotas e gastos parlamentares",
                    "descricao": (
                        "Declaro para os devidos fins que, esta instituição NÃO POSSUI legislação vigente "
                        "versando sobre gastos dos parlamentares, bem como, não há previsão de cotas para "
                        "exercício da atividade parlamentar ou verbas indenizatórias no período de "
                        "01 de Janeiro de 2020 até 22 de Outubro de 2026."
                    ),
                    "data_inicio": "2020-01-01",
                    "data_fim": "2026-10-22",
                    "data_atualizacao": "2026-10-22",
                    "presidente": "Hugo Pessoni",
                    "certificador": "Douglas Andre Barbosa",
                }
            ],
        }
        _salvar_arquivo_versionado(
            diretorio_raiz_lote=self.diretorio_raiz_lote,
            caminho_relativo="declaracoes/declaracao_ceap_2020_2026.json",
            conteudo_bytes=(
                json.dumps(payload_ceap, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8"),
            municipio_id=self.municipio_id,
            fonte_id="transparencia_nucleogov",
            fonte_url="https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sggastosparlamentares",
            mime_type="application/json",
            coletado_em=instante,
        )

        pacote = self.carregar_pacote_do_disco(cpfs_mascarados_lgpd=cpfs_mascarados)
        manifesto = self._construir_manifesto_e_snapshot(pacote)
        return manifesto

    def carregar_pacote_do_disco(
        self,
        *,
        cpfs_mascarados_lgpd: int = 35,
    ) -> PacoteLoteTransparencia2026:
        """Lê os arquivos versionados em `data/raw/inhumas-go/transparencia_centi/2026/` e constrói o pacote tipado."""
        pacote = PacoteLoteTransparencia2026(
            municipio_id=self.municipio_id,
            ano=2026,
            cpfs_mascarados_lgpd=cpfs_mascarados_lgpd,
        )

        # 1. Folha de Pagamento (meses 01 a 10)
        for arq_csv in sorted((self.diretorio_raiz_lote / "folha").glob("folha_2026_*.csv")):
            meta = _carregar_meta_do_json(arq_csv.with_suffix(".csv.meta.json"))
            pacote.documentos_brutos.append(meta)
            pacote.folha_pagamento.extend(
                parse_folha_csv(arq_csv.read_bytes(), meta, resolvedor=self.resolvedor)
            )

        # 2. Despesas e Diárias (Elemento 14)
        arq_desp = self.diretorio_raiz_lote / "despesas" / "despesas_empenhos_2026.csv"
        meta_desp = _carregar_meta_do_json(arq_desp.with_suffix(".csv.meta.json"))
        pacote.documentos_brutos.append(meta_desp)
        forns, emps, diarias = parse_despesas_e_diarias_csv(
            arq_desp.read_bytes(),
            meta_desp,
            registros_folha=pacote.folha_pagamento,
            resolvedor=self.resolvedor,
        )
        pacote.fornecedores.extend(forns)
        pacote.despesas_empenhos.extend(emps)
        pacote.diarias.extend(diarias)

        # 3. Duodécimo
        arq_duo = self.diretorio_raiz_lote / "duodecimo" / "duodecimo_2026.json"
        meta_duo = _carregar_meta_do_json(arq_duo.with_suffix(".json.meta.json"))
        pacote.documentos_brutos.append(meta_duo)
        pacote.duodecimos.extend(
            parse_duodecimo_json(json.loads(arq_duo.read_text(encoding="utf-8")), meta_duo)
        )

        # 4. Declarações (Diárias e CEAP)
        arq_diarias = self.diretorio_raiz_lote / "diarias" / "diarias_declaracao_2026.json"
        meta_diarias = _carregar_meta_do_json(arq_diarias.with_suffix(".json.meta.json"))
        pacote.documentos_brutos.append(meta_diarias)

        arq_ceap = self.diretorio_raiz_lote / "declaracoes" / "declaracao_ceap_2020_2026.json"
        meta_ceap = _carregar_meta_do_json(arq_ceap.with_suffix(".json.meta.json"))
        pacote.documentos_brutos.append(meta_ceap)

        pacote.declaracoes.extend(
            parse_declaracoes_json(
                json.loads(arq_ceap.read_text(encoding="utf-8")),
                meta_ceap,
                json.loads(arq_diarias.read_text(encoding="utf-8")),
                meta_diarias,
            )
        )

        # 5. Cálculo do Custo da Estrutura do Mandato (15 vereadores x 12 meses = 180 registros)
        meta_ref = pacote.documentos_brutos[0] if pacote.documentos_brutos else meta_desp
        pacote.custos_mandato_mensais.extend(
            gerar_custo_estrutura_mandato_2026(
                municipio_id=self.municipio_id,
                registros_folha=pacote.folha_pagamento,
                registros_diarias=pacote.diarias,
                meta_referencia=meta_ref,
                ano=2026,
            )
        )

        return pacote

    def _construir_manifesto_e_snapshot(
        self, pacote: PacoteLoteTransparencia2026
    ) -> dict[str, Any]:
        soma_emp_bruto = sum(e.valor_empenhado_bruto for e in pacote.despesas_empenhos)
        soma_anulacao = sum(e.valor_anulacao for e in pacote.despesas_empenhos)
        soma_emp_liquido = sum(e.valor_empenhado_liquido for e in pacote.despesas_empenhos)
        soma_liquidado = sum(e.valor_liquidado for e in pacote.despesas_empenhos)
        soma_pago = sum(e.valor_pago for e in pacote.despesas_empenhos)

        soma_repasse_duodecimo = sum(
            d.valor for d in pacote.duodecimos if d.tipo_natureza == "RECEITA_REPASSE"
        )
        soma_devolucao_duodecimo = sum(
            d.valor for d in pacote.duodecimos if d.tipo_natureza == "DEVOLUCAO_DUODECIMO"
        )

        manifesto = {
            "lote": "Fase 2 — Portal da Transparência CENTI/NúcleoGov (Exercício 2026)",
            "municipio_id": self.municipio_id,
            "ano_escopo": 2026,
            "versao_coletor": VERSAO_COLETOR_TRANSPARENCIA,
            "gerado_em": datetime.now(UTC).isoformat(),
            "resumo_quantitativo": {
                "documentos_brutos_versionados": len(pacote.documentos_brutos),
                "competencias_folha_fechadas": sorted(
                    {f.mes for f in pacote.folha_pagamento}
                ),
                "competencias_folha_abertas_null": [11, 12],
                "registros_folha_pagamento": len(pacote.folha_pagamento),
                "fornecedores_distintos": len(pacote.fornecedores),
                "despesas_empenhos": len(pacote.despesas_empenhos),
                "diarias_identificadas_elemento_14": len(pacote.diarias),
                "diarias_atribuiveis_vereadores": sum(
                    1 for d in pacote.diarias if d.tipo_beneficiario == "VEREADOR"
                ),
                "lancamentos_duodecimo": len(pacote.duodecimos),
                "declaracoes_oficiais": len(pacote.declaracoes),
                "registros_custo_estrutura_mandato_mensal": len(
                    pacote.custos_mandato_mensais
                ),
            },
            "reconciliacao_contabil_2026": {
                "despesas_empenhado_bruto_brl": str(soma_emp_bruto),
                "despesas_anulacao_brl": str(soma_anulacao),
                "despesas_empenhado_liquido_brl": str(soma_emp_liquido),
                "despesas_liquidado_brl": str(soma_liquidado),
                "despesas_pago_brl": str(soma_pago),
                "duodecimo_repasses_recebidos_brl": str(soma_repasse_duodecimo),
                "duodecimo_devolucoes_brl": str(soma_devolucao_duodecimo),
                "diarias_total_pago_brl": str(sum(d.valor_pago for d in pacote.diarias)),
                "diarias_vereadores_pago_brl": str(
                    sum(
                        d.valor_pago
                        for d in pacote.diarias
                        if d.tipo_beneficiario == "VEREADOR"
                    )
                ),
            },
            "protecao_lgpd": {
                "cpfs_pessoa_fisica_mascarados_em_despesas": pacote.cpfs_mascarados_lgpd,
                "cpfs_completos_armazenados": 0,
                "formato_mascara": "***.***.***-**",
            },
            "arquivos_versionados": [asdict(m) for m in pacote.documentos_brutos],
        }

        caminho_manifesto = self.diretorio_raiz_lote / "manifesto_transparencia_2026.json"
        caminho_manifesto.write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        snapshot = {
            "manifesto": manifesto,
            "custos_mandato_mensais": [asdict(c) for c in pacote.custos_mandato_mensais],
            "diarias": [asdict(d) for d in pacote.diarias],
            "duodecimos": [asdict(d) for d in pacote.duodecimos],
            "declaracoes": [asdict(d) for d in pacote.declaracoes],
        }
        caminho_snapshot = self.diretorio_raiz_lote / "snapshot_tratado_transparencia_2026.json"
        caminho_snapshot.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )

        return manifesto
