"""Executor auditável do Lote 2 de Backfill do Nexlegis — Ano de 2025 (Fase 1).

Escopo estrito autorizado:
1. Coleta dos detalhes das 73 sessões de 2025 em `/api/sessoes/{id}`.
2. Coleta de todas as páginas de `/api/materias` necessárias para recuperar as matérias de 2025
   (reaproveitando as páginas 8, 10, 11 e 12 já coletadas no Lote 1 e buscando da página 13
   até a fronteira com 2024, sem iniciar o Lote 3 de 2020–2024).
3. Consulta aos registros de vereadores para identificar autores, suplentes e participantes de 2025,
   sinalizando novos vereadores e aliases ainda não catalogados para revisão humana.
4. Download dos PDFs vinculados às sessões de 2025 e preservação dos arquivos originais e
   manifestos em `data/raw/inhumas-go/nexlegis/2025/`.
5. Taxa máxima estrita: 1 requisição a cada >= 3,0 segundos, com backoff em falhas transitórias
   e interrupção imediata diante de bloqueios (HTTP 403/429 ou CAPTCHA).
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
from cerrado_aberto_coleta.entidades import (
    VEREADORES_MESTRE_INHUMAS,
)
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
TIPOS_CONHECIDOS = {1, 2, 3, 4, 5, 6, 7, 8, 12, 112, 113, 144, 145, 210, 211, 213, 375}


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
class RegistroRequisicaoLote2:
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
    tentativas: int = 1
    erro: str | None = None


@dataclass
class RelatorioExecucaoLote2:
    execucao_id: str
    lote: str
    ano_alvo: int
    municipio_id: str
    versao_coletor: str
    iniciado_em: str
    finalizado_em: str | None = None
    robots_txt_status: int | None = None
    robots_txt_permite_coleta: bool = True
    total_requisicoes_realizadas: int = 0
    intervalo_minimo_observado_seg: float | None = None
    intervalo_medio_observado_seg: float | None = None
    # Contagens brutas encontradas para 2025
    sessoes_2025_encontradas_no_indice: int = 0
    sessoes_detalhes_2025_coletados: int = 0
    materias_paginas_novas_coletadas: int = 0
    materias_paginas_reaproveitadas_lote1: int = 0
    materias_2025_encontradas_nas_paginas_lote1: int = 0
    materias_2025_encontradas_nas_paginas_novas: int = 0
    materias_2025_total_encontradas: int = 0
    materias_pre_2025_na_fronteira_ignoradas: int = 0
    # Armazenados no repositório validado (escopo Lote 2 — 2025)
    vereadores_participantes_2025_identificados: int = 0
    sessoes_2025_armazenadas: int = 0
    presencas_2025_armazenadas: int = 0
    proposicoes_2025_armazenadas: int = 0
    proposicoes_parlamentares_2025: int = 0
    documentos_administrativos_2025: int = 0
    proposicoes_anos_anteriores_em_pauta_2025: int = 0
    autorias_2025_armazenadas: int = 0
    tramitacoes_2025_armazenadas: int = 0
    pauta_itens_2025_armazenados: int = 0
    votacoes_2025_armazenadas: int = 0
    votos_nominais_2025_armazenados: int = 0
    # PDFs das sessões de 2025
    pdfs_identificados_sessoes_2025: int = 0
    pdfs_baixados_com_sucesso: int = 0
    pdfs_falhas: list[str] = field(default_factory=list)
    # Vereadores, suplentes e aliases descobertos em 2025
    novos_vereadores_e_aliases_2025: list[dict[str, Any]] = field(default_factory=list)
    novos_tipos_proposicao_2025: list[dict[str, Any]] = field(default_factory=list)
    # Qualidade, LGPD e anomalias
    cpfs_mascarados_total: int = 0
    ocorrencias_lgpd_detalhadas: list[dict[str, Any]] = field(default_factory=list)
    duplicidades_identificadas_2025: list[dict[str, Any]] = field(default_factory=list)
    erros_e_inconsistencias: list[str] = field(default_factory=list)
    dados_revisao_humana: list[dict[str, Any]] = field(default_factory=list)
    verificacao_integridade: dict[str, Any] = field(default_factory=dict)
    arquivos_e_manifestos_gerados: list[str] = field(default_factory=list)
    indice_url_para_arquivo: dict[str, str] = field(default_factory=dict)
    log_requisicoes: list[RegistroRequisicaoLote2] = field(default_factory=list)


class ExecutorLote2Nexlegis:
    """Executa o Lote 2 (ano 2025) com controle estrito de taxa (>= 3.0s/req) e auditoria completa."""

    def __init__(self, repo_root: Path, *, crawl_delay_segundos: float = 3.05) -> None:
        self.repo_root = Path(repo_root)
        self.raw_base_dir = self.repo_root / "data" / "raw"
        self.nexlegis_raw_dir = self.raw_base_dir / "inhumas-go" / "nexlegis"
        self.lote2_dir = self.nexlegis_raw_dir / "2025"
        self.lote2_dir.mkdir(parents=True, exist_ok=True)

        self.config: MunicipioConfig = criar_config_municipio_padrao(raw_dir=self.raw_base_dir)
        self.storage = LocalVersionedStorage(self.raw_base_dir)
        self.parser = NexlegisParser(municipio_id=self.config.municipio_id)
        self.repo = InMemoryNexlegisRepository()
        self.crawl_delay = max(3.0, crawl_delay_segundos)
        self._ultimo_ts: float | None = None
        self._intervalos: list[float] = []

        self.relatorio = RelatorioExecucaoLote2(
            execucao_id=str(uuid4()),
            lote="Lote 2 — Backfill Nexlegis 2025",
            ano_alvo=2025,
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
        caminho = self.lote2_dir / "manifesto_lote2.json"
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

        logs_recuperados: list[RegistroRequisicaoLote2] = []
        for item in dados.get("log_requisicoes") or []:
            reg = RegistroRequisicaoLote2(**item)
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
        caminho = self.lote2_dir / "manifesto_lote2.json"
        caminho.write_text(
            json.dumps(asdict(self.relatorio), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        rel_manifesto = "data/raw/inhumas-go/nexlegis/2025/manifesto_lote2.json"
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
        max_tentativas: int = 3,
    ) -> tuple[bytes | None, MetadadosDocumentoBruto | None]:
        """Executa GET com >= 3.0s, backoff em falhas transitórias, filtro LGPD e salvamento em 2025/."""
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

        tentativa = 0
        ultimo_erro: Exception | None = None
        while tentativa < max_tentativas:
            tentativa += 1
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
                        RegistroRequisicaoLote2(
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
                            tentativas=tentativa,
                            erro=msg,
                        )
                    )
                    self._salvar_checkpoint_manifesto()
                    raise RuntimeError(msg)

                if status_http in (500, 502, 503, 504) and tentativa < max_tentativas:
                    espera_backoff = self.crawl_delay * (2**tentativa)
                    time.sleep(espera_backoff)
                    continue

                resp.raise_for_status()
                conteudo = resp.content
                cpfs_masc = 0
                if extensao == "json":
                    conteudo, cpfs_masc = sanitizar_cpf_em_bytes_json(conteudo)
                    if cpfs_masc > 0:
                        self.relatorio.cpfs_mascarados_total += cpfs_masc
                        self.relatorio.ocorrencias_lgpd_detalhadas.append(
                            {
                                "url": url,
                                "etapa": etapa,
                                "cpfs_mascarados": cpfs_masc,
                                "coletado_em": instante.isoformat(),
                            }
                        )

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
                    ano_particao=2025,
                )

                caminho_rel = f"data/raw/{meta.caminho_armazenamento}"
                caminho_meta_rel = f"{caminho_rel}.meta.json"
                if caminho_rel not in self.relatorio.arquivos_e_manifestos_gerados:
                    self.relatorio.arquivos_e_manifestos_gerados.append(caminho_rel)
                if caminho_meta_rel not in self.relatorio.arquivos_e_manifestos_gerados:
                    self.relatorio.arquivos_e_manifestos_gerados.append(caminho_meta_rel)

                self.relatorio.indice_url_para_arquivo[url] = caminho_rel
                self.relatorio.log_requisicoes.append(
                    RegistroRequisicaoLote2(
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
                        tentativas=tentativa,
                    )
                )
                self._salvar_checkpoint_manifesto()
                return conteudo, meta

            except (httpx.HTTPError, OSError, ValueError) as exc:
                ultimo_erro = exc
                if tentativa < max_tentativas:
                    time.sleep(self.crawl_delay * (2**tentativa))
                    continue
                erro_str = f"[{etapa}] Falha em {url} após {tentativa} tentativas: {exc}"
                self.relatorio.erros_e_inconsistencias.append(erro_str)
                self.relatorio.log_requisicoes.append(
                    RegistroRequisicaoLote2(
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
                        tentativas=tentativa,
                        erro=str(ultimo_erro),
                    )
                )
                self._salvar_checkpoint_manifesto()
                return None, None

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

    def carregar_base_vereadores_e_indice_sessoes_2025(self) -> list[dict[str, Any]]:
        """Carrega os 32 vereadores e o índice das 73 sessões de 2025 a partir do Lote 1."""
        manifesto_l1_path = self.nexlegis_raw_dir / "manifesto_lote1.json"
        if not manifesto_l1_path.exists():
            raise FileNotFoundError(f"Manifesto do Lote 1 não encontrado em {manifesto_l1_path}")
        manifesto_l1 = json.loads(manifesto_l1_path.read_text(encoding="utf-8"))
        idx_l1: dict[str, str] = manifesto_l1.get("indice_url_para_arquivo") or {}

        # 1. Vereadores
        url_ver = "https://inhumas.nexlegis.com.br/api/vereadores?page=1&per_page=50"
        rel_ver = idx_l1[url_ver]
        bruto_ver = (self.repo_root / rel_ver).read_bytes()
        meta_ver = MetadadosDocumentoBruto(
            **json.loads(Path(f"{self.repo_root / rel_ver}.meta.json").read_text(encoding="utf-8"))
        )
        vereadores = self.parser.parse_vereadores_list(bruto_ver, meta_ver)
        self.repo.carregar_vereadores(vereadores)

        # 2. Índice de sessões (8 páginas) -> filtra as 73 sessões de 2025
        sessoes_2025_raw: list[dict[str, Any]] = []
        por_tipo_num_ano: dict[tuple[int, str, int], list[dict[str, Any]]] = {}

        for pagina in range(1, 9):
            url_ses = f"https://inhumas.nexlegis.com.br/api/sessoes?page={pagina}&per_page=50"
            rel_ses = idx_l1[url_ses]
            bruto_ses = (self.repo_root / rel_ses).read_bytes()
            meta_ses = MetadadosDocumentoBruto(
                **json.loads(
                    Path(f"{self.repo_root / rel_ses}.meta.json").read_text(encoding="utf-8")
                )
            )
            payload_ses = json.loads(bruto_ses.decode("utf-8"))
            lista_2025_pag = [
                item
                for item in (payload_ses.get("data") or [])
                if int(item.get("ano") or 0) == 2025
            ]
            if not lista_2025_pag:
                continue

            sessoes_2025_raw.extend(lista_2025_pag)
            for item in lista_2025_pag:
                chave_tna = (
                    int(item.get("tipo_id") or 0),
                    str(item.get("numero") or "").strip(),
                    2025,
                )
                por_tipo_num_ano.setdefault(chave_tna, []).append(item)
                if item.get("numero") is None:
                    self.relatorio.dados_revisao_humana.append(
                        {
                            "tipo": "SESSAO_2025_COM_NUMERO_NULO_NA_FONTE",
                            "sessao_id": item.get("id"),
                            "nome_sessao": item.get("nome_sessao"),
                            "ano": 2025,
                            "data": item.get("data"),
                            "motivo": (
                                "Sessão de 2025 retornada pela API com campo 'numero': null; "
                                "normalizada pelo parser como 'S/N'."
                            ),
                        }
                    )

            payload_filtrado = {**payload_ses, "data": lista_2025_pag}
            bruto_f = json.dumps(payload_filtrado, ensure_ascii=False).encode("utf-8")
            meta_f = MetadadosDocumentoBruto(
                **{
                    **asdict(meta_ses),
                    "hash_conteudo": calcular_sha256(bruto_f),
                    "tamanho_bytes": len(bruto_f),
                }
            )
            self.repo.carregar_sessoes(self.parser.parse_sessoes_list(bruto_f, meta_f))

        for chave_tna, itens in por_tipo_num_ano.items():
            if len(itens) > 1:
                self.relatorio.duplicidades_identificadas_2025.append(
                    {
                        "entidade": "sessao_2025",
                        "criterio": "(tipo_id, numero, ano)",
                        "tipo_id": chave_tna[0],
                        "numero": chave_tna[1],
                        "ano": chave_tna[2],
                        "ids_encontrados": [i["id"] for i in itens],
                        "datas": [i.get("data") for i in itens],
                        "nomes": [i.get("nome_sessao") for i in itens],
                    }
                )

        self.relatorio.sessoes_2025_encontradas_no_indice = len(sessoes_2025_raw)
        return sessoes_2025_raw

    def coletar_materias_2025(self) -> None:
        """Recupera todas as matérias de 2025 (páginas 1..12 do Lote 1 + páginas >= 13 até a fronteira com 2024)."""
        manifesto_l1 = json.loads(
            (self.nexlegis_raw_dir / "manifesto_lote1.json").read_text(encoding="utf-8")
        )
        idx_l1: dict[str, str] = manifesto_l1.get("indice_url_para_arquivo") or {}

        por_chave_materia: dict[tuple[int, str, int], list[int]] = {}
        tipos_novos_vistos: dict[int, dict[str, Any]] = {
            item["tipo_id"]: item for item in self.relatorio.novos_tipos_proposicao_2025
        }
        paginas_l1_com_2025 = 0
        total_2025_l1 = 0

        # 1. Inspeciona as páginas 1..12 já coletadas no Lote 1 para não perder matérias de 2025 tramitadas em dez/2025–jan/2026
        for pagina in range(1, 13):
            url = f"https://inhumas.nexlegis.com.br/api/materias?page={pagina}&per_page=50"
            rel_mat = idx_l1.get(url)
            if not rel_mat:
                continue
            bruto = (self.repo_root / rel_mat).read_bytes()
            meta = MetadadosDocumentoBruto(
                **json.loads(
                    Path(f"{self.repo_root / rel_mat}.meta.json").read_text(encoding="utf-8")
                )
            )
            payload = json.loads(bruto.decode("utf-8"))
            itens_2025 = [
                item for item in (payload.get("data") or []) if int(item.get("ano") or 0) == 2025
            ]
            if not itens_2025:
                continue

            paginas_l1_com_2025 += 1
            total_2025_l1 += len(itens_2025)
            self._processar_itens_materias_2025(
                itens_2025,
                payload,
                meta,
                pagina=pagina,
                por_chave_materia=por_chave_materia,
                tipos_novos_vistos=tipos_novos_vistos,
            )

        self.relatorio.materias_paginas_reaproveitadas_lote1 = paginas_l1_com_2025
        self.relatorio.materias_2025_encontradas_nas_paginas_lote1 = total_2025_l1

        # 2. Coleta da página 13 em diante até atingir a fronteira com 2024 (sem entrar no Lote 3!)
        pagina = 13
        ultima_pagina = 60
        paginas_novas = 0
        total_2025_novas = 0
        itens_pre_2025_fronteira = 0

        while pagina <= ultima_pagina:
            url = f"https://inhumas.nexlegis.com.br/api/materias?page={pagina}&per_page=50"
            bruto, meta = self.requisitar_e_salvar(url, etapa="1_materias_2025")
            if bruto is None or meta is None:
                break

            paginas_novas += 1
            payload = json.loads(bruto.decode("utf-8"))
            meta_pag = payload.get("meta") or {}
            ultima_pagina = int(
                payload.get("last_page") or meta_pag.get("last_page") or ultima_pagina
            )
            lista = payload.get("data") or []
            if not lista:
                break

            itens_2025 = []
            itens_pre_2025_pag = 0
            for item in lista:
                ano_item = int(item.get("ano") or 0)
                if ano_item == 2025:
                    itens_2025.append(item)
                elif ano_item < 2025:
                    itens_pre_2025_pag += 1

            total_2025_novas += len(itens_2025)
            itens_pre_2025_fronteira += itens_pre_2025_pag

            if itens_2025:
                self._processar_itens_materias_2025(
                    itens_2025,
                    payload,
                    meta,
                    pagina=pagina,
                    por_chave_materia=por_chave_materia,
                    tipos_novos_vistos=tipos_novos_vistos,
                )

            # Condição estrita de parada na fronteira 2025 -> 2024 (para não iniciar o Lote 3):
            # Paramos assim que uma página inteira não tiver mais nenhum item de 2025 (ou os últimos 10 itens forem todos < 2025 com movimentação < 2025)
            ultimos_10 = lista[-10:] if len(lista) >= 10 else lista
            todos_ultimos_10_pre_2025 = all(
                int(x.get("ano") or 0) < 2025
                and str(x.get("ultima_movimentacao") or x.get("data_publicacao") or "")
                < "2025-01-01"
                for x in ultimos_10
            )
            if (len(itens_2025) == 0 and itens_pre_2025_pag > 0) or todos_ultimos_10_pre_2025:
                break

            pagina += 1

        self.relatorio.materias_paginas_novas_coletadas = paginas_novas
        self.relatorio.materias_2025_encontradas_nas_paginas_novas = total_2025_novas
        self.relatorio.materias_2025_total_encontradas = total_2025_l1 + total_2025_novas
        self.relatorio.materias_pre_2025_na_fronteira_ignoradas = itens_pre_2025_fronteira

        for chave_m, ids_m in por_chave_materia.items():
            if len(ids_m) > 1:
                self.relatorio.duplicidades_identificadas_2025.append(
                    {
                        "entidade": "proposicao_2025",
                        "criterio": "(tipo_id, numero, ano)",
                        "tipo_id": chave_m[0],
                        "numero": chave_m[1],
                        "ano": chave_m[2],
                        "ids_encontrados": ids_m,
                    }
                )

        self.relatorio.novos_tipos_proposicao_2025 = list(tipos_novos_vistos.values())

    def _processar_itens_materias_2025(
        self,
        itens_2025: list[dict[str, Any]],
        payload: dict[str, Any],
        meta: MetadadosDocumentoBruto,
        *,
        pagina: int,
        por_chave_materia: dict[tuple[int, str, int], list[int]],
        tipos_novos_vistos: dict[int, dict[str, Any]],
    ) -> None:
        for item in itens_2025:
            chave_m = (
                int(item.get("tipo_id") or 0),
                str(item.get("numero") or "").strip(),
                2025,
            )
            por_chave_materia.setdefault(chave_m, []).append(int(item["id"]))
            t_id = item.get("tipo_id")
            t_desc = (item.get("tipo") or {}).get("descricao")
            if t_id is not None and int(t_id) not in TIPOS_CONHECIDOS:
                tipos_novos_vistos[int(t_id)] = {
                    "tipo_id": int(t_id),
                    "descricao": t_desc,
                    "exemplo_materia_id": item.get("id"),
                    "exemplo_nome": item.get("nome_materia"),
                    "origem": f"materias_page_{pagina}",
                }

        payload_filtrado_2025 = {**payload, "data": itens_2025}
        bruto_2025 = json.dumps(payload_filtrado_2025, ensure_ascii=False).encode("utf-8")
        meta_2025 = MetadadosDocumentoBruto(
            **{
                **asdict(meta),
                "hash_conteudo": calcular_sha256(bruto_2025),
                "tamanho_bytes": len(bruto_2025),
            }
        )
        pacote_mat = self.parser.parse_materias_list(bruto_2025, meta_2025)
        self.repo.carregar_pacote_materias(pacote_mat)

    def coletar_detalhes_sessoes_2025_e_pdfs(
        self,
        sessoes_2025_raw: list[dict[str, Any]],
        *,
        baixar_pdfs: bool = True,
    ) -> None:
        """Coleta `/api/sessoes/{id}` para as 73 sessões de 2025 e baixa os PDFs vinculados."""
        ids_2025 = sorted({int(s["id"]) for s in sessoes_2025_raw}, reverse=True)
        tipos_novos_vistos: dict[int, dict[str, Any]] = {
            item["tipo_id"]: item for item in self.relatorio.novos_tipos_proposicao_2025
        }
        urls_pdfs_para_baixar: list[tuple[int, str, str]] = []
        participantes_2025: dict[int, dict[str, Any]] = {}

        self.relatorio.sessoes_detalhes_2025_coletados = 0
        for sessao_id in ids_2025:
            url = f"https://inhumas.nexlegis.com.br/api/sessoes/{sessao_id}"
            bruto, meta = self.requisitar_e_salvar(url, etapa="2_sessao_detalhe_2025")
            if bruto is None or meta is None:
                continue

            self.relatorio.sessoes_detalhes_2025_coletados += 1
            payload_det = json.loads(bruto.decode("utf-8"))

            # Inspeciona participantes (presença, presidente, autores de pauta e votos)
            for p_item in payload_det.get("presenca") or []:
                ver_obj = p_item.get("vereador") or {}
                v_id = p_item.get("vereador_id") or ver_obj.get("id")
                if v_id is not None:
                    v_id_int = int(v_id)
                    reg_part = participantes_2025.setdefault(
                        v_id_int,
                        {
                            "id_origem_nexlegis": v_id_int,
                            "nome": ver_obj.get("nome"),
                            "nome_politico": ver_obj.get("nome_politico"),
                            "slug": ver_obj.get("slug"),
                            "sessoes_presenca_2025": 0,
                            "sessoes_presente_2025": 0,
                            "votos_2025": 0,
                            "curado_em_vereadores_mestre": v_id_int in IDS_VEREADORES_CURADOS,
                        },
                    )
                    reg_part["sessoes_presenca_2025"] += 1
                    sit_desc = str((p_item.get("situacao") or {}).get("descricao") or "").lower()
                    if "presente" in sit_desc:
                        reg_part["sessoes_presente_2025"] += 1

            # Verifica mídias PDF na sessão de 2025
            for midia in payload_det.get("midias") or []:
                pdf_url = midia.get("url")
                m_mime = str(midia.get("mime_type") or "").lower()
                if pdf_url and (
                    str(pdf_url).lower().endswith(".pdf") or m_mime == "application/pdf"
                ):
                    urls_pdfs_para_baixar.append(
                        (
                            sessao_id,
                            str(pdf_url),
                            f"https://inhumas.nexlegis.com.br/api/sessoes/{sessao_id}",
                        )
                    )

            # Inspeciona pautas e votações da sessão de 2025
            for pauta in payload_det.get("pautas") or []:
                mat = pauta.get("materia") or {}
                t_id = mat.get("tipo_id")
                t_desc = (mat.get("tipo") or {}).get("descricao")
                if t_id is not None and int(t_id) not in TIPOS_CONHECIDOS:
                    tipos_novos_vistos[int(t_id)] = {
                        "tipo_id": int(t_id),
                        "descricao": t_desc,
                        "exemplo_materia_id": mat.get("id"),
                        "exemplo_nome": mat.get("nome_materia"),
                        "origem": f"sessao_{sessao_id}_pauta",
                    }

                vot = pauta.get("votacao")
                if isinstance(vot, dict) and vot.get("votos"):
                    votos_lista = vot["votos"]
                    for v_obj in votos_lista:
                        vid_voto = v_obj.get("vereador_id")
                        if vid_voto is not None and int(vid_voto) in participantes_2025:
                            participantes_2025[int(vid_voto)]["votos_2025"] += 1

                    todos_favoraveis = all(
                        (v.get("voto") or {}).get("descricao") == "Favorável"
                        for v in votos_lista
                    )
                    if todos_favoraveis and vot.get("unanime") is False:
                        self.relatorio.dados_revisao_humana.append(
                            {
                                "tipo": "DIVERGENCIA_FLAG_UNANIME_VS_PLACAR_NOMINAL_2025",
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

            if len(pacote.presencas) == 0:
                self.relatorio.dados_revisao_humana.append(
                    {
                        "tipo": "SESSAO_2025_SEM_LISTA_PRESENCA",
                        "sessao_id": sessao_id,
                        "nome_sessao": pacote.sessao.nome_sessao,
                        "data_abertura": str(pacote.sessao.data_abertura),
                        "motivo": "Sessão de 2025 retornou array 'presenca' vazio na API.",
                    }
                )

        # Registra também autores de matérias de 2025 que eventualmente não apareçam em presenças
        for aut in self.repo.autorias.ativos.values():
            if not aut.vereador_id:
                continue
            vid_num = int(aut.vereador_id.split("-")[-1])
            if vid_num not in participantes_2025:
                ver_reg = self.repo.vereadores.ativos.get(aut.vereador_id)
                participantes_2025[vid_num] = {
                    "id_origem_nexlegis": vid_num,
                    "nome": ver_reg.nome_civil if ver_reg else None,
                    "nome_politico": ver_reg.nome_politico if ver_reg else None,
                    "slug": ver_reg.slug if ver_reg else None,
                    "sessoes_presenca_2025": 0,
                    "sessoes_presente_2025": 0,
                    "votos_2025": 0,
                    "curado_em_vereadores_mestre": vid_num in IDS_VEREADORES_CURADOS,
                }

        self.relatorio.vereadores_participantes_2025_identificados = len(participantes_2025)
        self.relatorio.novos_vereadores_e_aliases_2025 = [
            p
            for p in sorted(participantes_2025.values(), key=lambda x: x["id_origem_nexlegis"])
            if not p["curado_em_vereadores_mestre"]
        ]
        for nao_curado in self.relatorio.novos_vereadores_e_aliases_2025:
            self.relatorio.dados_revisao_humana.append(
                {
                    "tipo": "VEREADOR_ATUANTE_2025_NAO_CURADO",
                    **nao_curado,
                    "motivo": (
                        "Vereador atuante em sessões ou matérias de 2025 ainda não curado "
                        "em VEREADORES_MESTRE_INHUMAS; sinalizado para revisão humana sem fusão automática."
                    ),
                }
            )

        self.relatorio.novos_tipos_proposicao_2025 = list(tipos_novos_vistos.values())

        # Download de PDFs das sessões de 2025
        self.relatorio.pdfs_identificados_sessoes_2025 = len(urls_pdfs_para_baixar)
        if not baixar_pdfs:
            return
        self.relatorio.pdfs_baixados_com_sucesso = 0
        self.relatorio.pdfs_falhas = []
        urls_vistas: set[str] = set()
        for sessao_id, pdf_url, url_canonica in urls_pdfs_para_baixar:
            if pdf_url in urls_vistas:
                continue
            urls_vistas.add(pdf_url)
            conteudo_pdf, meta_pdf = self.requisitar_e_salvar(
                pdf_url,
                etapa=f"3_pdf_sessao_{sessao_id}",
                fonte_url_canonica=url_canonica,
                extensao="pdf",
                mime_esperado="application/pdf",
                url_temporaria=False,
            )
            if (
                conteudo_pdf is not None
                and meta_pdf is not None
                and conteudo_pdf.startswith(b"%PDF")
            ):
                self.relatorio.pdfs_baixados_com_sucesso += 1
            else:
                self.relatorio.pdfs_falhas.append(f"Sessão {sessao_id}: {pdf_url}")

    def validar_integridade_e_reprodutibilidade(self) -> None:
        """Verifica os hashes SHA-256 no disco e reexecuta a carga em memória para comprovar reprodutibilidade."""
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

        sessoes_2025_repo = [
            s for s in self.repo.sessoes.ativos.values() if s.ano == 2025
        ]
        props_2025_repo = [
            p for p in self.repo.proposicoes.ativos.values() if p.ano == 2025
        ]
        props_pre_2025_pauta = [
            p for p in self.repo.proposicoes.ativos.values() if p.ano < 2025
        ]
        props_parlamentares_2025 = [
            p for p in props_2025_repo if p.eh_proposicao_parlamentar
        ]
        docs_admin_2025 = [
            p for p in props_2025_repo if not p.eh_proposicao_parlamentar
        ]

        self.relatorio.sessoes_2025_armazenadas = len(sessoes_2025_repo)
        self.relatorio.presencas_2025_armazenadas = len(self.repo.presencas.ativos)
        self.relatorio.proposicoes_2025_armazenadas = len(props_2025_repo)
        self.relatorio.proposicoes_parlamentares_2025 = len(props_parlamentares_2025)
        self.relatorio.documentos_administrativos_2025 = len(docs_admin_2025)
        self.relatorio.proposicoes_anos_anteriores_em_pauta_2025 = len(props_pre_2025_pauta)
        self.relatorio.autorias_2025_armazenadas = len(self.repo.autorias.ativos)
        self.relatorio.tramitacoes_2025_armazenadas = len(self.repo.tramitacoes.ativos)
        self.relatorio.pauta_itens_2025_armazenados = len(self.repo.pauta_itens.ativos)
        self.relatorio.votacoes_2025_armazenadas = len(self.repo.votacoes.ativos)
        self.relatorio.votos_nominais_2025_armazenados = len(self.repo.votos.ativos)

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

        snapshot_path = self.lote2_dir / "snapshot_tratado_lote2.json"
        snapshot_data = {
            "execucao_id": self.relatorio.execucao_id,
            "lote": self.relatorio.lote,
            "ano_alvo": 2025,
            "municipio_id": self.config.municipio_id,
            "versao_coletor": self.config.versao_coletor,
            "gerado_em": datetime.now(UTC).isoformat(),
            "contagens": {
                "vereadores_total_api": len(self.repo.vereadores.ativos),
                "vereadores_participantes_2025": self.relatorio.vereadores_participantes_2025_identificados,
                "sessoes_2025": len(sessoes_2025_repo),
                "presencas_2025": len(self.repo.presencas.ativos),
                "proposicoes_2025_total": len(props_2025_repo),
                "proposicoes_parlamentares_2025": len(props_parlamentares_2025),
                "documentos_administrativos_2025": len(docs_admin_2025),
                "proposicoes_anos_anteriores_em_pauta_2025": len(props_pre_2025_pauta),
                "autorias_2025": len(self.repo.autorias.ativos),
                "tramitacoes_2025": len(self.repo.tramitacoes.ativos),
                "pauta_itens_2025": len(self.repo.pauta_itens.ativos),
                "votacoes_2025": len(self.repo.votacoes.ativos),
                "votos_nominais_2025": len(self.repo.votos.ativos),
            },
            "producao_legislativa_por_vereador_2025": self.repo.contar_producao_legislativa_por_vereador(),
        }
        snapshot_path.write_text(
            json.dumps(snapshot_data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        rel_snap = "data/raw/inhumas-go/nexlegis/2025/snapshot_tratado_lote2.json"
        if rel_snap not in self.relatorio.arquivos_e_manifestos_gerados:
            self.relatorio.arquivos_e_manifestos_gerados.append(rel_snap)

        self.relatorio.verificacao_integridade = {
            "arquivos_brutos_verificados_sha256": arquivos_verificados,
            "divergencias_sha256": divergencias_hash,
            "reexecucao_idempotente_confirmada": idempotente_ok,
            "proveniencia_100_porcento": rel_qualidade.proveniencia_100_porcento,
            "inconsistencias_cruzadas": rel_qualidade.inconsistencias_cruzadas,
            "aprovado_qualidade": rel_qualidade.aprovado_para_publicacao
            and len(divergencias_hash) == 0,
        }
        self.relatorio.finalizado_em = datetime.now(UTC).isoformat()
        self._salvar_checkpoint_manifesto()

    def executar(
        self,
        *,
        incluir_detalhes_sessoes_2025: bool = True,
        baixar_pdfs_sessoes_2025: bool = True,
        incluir_materias_2025: bool = True,
    ) -> RelatorioExecucaoLote2:
        try:
            self.verificar_robots_txt()
            sessoes_2025_raw = self.carregar_base_vereadores_e_indice_sessoes_2025()
            if incluir_materias_2025:
                self.coletar_materias_2025()
            if incluir_detalhes_sessoes_2025:
                self.coletar_detalhes_sessoes_2025_e_pdfs(
                    sessoes_2025_raw, baixar_pdfs=baixar_pdfs_sessoes_2025
                )
            self.validar_integridade_e_reprodutibilidade()
            return self.relatorio
        finally:
            self._client.close()


if __name__ == "__main__":
    import argparse

    parser_cli = argparse.ArgumentParser(description="Executor do Lote 2 Nexlegis (2025)")
    parser_cli.add_argument(
        "--etapa",
        choices=["materias_2025", "sessoes_2025", "completo"],
        default="completo",
    )
    args = parser_cli.parse_args()
    raiz = Path(__file__).resolve().parents[5]
    executor = ExecutorLote2Nexlegis(raiz, crawl_delay_segundos=3.05)
    if args.etapa == "materias_2025":
        rel = executor.executar(
            incluir_detalhes_sessoes_2025=False,
            baixar_pdfs_sessoes_2025=False,
            incluir_materias_2025=True,
        )
    elif args.etapa == "sessoes_2025":
        rel = executor.executar(
            incluir_detalhes_sessoes_2025=True,
            baixar_pdfs_sessoes_2025=False,
            incluir_materias_2025=True,
        )
    else:
        rel = executor.executar(
            incluir_detalhes_sessoes_2025=True,
            baixar_pdfs_sessoes_2025=True,
            incluir_materias_2025=True,
        )
    print(
        json.dumps(
            {
                "etapa": args.etapa,
                "total_requisicoes_realizadas": rel.total_requisicoes_realizadas,
                "intervalo_minimo_observado_seg": rel.intervalo_minimo_observado_seg,
                "sessoes_2025_encontradas_no_indice": rel.sessoes_2025_encontradas_no_indice,
                "sessoes_detalhes_2025_coletados": rel.sessoes_detalhes_2025_coletados,
                "materias_paginas_novas_coletadas": rel.materias_paginas_novas_coletadas,
                "materias_2025_total_encontradas": rel.materias_2025_total_encontradas,
                "pdfs_identificados_sessoes_2025": rel.pdfs_identificados_sessoes_2025,
                "pdfs_baixados_com_sucesso": rel.pdfs_baixados_com_sucesso,
                "novos_vereadores_e_aliases_2025": rel.novos_vereadores_e_aliases_2025,
                "novos_tipos_proposicao_2025": rel.novos_tipos_proposicao_2025,
                "verificacao_integridade": rel.verificacao_integridade,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
