"""Executor auditável do Lote 1 de Backfill do Nexlegis (Fase 1).

Escopo estrito autorizado:
1. Verificação de robots.txt e coleta de `/api/vereadores`.
2. Coleta das 8 páginas de índice de `/api/sessoes` com `per_page=50`.
3. Coleta dos detalhes das sessões de 2026 (`/api/sessoes/{id}`) e matérias de 2026 (`/api/materias`).
4. Download de PDFs das sessões de 2026 e gravação dos arquivos originais e
   respectivos manifestos em `data/raw/inhumas-go/nexlegis/`.
5. Taxa máxima estrita: 1 requisição a cada >= 3,0 segundos.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from cerrado_aberto_coleta.config import MunicipioConfig, criar_config_municipio_padrao
from cerrado_aberto_coleta.entidades import VEREADORES_MESTRE_INHUMAS
from cerrado_aberto_coleta.nexlegis.loader import InMemoryNexlegisRepository
from cerrado_aberto_coleta.nexlegis.parser import NexlegisParser
from cerrado_aberto_coleta.qualidade import avaliar_qualidade_repositorio
from cerrado_aberto_coleta.storage import (
    LocalVersionedStorage,
    MetadadosDocumentoBruto,
    calcular_sha256,
)

_RE_CPF_TEXTO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
IDS_VEREADORES_CURADOS = {v.id_origem_nexlegis for v in VEREADORES_MESTRE_INHUMAS}
TIPOS_CONHECIDOS_INICIAIS = {1, 2, 3, 4, 5, 6, 7, 8, 144, 211}


def sanitizar_cpf_em_bytes_json(conteudo: bytes) -> tuple[bytes, int]:
    """Mascara qualquer CPF no formato XXX.XXX.XXX-XX antes de gravar em disco (LGPD)."""
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo, 0
    ocorrencias = len(_RE_CPF_TEXTO.findall(texto))
    if ocorrencias == 0:
        return conteudo, 0
    texto_limpo = _RE_CPF_TEXTO.sub("***.***.***-**", texto)
    return texto_limpo.encode("utf-8"), ocorrencias


@dataclass
class RegistroRequisicaoLote1:
    ordem: int
    etapa: str
    endpoint_ou_url: str
    metodo: str
    status_http: int | None
    coletado_em: str
    intervalo_desde_anterior_seg: float | None
    hash_sha256: str | None
    caminho_armazenamento: str | None
    tamanho_bytes: int
    cpfs_mascarados: int = 0
    erro: str | None = None


@dataclass
class RelatorioExecucaoLote1:
    execucao_id: str
    municipio_id: str
    versao_coletor: str
    iniciado_em: str
    finalizado_em: str | None = None
    robots_txt_status: int | None = None
    robots_txt_permite_coleta: bool = True
    total_requisicoes_realizadas: int = 0
    intervalo_minimo_observado_seg: float | None = None
    intervalo_medio_observado_seg: float | None = None
    # Contagens brutas encontradas
    vereadores_encontrados_api: int = 0
    sessoes_indice_total_api: int = 0
    sessoes_indice_lidas_8_paginas: int = 0
    sessoes_por_ano_no_indice: dict[str, int] = field(default_factory=dict)
    sessoes_2026_encontradas_no_indice: int = 0
    sessoes_detalhes_2026_coletados: int = 0
    materias_total_api: int = 0
    materias_paginas_2026_coletadas: int = 0
    materias_2026_encontradas_listagem: int = 0
    materias_pre_2026_na_fronteira_ignoradas: int = 0
    # Armazenados no repositório validado (escopo Lote 1)
    vereadores_armazenados: int = 0
    sessoes_indice_armazenadas: int = 0
    sessoes_2026_armazenadas: int = 0
    presencas_2026_armazenadas: int = 0
    proposicoes_2026_armazenadas: int = 0
    proposicoes_parlamentares_2026: int = 0
    documentos_administrativos_2026: int = 0
    autorias_2026_armazenadas: int = 0
    tramitacoes_2026_armazenadas: int = 0
    pauta_itens_2026_armazenados: int = 0
    votacoes_2026_armazenadas: int = 0
    votos_nominais_2026_armazenados: int = 0
    # PDFs
    pdfs_identificados_sessoes_2026: int = 0
    pdfs_baixados_com_sucesso: int = 0
    pdfs_falhas: list[str] = field(default_factory=list)
    # Qualidade e anomalias
    cpfs_mascarados_total: int = 0
    duplicidades_identificadas: list[dict[str, Any]] = field(default_factory=list)
    novos_tipos_proposicao: list[dict[str, Any]] = field(default_factory=list)
    erros_e_inconsistencias: list[str] = field(default_factory=list)
    dados_revisao_humana: list[dict[str, Any]] = field(default_factory=list)
    verificacao_integridade: dict[str, Any] = field(default_factory=dict)
    arquivos_e_manifestos_gerados: list[str] = field(default_factory=list)
    indice_url_para_arquivo: dict[str, str] = field(default_factory=dict)
    log_requisicoes: list[RegistroRequisicaoLote1] = field(default_factory=list)


class ExecutorLote1Nexlegis:
    """Executa o Lote 1 com controle estrito de taxa (>= 3.0s/req) e auditoria completa."""

    def __init__(self, repo_root: Path, *, crawl_delay_segundos: float = 3.05) -> None:
        self.repo_root = Path(repo_root)
        self.raw_base_dir = self.repo_root / "data" / "raw"
        self.nexlegis_raw_dir = self.raw_base_dir / "inhumas-go" / "nexlegis"
        self.nexlegis_raw_dir.mkdir(parents=True, exist_ok=True)

        self.config: MunicipioConfig = criar_config_municipio_padrao(raw_dir=self.raw_base_dir)
        self.storage = LocalVersionedStorage(self.raw_base_dir)
        self.parser = NexlegisParser(municipio_id=self.config.municipio_id)
        self.repo = InMemoryNexlegisRepository()
        self.crawl_delay = max(3.0, crawl_delay_segundos)
        self._ultimo_ts: float | None = None
        self._intervalos: list[float] = []

        self.relatorio = RelatorioExecucaoLote1(
            execucao_id=str(uuid4()),
            municipio_id=self.config.municipio_id,
            versao_coletor=self.config.versao_coletor,
            iniciado_em=datetime.now(UTC).isoformat(),
        )
        self._client = httpx.Client(
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        self._carregar_checkpoint_se_existir()

    def _carregar_checkpoint_se_existir(self) -> None:
        caminho = self.nexlegis_raw_dir / "manifesto_lote1.json"
        if not caminho.exists():
            return
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self.relatorio.execucao_id = dados.get("execucao_id") or self.relatorio.execucao_id
        self.relatorio.iniciado_em = dados.get("iniciado_em") or self.relatorio.iniciado_em
        self.relatorio.total_requisicoes_realizadas = int(
            dados.get("total_requisicoes_realizadas") or 0
        )
        self.relatorio.cpfs_mascarados_total = int(dados.get("cpfs_mascarados_total") or 0)
        self.relatorio.arquivos_e_manifestos_gerados = list(
            dados.get("arquivos_e_manifestos_gerados") or []
        )
        self.relatorio.indice_url_para_arquivo = dict(
            dados.get("indice_url_para_arquivo") or {}
        )
        self.relatorio.erros_e_inconsistencias = list(
            dados.get("erros_e_inconsistencias") or []
        )

        logs_recuperados: list[RegistroRequisicaoLote1] = []
        for item in dados.get("log_requisicoes") or []:
            reg = RegistroRequisicaoLote1(**item)
            logs_recuperados.append(reg)
            if reg.intervalo_desde_anterior_seg is not None:
                self._intervalos.append(float(reg.intervalo_desde_anterior_seg))
        self.relatorio.log_requisicoes = logs_recuperados
        if self._intervalos:
            self.relatorio.intervalo_minimo_observado_seg = min(self._intervalos)
            self.relatorio.intervalo_medio_observado_seg = round(
                sum(self._intervalos) / len(self._intervalos), 3
            )

    def _aguardar_taxa(self) -> float | None:
        if self._ultimo_ts is None:
            self._ultimo_ts = time.monotonic()
            return None
        decorrido = time.monotonic() - self._ultimo_ts
        if decorrido < self.crawl_delay:
            time.sleep(self.crawl_delay - decorrido)
        agora = time.monotonic()
        intervalo_real = round(agora - self._ultimo_ts, 3)
        self._ultimo_ts = agora
        self._intervalos.append(intervalo_real)
        self.relatorio.intervalo_minimo_observado_seg = min(self._intervalos)
        self.relatorio.intervalo_medio_observado_seg = round(
            sum(self._intervalos) / len(self._intervalos), 3
        )
        return intervalo_real

    def _salvar_checkpoint_manifesto(self) -> Path:
        caminho = self.nexlegis_raw_dir / "manifesto_lote1.json"
        caminho.write_text(
            json.dumps(asdict(self.relatorio), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        rel_manifesto = "data/raw/inhumas-go/nexlegis/manifesto_lote1.json"
        if rel_manifesto not in self.relatorio.arquivos_e_manifestos_gerados:
            self.relatorio.arquivos_e_manifestos_gerados.append(rel_manifesto)
        return caminho

    def requisitar_e_salvar(
        self,
        url: str,
        *,
        etapa: str,
        fonte_url_canonica: str | None = None,
        extensao: str = "json",
        mime_esperado: str = "application/json",
        url_temporaria: bool = False,
    ) -> tuple[bytes | None, MetadadosDocumentoBruto | None]:
        # Reaproveita arquivo já coletado e verificado no disco (idempotência e retomada segura)
        caminho_cache_rel = self.relatorio.indice_url_para_arquivo.get(url)
        if caminho_cache_rel:
            caminho_fisico = self.repo_root / caminho_cache_rel
            caminho_meta = Path(f"{caminho_fisico}.meta.json")
            if caminho_fisico.exists() and caminho_meta.exists():
                conteudo_disco = caminho_fisico.read_bytes()
                dados_meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
                if calcular_sha256(conteudo_disco) == dados_meta.get("hash_conteudo"):
                    meta_obj = MetadadosDocumentoBruto(**dados_meta)
                    return conteudo_disco, meta_obj

        intervalo = self._aguardar_taxa()
        ordem = self.relatorio.total_requisicoes_realizadas + 1
        self.relatorio.total_requisicoes_realizadas = ordem
        instante = datetime.now(UTC)

        try:
            resp = self._client.get(url)
            status_http = resp.status_code
            if status_http in (403, 429) or (
                extensao != "pdf" and "captcha" in resp.text[:500].lower()
            ):
                msg = (
                    f"Bloqueio ou limite detectado (HTTP {status_http}) em {url}. "
                    "Interrompendo imediatamente conforme regra de não contornar bloqueios."
                )
                self.relatorio.erros_e_inconsistencias.append(msg)
                self.relatorio.log_requisicoes.append(
                    RegistroRequisicaoLote1(
                        ordem=ordem,
                        etapa=etapa,
                        endpoint_ou_url=url,
                        metodo="GET",
                        status_http=status_http,
                        coletado_em=instante.isoformat(),
                        intervalo_desde_anterior_seg=intervalo,
                        hash_sha256=None,
                        caminho_armazenamento=None,
                        tamanho_bytes=0,
                        erro=msg,
                    )
                )
                self._salvar_checkpoint_manifesto()
                raise RuntimeError(msg)

            resp.raise_for_status()
            conteudo = resp.content
            cpfs_masc = 0
            if extensao == "json":
                conteudo, cpfs_masc = sanitizar_cpf_em_bytes_json(conteudo)
                self.relatorio.cpfs_mascarados_total += cpfs_masc

            mime_real = (
                resp.headers.get("content-type", mime_esperado).split(";")[0].strip()
                or mime_esperado
            )
            meta = self.storage.salvar_bruto(
                municipio_id=self.config.municipio_id,
                fonte_id="nexlegis",
                fonte_url=fonte_url_canonica or url,
                conteudo=conteudo,
                mime_type=mime_real,
                extensao=extensao,
                versao_coletor=self.config.versao_coletor,
                status_http=status_http,
                url_temporaria=url_temporaria,
                coletado_em=instante,
            )

            caminho_rel = f"data/raw/{meta.caminho_armazenamento}"
            caminho_meta_rel = f"{caminho_rel}.meta.json"
            if caminho_rel not in self.relatorio.arquivos_e_manifestos_gerados:
                self.relatorio.arquivos_e_manifestos_gerados.append(caminho_rel)
            if caminho_meta_rel not in self.relatorio.arquivos_e_manifestos_gerados:
                self.relatorio.arquivos_e_manifestos_gerados.append(caminho_meta_rel)

            self.relatorio.indice_url_para_arquivo[url] = caminho_rel
            self.relatorio.log_requisicoes.append(
                RegistroRequisicaoLote1(
                    ordem=ordem,
                    etapa=etapa,
                    endpoint_ou_url=url,
                    metodo="GET",
                    status_http=status_http,
                    coletado_em=instante.isoformat(),
                    intervalo_desde_anterior_seg=intervalo,
                    hash_sha256=meta.hash_conteudo,
                    caminho_armazenamento=caminho_rel,
                    tamanho_bytes=len(conteudo),
                    cpfs_mascarados=cpfs_masc,
                )
            )
            self._salvar_checkpoint_manifesto()
            return conteudo, meta

        except (httpx.HTTPError, OSError, ValueError) as exc:
            erro_str = f"[{etapa}] Falha em {url}: {exc}"
            self.relatorio.erros_e_inconsistencias.append(erro_str)
            self.relatorio.log_requisicoes.append(
                RegistroRequisicaoLote1(
                    ordem=ordem,
                    etapa=etapa,
                    endpoint_ou_url=url,
                    metodo="GET",
                    status_http=getattr(getattr(exc, "response", None), "status_code", None),
                    coletado_em=instante.isoformat(),
                    intervalo_desde_anterior_seg=intervalo,
                    hash_sha256=None,
                    caminho_armazenamento=None,
                    tamanho_bytes=0,
                    erro=str(exc),
                )
            )
            self._salvar_checkpoint_manifesto()
            return None, None

    def verificar_robots_txt(self) -> None:
        url = "https://inhumas.nexlegis.com.br/robots.txt"
        conteudo, meta = self.requisitar_e_salvar(
            url,
            etapa="0_robots_txt",
            extensao="txt",
            mime_esperado="text/plain",
        )
        if conteudo is None or meta is None:
            raise RuntimeError("Não foi possível verificar o robots.txt da fonte.")
        self.relatorio.robots_txt_status = meta.status_http
        texto = conteudo.decode("utf-8", errors="replace").lower()
        if "disallow: /api" in texto:
            self.relatorio.robots_txt_permite_coleta = False
            raise RuntimeError("robots.txt proíbe coleta em /api.")

    def coletar_vereadores(self) -> None:
        pagina = 1
        ultima_pagina = 1
        total_encontrados = 0

        while pagina <= ultima_pagina:
            url = f"https://inhumas.nexlegis.com.br/api/vereadores?page={pagina}&per_page=50"
            bruto, meta = self.requisitar_e_salvar(url, etapa="1_vereadores")
            if bruto is None or meta is None:
                break

            payload = json.loads(bruto.decode("utf-8"))
            meta_pag = payload.get("meta") or {}
            ultima_pagina = int(
                payload.get("last_page") or meta_pag.get("last_page") or 1
            )
            registros = self.parser.parse_vereadores_list(bruto, meta)
            total_encontrados += len(registros)
            self.repo.carregar_vereadores(registros)

            for v in registros:
                if v.id_origem_nexlegis not in IDS_VEREADORES_CURADOS:
                    self.relatorio.dados_revisao_humana.append(
                        {
                            "tipo": "VEREADOR_NAO_CURADO_EM_ALIASES",
                            "id_origem_nexlegis": v.id_origem_nexlegis,
                            "nome_politico": v.nome_politico,
                            "slug": v.slug,
                            "motivo": (
                                "Vereador retornado por /api/vereadores ainda não consta em "
                                "VEREADORES_MESTRE_INHUMAS (provável suplente ou legislatura anterior)."
                            ),
                        }
                    )
                if not v.biografia_texto:
                    self.relatorio.dados_revisao_humana.append(
                        {
                            "tipo": "VEREADOR_SEM_BIOGRAFIA_OU_PARTIDO",
                            "id_origem_nexlegis": v.id_origem_nexlegis,
                            "nome_politico": v.nome_politico,
                            "motivo": (
                                "Campo biografia está nulo/vazio na API Nexlegis; filiação partidária "
                                "precisará ser confirmada via dados eleitorais do TSE."
                            ),
                        }
                    )
            pagina += 1

        self.relatorio.vereadores_encontrados_api = total_encontrados
        self.relatorio.vereadores_armazenados = len(self.repo.vereadores.ativos)

    def coletar_indice_sessoes_8_paginas(self) -> list[dict[str, Any]]:
        """Coleta exatamente as 8 páginas de índice de `/api/sessoes?per_page=50`."""
        todas_sessoes_raw: list[dict[str, Any]] = []
        por_chave_natural: dict[tuple[int, str, int, str], list[int]] = {}
        contagem_por_ano: dict[str, int] = {}

        for pagina in range(1, 9):
            url = f"https://inhumas.nexlegis.com.br/api/sessoes?page={pagina}&per_page=50"
            bruto, meta = self.requisitar_e_salvar(url, etapa="2_sessoes_indice")
            if bruto is None or meta is None:
                continue

            payload = json.loads(bruto.decode("utf-8"))
            meta_pag = payload.get("meta") or {}
            self.relatorio.sessoes_indice_total_api = int(
                payload.get("total") or meta_pag.get("total") or 0
            )
            lista = payload.get("data") or []
            todas_sessoes_raw.extend(lista)

            for item in lista:
                ano_str = str(item.get("ano"))
                contagem_por_ano[ano_str] = contagem_por_ano.get(ano_str, 0) + 1
                if item.get("numero") is None:
                    self.relatorio.dados_revisao_humana.append(
                        {
                            "tipo": "SESSAO_COM_NUMERO_NULO_NA_FONTE",
                            "sessao_id": item.get("id"),
                            "nome_sessao": item.get("nome_sessao"),
                            "ano": item.get("ano"),
                            "data": item.get("data"),
                            "motivo": (
                                "Sessão retornada pela API com campo 'numero': null; "
                                "normalizada pelo parser como 'S/N'."
                            ),
                        }
                    )
                for midia in item.get("midias") or []:
                    m_url = str(midia.get("url") or "")
                    m_mime = str(midia.get("mime_type") or "")
                    if m_mime == "application/pdf" and not m_url.lower().endswith(".pdf"):
                        self.relatorio.dados_revisao_humana.append(
                            {
                                "tipo": "MIDIA_PDF_SEM_EXTENSAO_NA_URL",
                                "sessao_id": item.get("id"),
                                "file_name": midia.get("file_name"),
                                "url": m_url,
                                "motivo": (
                                    "Mídia com mime_type 'application/pdf' cuja URL S3 "
                                    "não termina com extensão '.pdf'."
                                ),
                            }
                        )
                chave_nat = (
                    int(item.get("tipo_id") or 0),
                    str(item.get("numero") or "").strip(),
                    int(item.get("ano") or 0),
                    str(item.get("data") or "").strip(),
                )
                por_chave_natural.setdefault(chave_nat, []).append(int(item["id"]))

            # Valida e carrega as sessões no repositório
            sessoes_parseadas = self.parser.parse_sessoes_list(bruto, meta)
            self.repo.carregar_sessoes(sessoes_parseadas)

        # Identifica duplicidades por chave natural ou por (tipo_id, numero, ano)
        por_tipo_num_ano: dict[tuple[int, str, int], list[dict[str, Any]]] = {}
        for item in todas_sessoes_raw:
            chave_tna = (
                int(item.get("tipo_id") or 0),
                str(item.get("numero") or "").strip(),
                int(item.get("ano") or 0),
            )
            por_tipo_num_ano.setdefault(chave_tna, []).append(item)

        for chave_tna, itens in por_tipo_num_ano.items():
            if len(itens) > 1:
                self.relatorio.duplicidades_identificadas.append(
                    {
                        "entidade": "sessao",
                        "criterio": "(tipo_id, numero, ano)",
                        "tipo_id": chave_tna[0],
                        "numero": chave_tna[1],
                        "ano": chave_tna[2],
                        "ids_encontrados": [i["id"] for i in itens],
                        "datas": [i.get("data") for i in itens],
                        "nomes": [i.get("nome_sessao") for i in itens],
                    }
                )

        self.relatorio.sessoes_indice_lidas_8_paginas = len(todas_sessoes_raw)
        self.relatorio.sessoes_por_ano_no_indice = dict(sorted(contagem_por_ano.items()))
        self.relatorio.sessoes_indice_armazenadas = len(self.repo.sessoes.ativos)

        sessoes_2026 = [s for s in todas_sessoes_raw if int(s.get("ano") or 0) == 2026]
        self.relatorio.sessoes_2026_encontradas_no_indice = len(sessoes_2026)
        return sessoes_2026

    def coletar_detalhes_sessoes_2026_e_pdfs(
        self,
        sessoes_2026_raw: list[dict[str, Any]],
        *,
        baixar_pdfs: bool = True,
    ) -> None:
        """Coleta `/api/sessoes/{id}` apenas para sessões de 2026 e baixa os PDFs vinculados."""
        ids_2026 = sorted({int(s["id"]) for s in sessoes_2026_raw}, reverse=True)
        tipos_novos_vistos: dict[int, dict[str, Any]] = {}
        urls_pdfs_para_baixar: list[tuple[int, str, str]] = []

        for sessao_id in ids_2026:
            url = f"https://inhumas.nexlegis.com.br/api/sessoes/{sessao_id}"
            bruto, meta = self.requisitar_e_salvar(url, etapa="3_sessao_detalhe_2026")
            if bruto is None or meta is None:
                continue

            self.relatorio.sessoes_detalhes_2026_coletados += 1
            payload_det = json.loads(bruto.decode("utf-8"))

            # Verifica mídias PDF na sessão
            for midia in payload_det.get("midias") or []:
                pdf_url = midia.get("url")
                m_mime = str(midia.get("mime_type") or "").lower()
                if pdf_url and (
                    str(pdf_url).lower().endswith(".pdf") or m_mime == "application/pdf"
                ):
                    urls_pdfs_para_baixar.append(
                        (sessao_id, str(pdf_url), f"https://inhumas.nexlegis.com.br/api/sessoes/{sessao_id}")
                    )

            # Inspeciona tipos de proposição nas pautas da sessão
            for pauta in payload_det.get("pautas") or []:
                mat = pauta.get("materia") or {}
                t_id = mat.get("tipo_id")
                t_desc = (mat.get("tipo") or {}).get("descricao")
                if t_id is not None and int(t_id) not in TIPOS_CONHECIDOS_INICIAIS:
                    tipos_novos_vistos[int(t_id)] = {
                        "tipo_id": int(t_id),
                        "descricao": t_desc,
                        "exemplo_materia_id": mat.get("id"),
                        "exemplo_nome": mat.get("nome_materia"),
                        "origem": f"sessao_{sessao_id}_pauta",
                    }

                # Verifica inconsistência da flag unanime vs votos nominais reais
                vot = pauta.get("votacao")
                if isinstance(vot, dict) and vot.get("votos"):
                    votos_lista = vot["votos"]
                    todos_favoraveis = all(
                        (v.get("voto") or {}).get("descricao") == "Favorável"
                        for v in votos_lista
                    )
                    if todos_favoraveis and vot.get("unanime") is False:
                        self.relatorio.dados_revisao_humana.append(
                            {
                                "tipo": "DIVERGENCIA_FLAG_UNANIME_VS_PLACAR_NOMINAL",
                                "sessao_id": sessao_id,
                                "votacao_id": vot.get("id"),
                                "materia_id": mat.get("id"),
                                "nome_materia": mat.get("nome_materia"),
                                "placar_favoravel": len(votos_lista),
                                "motivo": (
                                    "Todos os votos nominais registrados são 'Favorável', "
                                    "porém o campo booleano 'unanime' na API está false."
                                ),
                            }
                        )

            pacote = self.parser.parse_sessao_detalhe(bruto, meta)
            self.repo.carregar_pacote_sessao_detalhe(pacote)

            # Verifica se há sessão de 2026 sem lista de presença registrada
            if len(pacote.presencas) == 0:
                self.relatorio.dados_revisao_humana.append(
                    {
                        "tipo": "SESSAO_2026_SEM_LISTA_PRESENCA",
                        "sessao_id": sessao_id,
                        "nome_sessao": pacote.sessao.nome_sessao,
                        "data_abertura": str(pacote.sessao.data_abertura),
                        "motivo": "Sessão de 2026 retornou array 'presenca' vazio na API.",
                    }
                )

        ids_ja_registrados = {x["tipo_id"] for x in self.relatorio.novos_tipos_proposicao}
        for t_id_novo, t_novo in tipos_novos_vistos.items():
            if t_id_novo not in ids_ja_registrados:
                self.relatorio.novos_tipos_proposicao.append(t_novo)
                ids_ja_registrados.add(t_id_novo)

        # Download de PDFs das sessões de 2026
        self.relatorio.pdfs_identificados_sessoes_2026 = len(urls_pdfs_para_baixar)
        if not baixar_pdfs:
            return
        urls_vistas: set[str] = set()
        for sessao_id, pdf_url, url_canonica in urls_pdfs_para_baixar:
            if pdf_url in urls_vistas:
                continue
            urls_vistas.add(pdf_url)
            conteudo_pdf, meta_pdf = self.requisitar_e_salvar(
                pdf_url,
                etapa=f"4_pdf_sessao_{sessao_id}",
                fonte_url_canonica=url_canonica,
                extensao="pdf",
                mime_esperado="application/pdf",
                url_temporaria=False,
            )
            if conteudo_pdf is not None and meta_pdf is not None and conteudo_pdf.startswith(b"%PDF"):
                self.relatorio.pdfs_baixados_com_sucesso += 1
            else:
                self.relatorio.pdfs_falhas.append(f"Sessão {sessao_id}: {pdf_url}")

    def coletar_materias_2026(self) -> None:
        """Pagina `/api/materias?per_page=50` coletando exclusivamente matérias de 2026."""
        pagina = 1
        ultima_pagina = 1
        tipos_novos_vistos = {
            item["tipo_id"]: item for item in self.relatorio.novos_tipos_proposicao
        }
        por_chave_materia: dict[tuple[int, str, int], list[int]] = {}

        while pagina <= ultima_pagina:
            url = f"https://inhumas.nexlegis.com.br/api/materias?page={pagina}&per_page=50"
            bruto, meta = self.requisitar_e_salvar(url, etapa="5_materias_2026")
            if bruto is None or meta is None:
                break

            self.relatorio.materias_paginas_2026_coletadas += 1
            payload = json.loads(bruto.decode("utf-8"))
            meta_pag = payload.get("meta") or {}
            self.relatorio.materias_total_api = int(
                payload.get("total") or meta_pag.get("total") or 0
            )
            ultima_pagina = int(
                payload.get("last_page") or meta_pag.get("last_page") or 1
            )
            lista = payload.get("data") or []
            if not lista:
                break

            itens_2026 = []
            itens_pre_2026 = 0
            for item in lista:
                ano_item = int(item.get("ano") or 0)
                if ano_item == 2026:
                    itens_2026.append(item)
                    chave_m = (
                        int(item.get("tipo_id") or 0),
                        str(item.get("numero") or "").strip(),
                        ano_item,
                    )
                    por_chave_materia.setdefault(chave_m, []).append(int(item["id"]))

                    t_id = item.get("tipo_id")
                    t_desc = (item.get("tipo") or {}).get("descricao")
                    if t_id is not None and int(t_id) not in TIPOS_CONHECIDOS_INICIAIS:
                        tipos_novos_vistos[int(t_id)] = {
                            "tipo_id": int(t_id),
                            "descricao": t_desc,
                            "exemplo_materia_id": item.get("id"),
                            "exemplo_nome": item.get("nome_materia"),
                            "origem": f"materias_page_{pagina}",
                        }
                elif ano_item < 2026:
                    itens_pre_2026 += 1

            self.relatorio.materias_2026_encontradas_listagem += len(itens_2026)
            self.relatorio.materias_pre_2026_na_fronteira_ignoradas += itens_pre_2026

            if itens_2026:
                # Filtra o payload em memória para carregar no repositório apenas 2026 (escopo Lote 1),
                # mantendo o JSON bruto da página intacto no disco!
                payload_filtrado_2026 = {
                    **payload,
                    "data": itens_2026,
                }
                bruto_2026 = json.dumps(payload_filtrado_2026, ensure_ascii=False).encode("utf-8")
                meta_2026 = MetadadosDocumentoBruto(
                    **{
                        **asdict(meta),
                        "hash_conteudo": calcular_sha256(bruto_2026),
                        "tamanho_bytes": len(bruto_2026),
                    }
                )
                pacote_mat = self.parser.parse_materias_list(bruto_2026, meta_2026)
                self.repo.carregar_pacote_materias(pacote_mat)

            # Se a página já contém registros anteriores a 2026 e nenhum item de 2026 (ou atingiu a fronteira),
            # paramos imediatamente para NÃO iniciar os lotes históricos de 2021-2025!
            if itens_pre_2026 > 0 and len(itens_2026) == 0:
                break
            if itens_pre_2026 > 0 and all(
                int(x.get("ano") or 0) < 2026 for x in lista[-5:]
            ):
                break

            pagina += 1

        for chave_m, ids_m in por_chave_materia.items():
            if len(ids_m) > 1:
                self.relatorio.duplicidades_identificadas.append(
                    {
                        "entidade": "proposicao_2026",
                        "criterio": "(tipo_id, numero, ano)",
                        "tipo_id": chave_m[0],
                        "numero": chave_m[1],
                        "ano": chave_m[2],
                        "ids_encontrados": ids_m,
                    }
                )

        self.relatorio.novos_tipos_proposicao = list(tipos_novos_vistos.values())

    def validar_integridade_e_reprodutibilidade(self) -> None:
        """Verifica os hashes SHA-256 no disco e reexecuta a carga para comprovar reprodutibilidade."""
        arquivos_verificados = 0
        divergencias_hash: list[str] = []

        for req in self.relatorio.log_requisicoes:
            if not req.caminho_armazenamento or not req.hash_sha256:
                continue
            caminho_fisico = self.repo_root / req.caminho_armazenamento
            if not caminho_fisico.exists():
                divergencias_hash.append(f"Arquivo ausente: {req.caminho_armazenamento}")
                continue
            hash_disco = calcular_sha256(caminho_fisico.read_bytes())
            if hash_disco != req.hash_sha256:
                divergencias_hash.append(
                    f"Hash divergente em {req.caminho_armazenamento}: esperado={req.hash_sha256}, disco={hash_disco}"
                )
            else:
                arquivos_verificados += 1

        # Métricas finais do repositório
        sessoes_2026_repo = [
            s for s in self.repo.sessoes.ativos.values() if s.ano == 2026
        ]
        props_2026_repo = [
            p for p in self.repo.proposicoes.ativos.values() if p.ano == 2026
        ]
        props_parlamentares_2026 = [
            p for p in props_2026_repo if p.eh_proposicao_parlamentar
        ]
        docs_admin_2026 = [
            p for p in props_2026_repo if not p.eh_proposicao_parlamentar
        ]

        self.relatorio.sessoes_2026_armazenadas = len(sessoes_2026_repo)
        self.relatorio.presencas_2026_armazenadas = len(self.repo.presencas.ativos)
        self.relatorio.proposicoes_2026_armazenadas = len(props_2026_repo)
        self.relatorio.proposicoes_parlamentares_2026 = len(props_parlamentares_2026)
        self.relatorio.documentos_administrativos_2026 = len(docs_admin_2026)
        self.relatorio.autorias_2026_armazenadas = len(self.repo.autorias.ativos)
        self.relatorio.tramitacoes_2026_armazenadas = len(self.repo.tramitacoes.ativos)
        self.relatorio.pauta_itens_2026_armazenados = len(self.repo.pauta_itens.ativos)
        self.relatorio.votacoes_2026_armazenadas = len(self.repo.votacoes.ativos)
        self.relatorio.votos_nominais_2026_armazenados = len(self.repo.votos.ativos)

        # Teste de idempotência sobre o repositório populado (recarregando todos os vereadores e sessões)
        reexec_ver = self.repo.carregar_vereadores(list(self.repo.vereadores.ativos.values()))
        reexec_ses = self.repo.carregar_sessoes(list(self.repo.sessoes.ativos.values()))
        idempotente_ok = (
            reexec_ver.novos == 0
            and reexec_ver.alterados == 0
            and reexec_ses.novos == 0
            and reexec_ses.alterados == 0
        )

        rel_qualidade = avaliar_qualidade_repositorio(
            self.repo, municipio_id=self.config.municipio_id
        )

        # Exporta snapshot estruturado reproduzível dos registros tratados do Lote 1
        snapshot_path = self.nexlegis_raw_dir / "snapshot_tratado_lote1.json"
        snapshot_data = {
            "execucao_id": self.relatorio.execucao_id,
            "municipio_id": self.config.municipio_id,
            "versao_coletor": self.config.versao_coletor,
            "gerado_em": datetime.now(UTC).isoformat(),
            "contagens": {
                "vereadores": len(self.repo.vereadores.ativos),
                "sessoes_indice_total": len(self.repo.sessoes.ativos),
                "sessoes_2026": len(sessoes_2026_repo),
                "presencas_2026": len(self.repo.presencas.ativos),
                "proposicoes_2026_total": len(props_2026_repo),
                "proposicoes_parlamentares_2026": len(props_parlamentares_2026),
                "documentos_administrativos_2026": len(docs_admin_2026),
                "autorias_2026": len(self.repo.autorias.ativos),
                "tramitacoes_2026": len(self.repo.tramitacoes.ativos),
                "pauta_itens_2026": len(self.repo.pauta_itens.ativos),
                "votacoes_2026": len(self.repo.votacoes.ativos),
                "votos_nominais_2026": len(self.repo.votos.ativos),
            },
            "producao_legislativa_por_vereador_2026": self.repo.contar_producao_legislativa_por_vereador(),
        }
        snapshot_path.write_text(
            json.dumps(snapshot_data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        rel_snap = "data/raw/inhumas-go/nexlegis/snapshot_tratado_lote1.json"
        if rel_snap not in self.relatorio.arquivos_e_manifestos_gerados:
            self.relatorio.arquivos_e_manifestos_gerados.append(rel_snap)

        self.relatorio.verificacao_integridade = {
            "arquivos_brutos_verificados_sha256": arquivos_verificados,
            "divergencias_sha256": divergencias_hash,
            "reexecucao_idempotente_confirmada": idempotente_ok,
            "proveniencia_100_porcento": rel_qualidade.proveniencia_100_porcento,
            "inconsistencias_cruzadas": rel_qualidade.inconsistencias_cruzadas,
            "aprovado_qualidade": rel_qualidade.aprovado_para_publicacao and len(divergencias_hash) == 0,
        }
        self.relatorio.finalizado_em = datetime.now(UTC).isoformat()
        self._salvar_checkpoint_manifesto()

    def executar(
        self,
        *,
        incluir_detalhes_sessoes_2026: bool = True,
        baixar_pdfs_sessoes_2026: bool = True,
        incluir_materias_2026: bool = True,
    ) -> RelatorioExecucaoLote1:
        try:
            self.verificar_robots_txt()
            self.coletar_vereadores()
            sessoes_2026_raw = self.coletar_indice_sessoes_8_paginas()
            if incluir_materias_2026:
                self.coletar_materias_2026()
            if incluir_detalhes_sessoes_2026:
                self.coletar_detalhes_sessoes_2026_e_pdfs(
                    sessoes_2026_raw, baixar_pdfs=baixar_pdfs_sessoes_2026
                )
            self.validar_integridade_e_reprodutibilidade()
            return self.relatorio
        finally:
            self._client.close()


if __name__ == "__main__":
    import argparse

    parser_cli = argparse.ArgumentParser(description="Executor do Lote 1 Nexlegis")
    parser_cli.add_argument(
        "--etapa",
        choices=["indices_e_materias", "detalhes_sessoes_2026", "completo"],
        default="completo",
    )
    args = parser_cli.parse_args()
    raiz = Path(__file__).resolve().parents[5]
    executor = ExecutorLote1Nexlegis(raiz, crawl_delay_segundos=3.05)
    if args.etapa == "indices_e_materias":
        rel = executor.executar(
            incluir_detalhes_sessoes_2026=False,
            baixar_pdfs_sessoes_2026=False,
            incluir_materias_2026=True,
        )
    elif args.etapa == "detalhes_sessoes_2026":
        rel = executor.executar(
            incluir_detalhes_sessoes_2026=True,
            baixar_pdfs_sessoes_2026=False,
            incluir_materias_2026=True,
        )
    else:
        rel = executor.executar(
            incluir_detalhes_sessoes_2026=True,
            baixar_pdfs_sessoes_2026=True,
            incluir_materias_2026=True,
        )
    print(
        json.dumps(
            {
                "etapa": args.etapa,
                "total_requisicoes_realizadas": rel.total_requisicoes_realizadas,
                "intervalo_minimo_observado_seg": rel.intervalo_minimo_observado_seg,
                "vereadores_armazenados": rel.vereadores_armazenados,
                "sessoes_indice_lidas_8_paginas": rel.sessoes_indice_lidas_8_paginas,
                "sessoes_2026_encontradas_no_indice": rel.sessoes_2026_encontradas_no_indice,
                "sessoes_detalhes_2026_coletados": rel.sessoes_detalhes_2026_coletados,
                "materias_paginas_2026_coletadas": rel.materias_paginas_2026_coletadas,
                "materias_2026_encontradas_listagem": rel.materias_2026_encontradas_listagem,
                "pdfs_identificados_sessoes_2026": rel.pdfs_identificados_sessoes_2026,
                "pdfs_baixados_com_sucesso": rel.pdfs_baixados_com_sucesso,
                "verificacao_integridade": rel.verificacao_integridade,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
