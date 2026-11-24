"""Coletor incremental semanal do Nexlegis (Fase 4 — Distribuição, Retenção e Atualização Semanal).

Executa o ciclo Fetch -> Parse -> Load buscando apenas o delta de sessões e matérias
publicadas ou atualizadas desde a última carga no PostgreSQL 16, respeitando:
- Verificação prévia de `robots.txt`
- Intervalo mínimo educado (`>= 3,0s` por padrão entre requisições)
- Sanitização preventiva de CPF (LGPD) antes de gravar bruto ou persistir no banco
- Armazenamento bruto imutável em `data/raw/` com SHA-256 + manifesto em `incremental/YYYY-MM-DD/`
- Upsert 100% idempotente no PostgreSQL 16 (reexecução resulta em `novos=0, alterados=0`)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
from psycopg.rows import dict_row

from cerrado_aberto_coleta import __version__
from cerrado_aberto_coleta.config import MunicipioConfig, criar_config_municipio_padrao
from cerrado_aberto_coleta.nexlegis.loader import ResultadoCarga
from cerrado_aberto_coleta.nexlegis.lote1 import sanitizar_cpf_em_bytes_json
from cerrado_aberto_coleta.nexlegis.parser import NexlegisParser
from cerrado_aberto_coleta.nexlegis.postgres_loader import PostgresNexlegisRepository
from cerrado_aberto_coleta.nexlegis.schemas import (
    AutoriaRegistro,
    PautaItemRegistro,
    PresencaRegistro,
    ProposicaoRegistro,
    SessaoRegistro,
    TramitacaoRegistro,
    VotacaoRegistro,
    VotoNominalRegistro,
)
from cerrado_aberto_coleta.storage import LocalVersionedStorage, MetadadosDocumentoBruto

VERSAO_COLETOR_INCREMENTAL = f"cerrado-aberto-coleta/{__version__}-incremental-semanal"


@dataclass
class ItemArquivoIncremental:
    tipo_payload: str  # "sessoes_list" | "sessao_detalhe" | "materias_list"
    fonte_url: str
    caminho_armazenamento: str
    hash_sha256: str
    coletado_em: str
    status_http: int
    cpfs_mascarados: int = 0


@dataclass
class RelatorioColetaIncremental:
    execucao_id: str
    municipio_id: str
    ano: int
    versao_coletor: str
    iniciado_em: str
    finalizado_em: str | None = None
    robots_txt_permite_coleta: bool = True
    total_requisicoes: int = 0
    intervalo_minimo_seg: float | None = None
    sessoes_candidatas_ids: list[int] = field(default_factory=list)
    sessoes_detalhes_coletados: int = 0
    materias_paginas_coletadas: int = 0
    cpfs_mascarados_total: int = 0
    arquivos: list[ItemArquivoIncremental] = field(default_factory=list)
    por_tabela: dict[str, dict[str, int]] = field(default_factory=dict)
    contagem_total_banco: dict[str, int] = field(default_factory=dict)
    caminho_manifesto: str | None = None


def _robots_permite_api(robots_texto: str) -> bool:
    em_wildcard = False
    for linha in robots_texto.splitlines():
        limpa = linha.split("#", 1)[0].strip()
        if not limpa:
            continue
        lower = limpa.lower()
        if lower.startswith("user-agent:"):
            agente = limpa.split(":", 1)[1].strip()
            em_wildcard = agente == "*"
        elif em_wildcard and lower.startswith("disallow:"):
            regra = limpa.split(":", 1)[1].strip()
            if regra in ("/", "/api", "/api/"):
                return False
    return True


class ColetorIncrementalNexlegis:
    """Coleta incrementalmente o delta semanal de sessões e matérias de um ano no Nexlegis."""

    def __init__(
        self,
        *,
        repo_root: Path,
        municipio_id: str = "inhumas-go",
        ano: int = 2026,
        config: MunicipioConfig | None = None,
        http_client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        crawl_delay_segundos: float = 3.0,
        janela_revisao_dias: int = 14,
        max_paginas_sessoes: int = 2,
        max_paginas_materias: int = 3,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.municipio_id = municipio_id
        self.ano = ano
        self.config = config or criar_config_municipio_padrao()
        self.fonte_cfg = self.config.obter_fonte("nexlegis")
        self.storage = LocalVersionedStorage(self.repo_root / "data" / "raw")
        self.parser = NexlegisParser(municipio_id=municipio_id)
        self._sleep = sleep_fn
        self._crawl_delay = max(0.0, crawl_delay_segundos)
        self._janela_revisao_dias = janela_revisao_dias
        self._max_paginas_sessoes = max_paginas_sessoes
        self._max_paginas_materias = max_paginas_materias
        self._ultimo_ts: float | None = None
        self._intervalos: list[float] = []
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=self.fonte_cfg.timeout_segundos,
            follow_redirects=True,
        )

    def _aguardar_taxa(self) -> None:
        agora = time.monotonic()
        if self._ultimo_ts is not None:
            decorrido = agora - self._ultimo_ts
            restante = self._crawl_delay - decorrido
            if restante > 0:
                self._sleep(restante)
            novo_agora = time.monotonic()
            self._intervalos.append(round(novo_agora - self._ultimo_ts, 3))
            self._ultimo_ts = novo_agora
        else:
            self._ultimo_ts = agora

    def _get_com_retry(self, url: str) -> tuple[bytes, int, str]:
        ultimo_erro: Exception | None = None
        for tentativa in range(1, self.fonte_cfg.max_tentativas + 1):
            self._aguardar_taxa()
            try:
                resp = self._client.get(url)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"Status HTTP {resp.status_code} em {url}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                mime = resp.headers.get("content-type", "application/json").split(";")[0].strip()
                return resp.content, resp.status_code, mime
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                ultimo_erro = exc
                if tentativa < self.fonte_cfg.max_tentativas:
                    self._sleep((2**tentativa) + random.uniform(0.1, 0.5))
        raise RuntimeError(f"Falha ao baixar {url}: {ultimo_erro}") from ultimo_erro

    def _baixar_e_salvar_json(
        self, url: str, tipo_payload: str, relatorio: RelatorioColetaIncremental
    ) -> tuple[bytes, MetadadosDocumentoBruto]:
        bruto_original, status_http, mime_type = self._get_com_retry(url)
        relatorio.total_requisicoes += 1
        bruto_limpo, cpfs = sanitizar_cpf_em_bytes_json(bruto_original)
        relatorio.cpfs_mascarados_total += cpfs
        meta = self.storage.salvar_bruto(
            municipio_id=self.municipio_id,
            fonte_id="nexlegis",
            fonte_url=url,
            conteudo=bruto_limpo,
            mime_type=mime_type or "application/json",
            extensao="json",
            versao_coletor=VERSAO_COLETOR_INCREMENTAL,
            status_http=status_http,
            url_temporaria=False,
            coletado_em=datetime.now(UTC),
            ano_particao=self.ano,
        )
        relatorio.arquivos.append(
            ItemArquivoIncremental(
                tipo_payload=tipo_payload,
                fonte_url=url,
                caminho_armazenamento=meta.caminho_armazenamento,
                hash_sha256=meta.hash_conteudo,
                coletado_em=meta.coletado_em,
                status_http=status_http,
                cpfs_mascarados=cpfs,
            )
        )
        return bruto_limpo, meta

    def _consultar_watermark_postgres(
        self, conn: psycopg.Connection[Any]
    ) -> tuple[dict[int, date], dict[int, tuple[date | None, str | None]]]:
        sessoes_map: dict[int, date] = {}
        props_map: dict[int, tuple[date | None, str | None]] = {}
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id_origem_nexlegis, data_abertura
                FROM sessao
                WHERE municipio_id = %s AND ano = %s
                """,
                (self.municipio_id, self.ano),
            )
            for r in cur.fetchall():
                sessoes_map[int(r["id_origem_nexlegis"])] = r["data_abertura"]

            cur.execute(
                """
                SELECT id_origem_nexlegis, ultima_movimentacao, situacao_atual
                FROM proposicao
                WHERE municipio_id = %s AND ano = %s
                """,
                (self.municipio_id, self.ano),
            )
            for r in cur.fetchall():
                props_map[int(r["id_origem_nexlegis"])] = (
                    r["ultima_movimentacao"],
                    r["situacao_atual"],
                )
        return sessoes_map, props_map

    def _verificar_robots(self, relatorio: RelatorioColetaIncremental) -> None:
        base_origem = self.fonte_cfg.url_base.rstrip("/").removesuffix("/api")
        url_robots = f"{base_origem}/robots.txt"
        try:
            conteudo, _status, _mime = self._get_com_retry(url_robots)
            relatorio.total_requisicoes += 1
            permite = _robots_permite_api(conteudo.decode("utf-8", errors="ignore"))
            relatorio.robots_txt_permite_coleta = permite
            if not permite:
                raise PermissionError(f"robots.txt em {url_robots} bloqueia acesso à API.")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                relatorio.robots_txt_permite_coleta = True
            else:
                raise

    def executar(self, conn: psycopg.Connection[Any]) -> RelatorioColetaIncremental:
        """Executa o fluxo completo Fetch -> Parse -> Load incremental para o ano configurado."""
        execucao_id = str(uuid4())
        relatorio = RelatorioColetaIncremental(
            execucao_id=execucao_id,
            municipio_id=self.municipio_id,
            ano=self.ano,
            versao_coletor=VERSAO_COLETOR_INCREMENTAL,
            iniciado_em=datetime.now(UTC).isoformat(),
        )

        try:
            sessoes_existentes, props_existentes = self._consultar_watermark_postgres(conn)
            self._verificar_robots(relatorio)

            base_api = self.fonte_cfg.url_base.rstrip("/")
            sessoes_listadas_ano: list[SessaoRegistro] = []
            for pagina in range(1, self._max_paginas_sessoes + 1):
                url = f"{base_api}/sessoes?page={pagina}&per_page=20"
                bruto, meta = self._baixar_e_salvar_json(url, "sessoes_list", relatorio)
                lista_sessoes = self.parser.parse_sessoes_list(bruto, meta)
                encontrou_nova_na_pagina = False
                for s in lista_sessoes:
                    if s.ano != self.ano:
                        continue
                    sessoes_listadas_ano.append(s)
                    if s.id_origem_nexlegis not in sessoes_existentes:
                        encontrou_nova_na_pagina = True
                if not encontrou_nova_na_pagina:
                    break

            datas_referencia = [s.data_abertura for s in sessoes_listadas_ano] + list(
                sessoes_existentes.values()
            )
            data_mais_recente = max(datas_referencia) if datas_referencia else date(self.ano, 1, 1)
            data_corte_revisao = data_mais_recente - timedelta(days=self._janela_revisao_dias)

            sessoes_candidatas: dict[int, SessaoRegistro] = {}
            for s in sessoes_listadas_ano:
                eh_nova = s.id_origem_nexlegis not in sessoes_existentes
                eh_recente = s.data_abertura >= data_corte_revisao
                if eh_nova or eh_recente:
                    sessoes_candidatas[s.id_origem_nexlegis] = s

            relatorio.sessoes_candidatas_ids = sorted(sessoes_candidatas.keys(), reverse=True)

            # Fetch detalhes das sessões candidatas
            sessoes_parseadas: list[SessaoRegistro] = []
            presencas_parseadas: list[PresencaRegistro] = []
            props_pauta_parseadas: list[ProposicaoRegistro] = []
            pautas_parseadas: list[PautaItemRegistro] = []
            votacoes_parseadas: list[VotacaoRegistro] = []
            votos_parseados: list[VotoNominalRegistro] = []
            metadados_docs: list[MetadadosDocumentoBruto] = []

            for sessao_id_orig in relatorio.sessoes_candidatas_ids:
                url_det = f"{base_api}/sessoes/{sessao_id_orig}"
                bruto_det, meta_det = self._baixar_e_salvar_json(
                    url_det, "sessao_detalhe", relatorio
                )
                metadados_docs.append(meta_det)
                pacote = self.parser.parse_sessao_detalhe(bruto_det, meta_det)
                sessoes_parseadas.append(pacote.sessao)
                presencas_parseadas.extend(pacote.presencas)
                props_pauta_parseadas.extend(pacote.proposicoes_pauta)
                pautas_parseadas.extend(pacote.pauta_itens)
                votacoes_parseadas.extend(pacote.votacoes)
                votos_parseados.extend(pacote.votos_nominais)
                relatorio.sessoes_detalhes_coletados += 1

            # Fetch delta de matérias (para capturar autorias, tramitações e ementas completas)
            props_materias: list[ProposicaoRegistro] = []
            autorias_parseadas: list[AutoriaRegistro] = []
            tramitacoes_parseadas: list[TramitacaoRegistro] = []

            for pagina in range(1, self._max_paginas_materias + 1):
                url_mat = f"{base_api}/materias?page={pagina}&per_page=50"
                bruto_mat, meta_mat = self._baixar_e_salvar_json(
                    url_mat, "materias_list", relatorio
                )
                metadados_docs.append(meta_mat)
                relatorio.materias_paginas_coletadas += 1
                pacote_mat = self.parser.parse_materias_list(bruto_mat, meta_mat)

                novas_ou_atualizadas = 0
                props_ids_pagina_ano: set[str] = set()
                for prop in pacote_mat.proposicoes:
                    if prop.ano != self.ano:
                        continue
                    prev = props_existentes.get(prop.id_origem_nexlegis)
                    if prev is None or prev != (prop.ultima_movimentacao, prop.situacao_atual):
                        novas_ou_atualizadas += 1
                    props_materias.append(prop)
                    props_ids_pagina_ano.add(prop.proposicao_id)

                autorias_parseadas.extend(
                    a for a in pacote_mat.autorias if a.proposicao_id in props_ids_pagina_ano
                )
                tramitacoes_parseadas.extend(
                    t for t in pacote_mat.tramitacoes if t.proposicao_id in props_ids_pagina_ano
                )

                if novas_ou_atualizadas == 0 or pagina >= pacote_mat.ultima_pagina:
                    break

            relatorio.finalizado_em = datetime.now(UTC).isoformat()
            if self._intervalos:
                relatorio.intervalo_minimo_seg = min(self._intervalos)

            # Persistência idempotente no PostgreSQL 16
            por_tabela, contagem_total = _persistir_pacote_incremental_no_postgres(
                conn=conn,
                relatorio=relatorio,
                metadados_docs=metadados_docs,
                sessoes=sessoes_parseadas,
                presencas=presencas_parseadas,
                props_pauta=props_pauta_parseadas,
                props_materias=props_materias,
                autorias=autorias_parseadas,
                tramitacoes=tramitacoes_parseadas,
                pauta_itens=pautas_parseadas,
                votacoes=votacoes_parseadas,
                votos=votos_parseados,
            )
            relatorio.por_tabela = por_tabela
            relatorio.contagem_total_banco = contagem_total

            # Grava manifesto auditável da execução incremental
            dia_iso = datetime.now(UTC).strftime("%Y-%m-%d")
            dir_manifesto = (
                self.repo_root
                / "data"
                / "raw"
                / self.municipio_id
                / "nexlegis"
                / "incremental"
                / dia_iso
            )
            dir_manifesto.mkdir(parents=True, exist_ok=True)
            arq_manifesto = dir_manifesto / f"manifesto_{relatorio.execucao_id}.json"
            relatorio.caminho_manifesto = str(arq_manifesto.relative_to(self.repo_root)).replace(
                "\\", "/"
            )
            arq_manifesto.write_text(
                json.dumps(asdict(relatorio), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return relatorio
        finally:
            if self._owns_client:
                self._client.close()


def _persistir_pacote_incremental_no_postgres(
    *,
    conn: psycopg.Connection[Any],
    relatorio: RelatorioColetaIncremental,
    metadados_docs: list[MetadadosDocumentoBruto],
    sessoes: list[SessaoRegistro],
    presencas: list[PresencaRegistro],
    props_pauta: list[ProposicaoRegistro],
    props_materias: list[ProposicaoRegistro],
    autorias: list[AutoriaRegistro],
    tramitacoes: list[TramitacaoRegistro],
    pauta_itens: list[PautaItemRegistro],
    votacoes: list[VotacaoRegistro],
    votos: list[VotoNominalRegistro],
) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    pg_repo = PostgresNexlegisRepository(conn)
    res_vocab = pg_repo.sincronizar_vocabulario_tipos_proposicao(relatorio.municipio_id)
    res_exec = pg_repo.registrar_execucao_coleta(
        execucao_id=relatorio.execucao_id,
        municipio_id=relatorio.municipio_id,
        fonte_id="nexlegis",
        versao_coletor=relatorio.versao_coletor,
        iniciado_em=relatorio.iniciado_em,
        finalizado_em=relatorio.finalizado_em,
        status="SUCESSO",
        registros_lidos=len(metadados_docs),
        registros_novos=len(metadados_docs),
        registros_alterados=0,
        registros_inalterados=0,
        relatorio_qualidade={
            "modo": "INCREMENTAL_SEMANAL",
            "sessoes_candidatas_ids": relatorio.sessoes_candidatas_ids,
            "cpfs_mascarados_total": relatorio.cpfs_mascarados_total,
        },
    )
    res_docs = pg_repo.carregar_documentos_brutos(metadados_docs, execucao_id=relatorio.execucao_id)
    res_ses = pg_repo.carregar_sessoes(sessoes)
    res_pres = pg_repo.carregar_presencas(presencas)

    # Primeiro garante todas as proposições de pauta sem sobrescrever existentes;
    # depois atualiza com os dados completos de `/api/materias`.
    res_prop_pauta = pg_repo.carregar_proposicoes(props_pauta, sobrescrever_existentes=False)
    res_prop_mat = pg_repo.carregar_proposicoes(props_materias, sobrescrever_existentes=True)
    res_prop = ResultadoCarga(
        lidos=res_prop_pauta.lidos + res_prop_mat.lidos,
        novos=res_prop_pauta.novos + res_prop_mat.novos,
        alterados=res_prop_pauta.alterados + res_prop_mat.alterados,
        inalterados=res_prop_pauta.inalterados + res_prop_mat.inalterados,
    )
    res_aut = pg_repo.carregar_autorias(autorias)
    res_tram = pg_repo.carregar_tramitacoes(tramitacoes)
    res_pauta = pg_repo.carregar_pauta_itens(pauta_itens)
    res_vot = pg_repo.carregar_votacoes(votacoes)
    res_voto = pg_repo.carregar_votos_nominais(votos)

    por_tabela = {
        "de_para_tipo_proposicao": asdict(res_vocab),
        "coleta_execucao": asdict(res_exec),
        "documento_bruto": asdict(res_docs),
        "sessao": asdict(res_ses),
        "presenca": asdict(res_pres),
        "proposicao": asdict(res_prop),
        "autoria": asdict(res_aut),
        "tramitacao": asdict(res_tram),
        "pauta_item": asdict(res_pauta),
        "votacao": asdict(res_vot),
        "voto": asdict(res_voto),
    }
    return por_tabela, pg_repo.contar_registros_por_tabela(relatorio.municipio_id)


def carregar_incrementais_em_disco_no_postgres(
    conn: psycopg.Connection[Any],
    repo_root: Path,
    *,
    municipio_id: str = "inhumas-go",
) -> list[dict[str, Any]]:
    """Reaplica offline e de forma idempotente todos os manifestos incrementais salvos em `data/raw/`."""
    raiz = Path(repo_root)
    base_inc = raiz / "data" / "raw" / municipio_id / "nexlegis" / "incremental"
    if not base_inc.exists():
        return []

    storage = LocalVersionedStorage(raiz / "data" / "raw")
    parser = NexlegisParser(municipio_id=municipio_id)
    resultados: list[dict[str, Any]] = []

    for arq_manifesto in sorted(base_inc.rglob("manifesto_*.json")):
        dados = json.loads(arq_manifesto.read_text(encoding="utf-8"))
        relatorio = RelatorioColetaIncremental(
            execucao_id=dados["execucao_id"],
            municipio_id=dados["municipio_id"],
            ano=int(dados["ano"]),
            versao_coletor=dados["versao_coletor"],
            iniciado_em=dados["iniciado_em"],
            finalizado_em=dados.get("finalizado_em"),
            sessoes_candidatas_ids=list(dados.get("sessoes_candidatas_ids") or []),
            cpfs_mascarados_total=int(dados.get("cpfs_mascarados_total") or 0),
        )

        metadados_docs: list[MetadadosDocumentoBruto] = []
        sessoes: list[SessaoRegistro] = []
        presencas: list[PresencaRegistro] = []
        props_pauta: list[ProposicaoRegistro] = []
        props_materias: list[ProposicaoRegistro] = []
        autorias: list[AutoriaRegistro] = []
        tramitacoes: list[TramitacaoRegistro] = []
        pauta_itens: list[PautaItemRegistro] = []
        votacoes: list[VotacaoRegistro] = []
        votos: list[VotoNominalRegistro] = []

        for item in dados.get("arquivos", []):
            tipo = item["tipo_payload"]
            if tipo not in ("sessao_detalhe", "materias_list"):
                continue
            caminho_rel = item["caminho_armazenamento"]
            caminho_arq = raiz / "data" / "raw" / caminho_rel
            caminho_meta = caminho_arq.with_suffix(caminho_arq.suffix + ".meta.json")
            if not caminho_arq.exists() or not caminho_meta.exists():
                continue
            bruto = storage.ler_bruto(caminho_rel)
            meta = MetadadosDocumentoBruto(**json.loads(caminho_meta.read_text(encoding="utf-8")))
            metadados_docs.append(meta)
            if tipo == "sessao_detalhe":
                pacote = parser.parse_sessao_detalhe(bruto, meta)
                sessoes.append(pacote.sessao)
                presencas.extend(pacote.presencas)
                props_pauta.extend(pacote.proposicoes_pauta)
                pauta_itens.extend(pacote.pauta_itens)
                votacoes.extend(pacote.votacoes)
                votos.extend(pacote.votos_nominais)
            elif tipo == "materias_list":
                pacote_m = parser.parse_materias_list(bruto, meta)
                props_ids_ano: set[str] = set()
                for p in pacote_m.proposicoes:
                    if p.ano == relatorio.ano:
                        props_materias.append(p)
                        props_ids_ano.add(p.proposicao_id)
                autorias.extend(a for a in pacote_m.autorias if a.proposicao_id in props_ids_ano)
                tramitacoes.extend(
                    t for t in pacote_m.tramitacoes if t.proposicao_id in props_ids_ano
                )

        por_tabela, contagem_total = _persistir_pacote_incremental_no_postgres(
            conn=conn,
            relatorio=relatorio,
            metadados_docs=metadados_docs,
            sessoes=sessoes,
            presencas=presencas,
            props_pauta=props_pauta,
            props_materias=props_materias,
            autorias=autorias,
            tramitacoes=tramitacoes,
            pauta_itens=pauta_itens,
            votacoes=votacoes,
            votos=votos,
        )
        resultados.append(
            {
                "execucao_id": relatorio.execucao_id,
                "por_tabela": por_tabela,
                "contagem_total_banco": contagem_total,
            }
        )

    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coletor incremental semanal do Nexlegis (Cerrado Aberto)."
    )
    parser.add_argument("--municipio-id", default="inhumas-go")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--crawl-delay", type=float, default=3.0)
    args = parser.parse_args()

    raiz_repo = Path(__file__).resolve().parents[5]
    db_url = os.environ.get("DATABASE_URL")
    pg_srv = None
    try:
        if not db_url:
            import pgserver

            pgdata_dir = (raiz_repo / "data" / "pgdata").resolve()
            pgdata_dir.mkdir(parents=True, exist_ok=True)
            conf_path = pgdata_dir / "postgresql.conf"
            if conf_path.exists() and "\nfsync = off" not in conf_path.read_text(
                encoding="utf-8", errors="ignore"
            ):
                with conf_path.open("a", encoding="utf-8") as fp:
                    fp.write("\nfsync = off\n")
            pg_srv = pgserver.get_server(str(pgdata_dir))
            db_url = pg_srv.get_uri()

        with psycopg.connect(db_url) as conexao:
            coletor = ColetorIncrementalNexlegis(
                repo_root=raiz_repo,
                municipio_id=args.municipio_id,
                ano=args.ano,
                crawl_delay_segundos=args.crawl_delay,
            )
            relatorio = coletor.executar(conexao)
            print(json.dumps(asdict(relatorio), ensure_ascii=False, indent=2))
    finally:
        if pg_srv is not None:
            pg_srv.cleanup()


if __name__ == "__main__":
    main()
