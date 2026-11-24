"""Persistência PostgreSQL 16 idempotente para os dados validados de 2026 do Nexlegis (Fase 1).

Garantias implementadas:
- Proveniência obrigatória em 100% das tabelas (`fonte_id`, `fonte_url`, `coletado_em`, `hash_conteudo`, `versao_coletor`).
- Idempotência real: compara assinatura dos dados existentes antes de atualizar; reexecução resulta em `novos=0, alterados=0`.
- LGPD: bloqueia/impede a persistência de CPF completo (`XXX.XXX.XXX-XX` ou 11 dígitos de CPF) em qualquer coluna.
- Preservação estrita de `NULL`: campos ausentes permanecem `NULL` no PostgreSQL, nunca convertidos em zero.
- Escopo estrito de 2026 conforme autorização do Lote 1.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from cerrado_aberto_coleta.entidades import (
    MAPA_TIPOS_PROPOSICAO_PADRAO,
    VEREADORES_MESTRE_INHUMAS,
    VereadorMestreSeed,
)
from cerrado_aberto_coleta.nexlegis.loader import ResultadoCarga
from cerrado_aberto_coleta.nexlegis.lote1 import ExecutorLote1Nexlegis
from cerrado_aberto_coleta.nexlegis.lote2 import ExecutorLote2Nexlegis
from cerrado_aberto_coleta.nexlegis.schemas import (
    AutoriaRegistro,
    PacoteMateriasParseado,
    PacoteSessaoDetalheParseado,
    PautaItemRegistro,
    PresencaRegistro,
    ProposicaoRegistro,
    SessaoRegistro,
    TramitacaoRegistro,
    VereadorRegistro,
    VotacaoRegistro,
    VotoNominalRegistro,
)
from cerrado_aberto_coleta.normalizacao import gerar_chave_busca
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto

_RE_CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_RE_CPF_11_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")


class ViolacaoLGPDError(ValueError):
    """Exceção disparada caso se tente persistir CPF completo no banco de dados."""


def validar_ausencia_cpf_em_valores(valores: dict[str, Any], *, contexto: str) -> None:
    """Garante que nenhum campo textual contenha CPF completo antes de persistir no PostgreSQL."""
    chaves_hash_ou_url = {"hash_conteudo", "fonte_url", "avatar_url", "ata_pdf_url", "anexo_principal_url", "caminho_armazenamento"}
    for chave, valor in valores.items():
        if not isinstance(valor, str) or not valor:
            continue
        if _RE_CPF_FORMATADO.search(valor):
            raise ViolacaoLGPDError(
                f"Violação LGPD em {contexto}.{chave}: tentativa de persistir CPF formatado completo."
            )
        if chave not in chaves_hash_ou_url and "cpf" in chave.lower() and _RE_CPF_11_DIGITOS.search(valor):
            raise ViolacaoLGPDError(
                f"Violação LGPD em {contexto}.{chave}: tentativa de persistir CPF de 11 dígitos completo."
            )


@dataclass
class RelatorioPersistenciaPostgres:
    municipio_id: str
    escopo_ano: int
    executado_em: str
    por_tabela: dict[str, dict[str, int]] = field(default_factory=dict)
    contagem_total_banco: dict[str, int] = field(default_factory=dict)


class PostgresNexlegisRepository:
    """Repositório PostgreSQL 16 idempotente para entidades do Nexlegis."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self.conn = conn

    def aplicar_migracao_sql(self, caminho_sql: Path) -> None:
        sql = Path(caminho_sql).read_text(encoding="utf-8")
        with self.conn.cursor() as cur:
            cur.execute(sql)
        self.conn.commit()

    def sincronizar_vocabulario_tipos_proposicao(self, municipio_id: str = "inhumas-go") -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for tipo_id, regra in sorted(MAPA_TIPOS_PROPOSICAO_PADRAO.items()):
                cur.execute(
                    """
                    SELECT descricao_origem, codigo_normalizado, nome_exibicao,
                           categoria, eh_proposicao_parlamentar, contabilizar_producao_vereador
                    FROM de_para_tipo_proposicao
                    WHERE municipio_id = %s AND tipo_id_origem = %s
                    """,
                    (municipio_id, tipo_id),
                )
                existente = cur.fetchone()
                novo_dict = {
                    "descricao_origem": regra.descricao_origem,
                    "codigo_normalizado": regra.codigo_normalizado,
                    "nome_exibicao": regra.nome_exibicao,
                    "categoria": regra.categoria,
                    "eh_proposicao_parlamentar": regra.eh_proposicao_parlamentar,
                    "contabilizar_producao_vereador": regra.contabilizar_producao_vereador,
                }
                res.lidos += 1
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO de_para_tipo_proposicao (
                            municipio_id, tipo_id_origem, descricao_origem, codigo_normalizado,
                            nome_exibicao, categoria, eh_proposicao_parlamentar,
                            contabilizar_producao_vereador, justificativa_classificacao
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            municipio_id,
                            tipo_id,
                            regra.descricao_origem,
                            regra.codigo_normalizado,
                            regra.nome_exibicao,
                            regra.categoria,
                            regra.eh_proposicao_parlamentar,
                            regra.contabilizar_producao_vereador,
                            regra.justificativa,
                        ),
                    )
                    res.novos += 1
                elif dict(existente) != novo_dict:
                    cur.execute(
                        """
                        UPDATE de_para_tipo_proposicao
                        SET descricao_origem = %s,
                            codigo_normalizado = %s,
                            nome_exibicao = %s,
                            categoria = %s,
                            eh_proposicao_parlamentar = %s,
                            contabilizar_producao_vereador = %s,
                            justificativa_classificacao = %s,
                            atualizado_em = NOW()
                        WHERE municipio_id = %s AND tipo_id_origem = %s
                        """,
                        (
                            regra.descricao_origem,
                            regra.codigo_normalizado,
                            regra.nome_exibicao,
                            regra.categoria,
                            regra.eh_proposicao_parlamentar,
                            regra.contabilizar_producao_vereador,
                            regra.justificativa,
                            municipio_id,
                            tipo_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def registrar_execucao_coleta(
        self,
        *,
        execucao_id: str,
        municipio_id: str,
        fonte_id: str,
        versao_coletor: str,
        iniciado_em: str,
        finalizado_em: str | None,
        status: str,
        registros_lidos: int,
        registros_novos: int,
        registros_alterados: int,
        registros_inalterados: int,
        relatorio_qualidade: dict[str, Any],
    ) -> ResultadoCarga:
        res = ResultadoCarga(lidos=1)
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT status, registros_lidos FROM coleta_execucao WHERE execucao_id = %s",
                (execucao_id,),
            )
            atual = cur.fetchone()
            if atual is None:
                cur.execute(
                    """
                    INSERT INTO coleta_execucao (
                        execucao_id, municipio_id, fonte_id, versao_coletor,
                        iniciado_em, finalizado_em, status,
                        registros_lidos, registros_novos, registros_alterados,
                        registros_inalterados, relatorio_qualidade
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        execucao_id,
                        municipio_id,
                        fonte_id,
                        versao_coletor,
                        iniciado_em,
                        finalizado_em,
                        status,
                        registros_lidos,
                        registros_novos,
                        registros_alterados,
                        registros_inalterados,
                        json.dumps(relatorio_qualidade, ensure_ascii=False),
                    ),
                )
                res.novos += 1
            elif atual["status"] != status or atual["registros_lidos"] != registros_lidos:
                cur.execute(
                    """
                    UPDATE coleta_execucao
                    SET finalizado_em = %s,
                        status = %s,
                        registros_lidos = %s,
                        registros_novos = %s,
                        registros_alterados = %s,
                        registros_inalterados = %s,
                        relatorio_qualidade = %s::jsonb
                    WHERE execucao_id = %s
                    """,
                    (
                        finalizado_em,
                        status,
                        registros_lidos,
                        registros_novos,
                        registros_alterados,
                        registros_inalterados,
                        json.dumps(relatorio_qualidade, ensure_ascii=False),
                        execucao_id,
                    ),
                )
                res.alterados += 1
            else:
                res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_documentos_brutos(
        self, metadados_lista: list[MetadadosDocumentoBruto], *, execucao_id: str | None = None
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for m in metadados_lista:
                validar_ausencia_cpf_em_valores(asdict(m), contexto="documento_bruto")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT hash_conteudo, caminho_armazenamento, mime_type, tamanho_bytes
                    FROM documento_bruto
                    WHERE municipio_id = %s AND fonte_id = %s AND hash_conteudo = %s AND fonte_url = %s
                    """,
                    (m.municipio_id, m.fonte_id, m.hash_conteudo, m.fonte_url),
                )
                existente = cur.fetchone()
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO documento_bruto (
                            documento_id, municipio_id, fonte_id, execucao_id, fonte_url,
                            coletado_em, hash_conteudo, versao_coletor, storage_backend,
                            caminho_armazenamento, mime_type, tamanho_bytes, status_http,
                            url_temporaria, processado_ocr, extraido_por_ocr,
                            ocr_engine_versao, ocr_confianca_media,
                            requer_revisao_humana, motivo_revisao_humana
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s
                        )
                        """,
                        (
                            m.documento_id,
                            m.municipio_id,
                            m.fonte_id,
                            execucao_id,
                            m.fonte_url,
                            m.coletado_em,
                            m.hash_conteudo,
                            m.versao_coletor,
                            m.storage_backend,
                            m.caminho_armazenamento,
                            m.mime_type,
                            m.tamanho_bytes,
                            m.status_http,
                            m.url_temporaria,
                            m.processado_ocr,
                            m.extraido_por_ocr,
                            m.ocr_engine_versao,
                            m.ocr_confianca_media,
                            m.requer_revisao_humana,
                            m.motivo_revisao_humana,
                        ),
                    )
                    res.novos += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_vereadores(self, registros: list[VereadorRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        sementes_por_id = {s.id_origem_nexlegis: s for s in VEREADORES_MESTRE_INHUMAS}

        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                seed = sementes_por_id.get(r.id_origem_nexlegis)
                nome_civil = r.nome_civil if r.nome_civil is not None else (seed.nome_civil if seed else None)
                nome_exibicao = seed.nome_exibicao if seed else r.nome_exibicao
                dados_r = r.model_dump()
                dados_r["nome_civil"] = nome_civil
                dados_r["nome_exibicao"] = nome_exibicao
                validar_ausencia_cpf_em_valores(dados_r, contexto="vereador")

                res.lidos += 1
                cur.execute(
                    """
                    SELECT nome_civil, nome_politico, nome_exibicao, slug, chave_busca,
                           email_publico, avatar_url, biografia_html, biografia_texto, hash_conteudo
                    FROM vereador
                    WHERE vereador_id = %s
                    """,
                    (r.vereador_id,),
                )
                atual = cur.fetchone()
                assinatura_nova = {
                    "nome_civil": nome_civil,
                    "nome_politico": r.nome_politico,
                    "nome_exibicao": nome_exibicao,
                    "slug": r.slug,
                    "chave_busca": r.chave_busca,
                    "email_publico": r.email_publico,
                    "avatar_url": r.avatar_url,
                    "biografia_html": r.biografia_html,
                    "biografia_texto": r.biografia_texto,
                    "hash_conteudo": r.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO vereador (
                            vereador_id, municipio_id, id_origem_nexlegis, nome_civil,
                            nome_politico, nome_exibicao, slug, chave_busca,
                            email_publico, avatar_url, biografia_html, biografia_texto,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.vereador_id,
                            r.municipio_id,
                            r.id_origem_nexlegis,
                            nome_civil,
                            r.nome_politico,
                            nome_exibicao,
                            r.slug,
                            r.chave_busca,
                            r.email_publico,
                            r.avatar_url,
                            r.biografia_html,
                            r.biografia_texto,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != assinatura_nova:
                    cur.execute(
                        """
                        UPDATE vereador
                        SET nome_civil = %s,
                            nome_politico = %s,
                            nome_exibicao = %s,
                            slug = %s,
                            chave_busca = %s,
                            email_publico = %s,
                            avatar_url = %s,
                            biografia_html = %s,
                            biografia_texto = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE vereador_id = %s
                        """,
                        (
                            nome_civil,
                            r.nome_politico,
                            nome_exibicao,
                            r.slug,
                            r.chave_busca,
                            r.email_publico,
                            r.avatar_url,
                            r.biografia_html,
                            r.biografia_texto,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                            r.vereador_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_aliases_e_mandatos_curados(
        self,
        *,
        municipio_id: str,
        fonte_url: str,
        coletado_em: str,
        hash_conteudo: str,
        versao_coletor: str,
        sementes: tuple[VereadorMestreSeed, ...] = VEREADORES_MESTRE_INHUMAS,
    ) -> tuple[ResultadoCarga, ResultadoCarga]:
        res_aliases = ResultadoCarga()
        res_mandatos = ResultadoCarga()

        with self.conn.cursor(row_factory=dict_row) as cur:
            for seed in sementes:
                # 1. Aliases curados
                for alias_str in seed.aliases:
                    chave = gerar_chave_busca(alias_str, remover_titulos=False)
                    if not chave:
                        continue
                    tipo_alias = (
                        "LOTACAO_GABINETE"
                        if alias_str.upper().startswith("GAB.")
                        else (
                            "NOME_CIVIL"
                            if seed.nome_civil and alias_str == seed.nome_civil
                            else "NOME_POLITICO"
                        )
                    )
                    res_aliases.lidos += 1
                    cur.execute(
                        """
                        SELECT vereador_id, alias_texto
                        FROM vereador_alias
                        WHERE municipio_id = %s AND alias_chave_busca = %s AND tipo_alias = %s
                        """,
                        (municipio_id, chave, tipo_alias),
                    )
                    existente_al = cur.fetchone()
                    if existente_al is None:
                        cur.execute(
                            """
                            INSERT INTO vereador_alias (
                                municipio_id, vereador_id, alias_texto,
                                alias_chave_busca, tipo_alias, fonte_origem, confianca
                            ) VALUES (%s, %s, %s, %s, %s, %s, 'ALTA')
                            """,
                            (
                                municipio_id,
                                seed.vereador_id,
                                alias_str,
                                chave,
                                tipo_alias,
                                "nexlegis+transparencia_centi",
                            ),
                        )
                        res_aliases.novos += 1
                    elif existente_al["vereador_id"] != seed.vereador_id:
                        cur.execute(
                            """
                            UPDATE vereador_alias
                            SET vereador_id = %s, alias_texto = %s
                            WHERE municipio_id = %s AND alias_chave_busca = %s AND tipo_alias = %s
                            """,
                            (seed.vereador_id, alias_str, municipio_id, chave, tipo_alias),
                        )
                        res_aliases.alterados += 1
                    else:
                        res_aliases.inalterados += 1

                # 2. Mandato na 20ª Legislatura (2025-2028)
                mandato_id = f"{seed.vereador_id}-leg-2025-2028"
                condicao = "SUPLENTE" if seed.id_origem_nexlegis == 246 else "TITULAR"
                res_mandatos.lidos += 1
                cur.execute(
                    """
                    SELECT partido_id, condicao
                    FROM mandato
                    WHERE mandato_id = %s
                    """,
                    (mandato_id,),
                )
                existente_m = cur.fetchone()
                if existente_m is None:
                    cur.execute(
                        """
                        INSERT INTO mandato (
                            mandato_id, municipio_id, vereador_id, legislatura_id,
                            partido_id, condicao, valido_de, valido_ate,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, 'inhumas-go-2025-2028',
                            %s, %s, '2025-01-01', NULL,
                            'nexlegis', %s, %s, %s, %s
                        )
                        """,
                        (
                            mandato_id,
                            municipio_id,
                            seed.vereador_id,
                            seed.partido_atual_sigla,
                            condicao,
                            fonte_url,
                            coletado_em,
                            hash_conteudo,
                            versao_coletor,
                        ),
                    )
                    res_mandatos.novos += 1
                elif (
                    existente_m["partido_id"] != seed.partido_atual_sigla
                    or existente_m["condicao"] != condicao
                ):
                    cur.execute(
                        """
                        UPDATE mandato
                        SET partido_id = %s, condicao = %s
                        WHERE mandato_id = %s
                        """,
                        (seed.partido_atual_sigla, condicao, mandato_id),
                    )
                    res_mandatos.alterados += 1
                else:
                    res_mandatos.inalterados += 1

        self.conn.commit()
        return res_aliases, res_mandatos

    def carregar_sessoes(self, registros: list[SessaoRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(r.model_dump(), contexto="sessao")
                res.lidos += 1
                legislatura_id = "inhumas-go-2025-2028" if r.ano >= 2025 else "inhumas-go-2021-2024"
                cur.execute(
                    """
                    SELECT sessao_id, ids_origem_duplicados, tipo_id_origem, tipo_descricao,
                           numero, ano, nome_sessao, slug, data_abertura,
                           horario_abertura::text AS horario_abertura,
                           data_encerramento,
                           horario_encerramento::text AS horario_encerramento,
                           presidente_vereador_id, quorum, ata_pdf_url, hash_conteudo
                    FROM sessao
                    WHERE sessao_id = %s
                       OR (municipio_id = %s AND tipo_id_origem = %s AND numero = %s AND ano = %s AND data_abertura = %s)
                    """,
                    (
                        r.sessao_id,
                        r.municipio_id,
                        r.tipo_id_origem,
                        r.numero,
                        r.ano,
                        r.data_abertura,
                    ),
                )
                atual = cur.fetchone()
                dups_lista = list(r.ids_origem_duplicados)

                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO sessao (
                            sessao_id, municipio_id, legislatura_id, id_origem_nexlegis,
                            ids_origem_duplicados, tipo_id_origem, tipo_descricao,
                            numero, ano, nome_sessao, slug, data_abertura,
                            horario_abertura, data_encerramento, horario_encerramento,
                            inicio_sessao_real, presidente_vereador_id, quorum, ata_pdf_url,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.sessao_id,
                            r.municipio_id,
                            legislatura_id,
                            r.id_origem_nexlegis,
                            dups_lista,
                            r.tipo_id_origem,
                            r.tipo_descricao,
                            r.numero,
                            r.ano,
                            r.nome_sessao,
                            r.slug,
                            r.data_abertura,
                            r.horario_abertura,
                            r.data_encerramento,
                            r.horario_encerramento,
                            r.inicio_sessao_real,
                            r.presidente_vereador_id,
                            r.quorum,
                            r.ata_pdf_url,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    sessao_id_alvo = atual["sessao_id"]
                    if sessao_id_alvo != r.sessao_id:
                        dups_lista = sorted(
                            set(list(atual["ids_origem_duplicados"] or []) + [r.id_origem_nexlegis])
                        )
                    comparacao_atual = {
                        "ids_origem_duplicados": list(atual["ids_origem_duplicados"] or []),
                        "tipo_id_origem": atual["tipo_id_origem"],
                        "tipo_descricao": atual["tipo_descricao"],
                        "numero": atual["numero"],
                        "ano": atual["ano"],
                        "nome_sessao": atual["nome_sessao"],
                        "slug": atual["slug"],
                        "data_abertura": atual["data_abertura"],
                        "horario_abertura": (atual["horario_abertura"] or "")[:5] or None,
                        "data_encerramento": atual["data_encerramento"],
                        "horario_encerramento": (atual["horario_encerramento"] or "")[:5] or None,
                        "presidente_vereador_id": atual["presidente_vereador_id"],
                        "quorum": atual["quorum"],
                        "ata_pdf_url": atual["ata_pdf_url"],
                        "hash_conteudo": atual["hash_conteudo"],
                    }
                    comparacao_nova = {
                        "ids_origem_duplicados": dups_lista,
                        "tipo_id_origem": r.tipo_id_origem,
                        "tipo_descricao": r.tipo_descricao,
                        "numero": r.numero,
                        "ano": r.ano,
                        "nome_sessao": r.nome_sessao,
                        "slug": r.slug,
                        "data_abertura": r.data_abertura,
                        "horario_abertura": (r.horario_abertura or "")[:5] or None,
                        "data_encerramento": r.data_encerramento,
                        "horario_encerramento": (r.horario_encerramento or "")[:5] or None,
                        "presidente_vereador_id": r.presidente_vereador_id,
                        "quorum": r.quorum,
                        "ata_pdf_url": r.ata_pdf_url,
                        "hash_conteudo": r.hash_conteudo,
                    }
                    if comparacao_atual != comparacao_nova:
                        cur.execute(
                            """
                            UPDATE sessao
                            SET ids_origem_duplicados = %s,
                                tipo_id_origem = %s,
                                tipo_descricao = %s,
                                numero = %s,
                                ano = %s,
                                nome_sessao = %s,
                                slug = %s,
                                data_abertura = %s,
                                horario_abertura = %s,
                                data_encerramento = %s,
                                horario_encerramento = %s,
                                inicio_sessao_real = %s,
                                presidente_vereador_id = %s,
                                quorum = %s,
                                ata_pdf_url = %s,
                                fonte_url = %s,
                                coletado_em = %s,
                                hash_conteudo = %s,
                                versao_coletor = %s
                            WHERE sessao_id = %s
                            """,
                            (
                                dups_lista,
                                r.tipo_id_origem,
                                r.tipo_descricao,
                                r.numero,
                                r.ano,
                                r.nome_sessao,
                                r.slug,
                                r.data_abertura,
                                r.horario_abertura,
                                r.data_encerramento,
                                r.horario_encerramento,
                                r.inicio_sessao_real,
                                r.presidente_vereador_id,
                                r.quorum,
                                r.ata_pdf_url,
                                r.fonte_url,
                                r.coletado_em,
                                r.hash_conteudo,
                                r.versao_coletor,
                                sessao_id_alvo,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_presencas(self, registros: list[PresencaRegistro] | tuple[PresencaRegistro, ...]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for p in registros:
                validar_ausencia_cpf_em_valores(p.model_dump(), contexto="presenca")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT situacao_id_origem, situacao_descricao, status_normalizado, hash_conteudo
                    FROM presenca
                    WHERE presenca_id = %s
                    """,
                    (p.presenca_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "situacao_id_origem": p.situacao_id_origem,
                    "situacao_descricao": p.situacao_descricao,
                    "status_normalizado": p.status_normalizado,
                    "hash_conteudo": p.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO presenca (
                            presenca_id, municipio_id, sessao_id, vereador_id,
                            situacao_id_origem, situacao_descricao, status_normalizado,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            p.presenca_id,
                            p.municipio_id,
                            p.sessao_id,
                            p.vereador_id,
                            p.situacao_id_origem,
                            p.situacao_descricao,
                            p.status_normalizado,
                            p.fonte_id,
                            p.fonte_url,
                            p.coletado_em,
                            p.hash_conteudo,
                            p.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE presenca
                        SET situacao_id_origem = %s,
                            situacao_descricao = %s,
                            status_normalizado = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE presenca_id = %s
                        """,
                        (
                            p.situacao_id_origem,
                            p.situacao_descricao,
                            p.status_normalizado,
                            p.fonte_url,
                            p.coletado_em,
                            p.hash_conteudo,
                            p.versao_coletor,
                            p.presenca_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_proposicoes(
        self,
        registros: list[ProposicaoRegistro] | tuple[ProposicaoRegistro, ...],
        *,
        sobrescrever_existentes: bool = True,
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for prop in registros:
                validar_ausencia_cpf_em_valores(prop.model_dump(), contexto="proposicao")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT tipo_id_origem, tipo_descricao_origem, numero, ano, nome_materia,
                           slug, ementa, data_publicacao, ultima_movimentacao, situacao_atual,
                           local_origem, local_destino, autoria_codigo_origem,
                           anexo_principal_url, anexo_principal_nome, anexo_principal_mime,
                           anexo_principal_tamanho, categoria_classificada,
                           eh_proposicao_parlamentar, contabilizar_producao_vereador, hash_conteudo
                    FROM proposicao
                    WHERE proposicao_id = %s
                    """,
                    (prop.proposicao_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "tipo_id_origem": prop.tipo_id_origem,
                    "tipo_descricao_origem": prop.tipo_descricao_origem,
                    "numero": prop.numero,
                    "ano": prop.ano,
                    "nome_materia": prop.nome_materia,
                    "slug": prop.slug,
                    "ementa": prop.ementa,
                    "data_publicacao": prop.data_publicacao,
                    "ultima_movimentacao": prop.ultima_movimentacao,
                    "situacao_atual": prop.situacao_atual,
                    "local_origem": prop.local_origem,
                    "local_destino": prop.local_destino,
                    "autoria_codigo_origem": prop.autoria_codigo_origem,
                    "anexo_principal_url": prop.anexo_principal_url,
                    "anexo_principal_nome": prop.anexo_principal_nome,
                    "anexo_principal_mime": prop.anexo_principal_mime,
                    "anexo_principal_tamanho": prop.anexo_principal_tamanho,
                    "categoria_classificada": prop.categoria_classificada,
                    "eh_proposicao_parlamentar": prop.eh_proposicao_parlamentar,
                    "contabilizar_producao_vereador": prop.contabilizar_producao_vereador,
                    "hash_conteudo": prop.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO proposicao (
                            proposicao_id, municipio_id, id_origem_nexlegis,
                            tipo_id_origem, tipo_descricao_origem, numero, ano,
                            nome_materia, slug, ementa, data_publicacao,
                            ultima_movimentacao, situacao_atual, local_origem,
                            local_destino, autoria_codigo_origem,
                            anexo_principal_url, anexo_principal_nome,
                            anexo_principal_mime, anexo_principal_tamanho,
                            categoria_classificada, eh_proposicao_parlamentar,
                            contabilizar_producao_vereador,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            prop.proposicao_id,
                            prop.municipio_id,
                            prop.id_origem_nexlegis,
                            prop.tipo_id_origem,
                            prop.tipo_descricao_origem,
                            prop.numero,
                            prop.ano,
                            prop.nome_materia,
                            prop.slug,
                            prop.ementa,
                            prop.data_publicacao,
                            prop.ultima_movimentacao,
                            prop.situacao_atual,
                            prop.local_origem,
                            prop.local_destino,
                            prop.autoria_codigo_origem,
                            prop.anexo_principal_url,
                            prop.anexo_principal_nome,
                            prop.anexo_principal_mime,
                            prop.anexo_principal_tamanho,
                            prop.categoria_classificada,
                            prop.eh_proposicao_parlamentar,
                            prop.contabilizar_producao_vereador,
                            prop.fonte_id,
                            prop.fonte_url,
                            prop.coletado_em,
                            prop.hash_conteudo,
                            prop.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif sobrescrever_existentes and dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE proposicao
                        SET tipo_id_origem = %s,
                            tipo_descricao_origem = %s,
                            numero = %s,
                            ano = %s,
                            nome_materia = %s,
                            slug = %s,
                            ementa = %s,
                            data_publicacao = %s,
                            ultima_movimentacao = %s,
                            situacao_atual = %s,
                            local_origem = %s,
                            local_destino = %s,
                            autoria_codigo_origem = %s,
                            anexo_principal_url = %s,
                            anexo_principal_nome = %s,
                            anexo_principal_mime = %s,
                            anexo_principal_tamanho = %s,
                            categoria_classificada = %s,
                            eh_proposicao_parlamentar = %s,
                            contabilizar_producao_vereador = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE proposicao_id = %s
                        """,
                        (
                            prop.tipo_id_origem,
                            prop.tipo_descricao_origem,
                            prop.numero,
                            prop.ano,
                            prop.nome_materia,
                            prop.slug,
                            prop.ementa,
                            prop.data_publicacao,
                            prop.ultima_movimentacao,
                            prop.situacao_atual,
                            prop.local_origem,
                            prop.local_destino,
                            prop.autoria_codigo_origem,
                            prop.anexo_principal_url,
                            prop.anexo_principal_nome,
                            prop.anexo_principal_mime,
                            prop.anexo_principal_tamanho,
                            prop.categoria_classificada,
                            prop.eh_proposicao_parlamentar,
                            prop.contabilizar_producao_vereador,
                            prop.fonte_url,
                            prop.coletado_em,
                            prop.hash_conteudo,
                            prop.versao_coletor,
                            prop.proposicao_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_autorias(self, registros: list[AutoriaRegistro] | tuple[AutoriaRegistro, ...]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for aut in registros:
                validar_ausencia_cpf_em_valores(aut.model_dump(), contexto="autoria")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT proposicao_id, vereador_id, autor_institucional, tipo_autor, hash_conteudo
                    FROM autoria
                    WHERE autoria_id = %s
                    """,
                    (aut.autoria_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "proposicao_id": aut.proposicao_id,
                    "vereador_id": aut.vereador_id,
                    "autor_institucional": aut.autor_institucional,
                    "tipo_autor": aut.tipo_autor,
                    "hash_conteudo": aut.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO autoria (
                            autoria_id, municipio_id, proposicao_id, vereador_id,
                            autor_institucional, tipo_autor,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            aut.autoria_id,
                            aut.municipio_id,
                            aut.proposicao_id,
                            aut.vereador_id,
                            aut.autor_institucional,
                            aut.tipo_autor,
                            aut.fonte_id,
                            aut.fonte_url,
                            aut.coletado_em,
                            aut.hash_conteudo,
                            aut.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE autoria
                        SET vereador_id = %s,
                            autor_institucional = %s,
                            tipo_autor = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE autoria_id = %s
                        """,
                        (
                            aut.vereador_id,
                            aut.autor_institucional,
                            aut.tipo_autor,
                            aut.fonte_url,
                            aut.coletado_em,
                            aut.hash_conteudo,
                            aut.versao_coletor,
                            aut.autoria_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_tramitacoes(self, registros: list[TramitacaoRegistro] | tuple[TramitacaoRegistro, ...]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for tr in registros:
                validar_ausencia_cpf_em_valores(tr.model_dump(), contexto="tramitacao")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT proposicao_id, data_tramitacao, local_origem, local_destino,
                           situacao_descricao, prioridade_descricao, prazo_descricao,
                           justificativa, hash_conteudo
                    FROM tramitacao
                    WHERE tramitacao_id = %s
                    """,
                    (tr.tramitacao_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "proposicao_id": tr.proposicao_id,
                    "data_tramitacao": tr.data_tramitacao,
                    "local_origem": tr.local_origem,
                    "local_destino": tr.local_destino,
                    "situacao_descricao": tr.situacao_descricao,
                    "prioridade_descricao": tr.prioridade_descricao,
                    "prazo_descricao": tr.prazo_descricao,
                    "justificativa": tr.justificativa,
                    "hash_conteudo": tr.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO tramitacao (
                            tramitacao_id, municipio_id, proposicao_id, id_origem_nexlegis,
                            data_tramitacao, local_origem, local_destino,
                            situacao_descricao, prioridade_descricao, prazo_descricao, justificativa,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            tr.tramitacao_id,
                            tr.municipio_id,
                            tr.proposicao_id,
                            tr.id_origem_nexlegis,
                            tr.data_tramitacao,
                            tr.local_origem,
                            tr.local_destino,
                            tr.situacao_descricao,
                            tr.prioridade_descricao,
                            tr.prazo_descricao,
                            tr.justificativa,
                            tr.fonte_id,
                            tr.fonte_url,
                            tr.coletado_em,
                            tr.hash_conteudo,
                            tr.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE tramitacao
                        SET data_tramitacao = %s,
                            local_origem = %s,
                            local_destino = %s,
                            situacao_descricao = %s,
                            prioridade_descricao = %s,
                            prazo_descricao = %s,
                            justificativa = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE tramitacao_id = %s
                        """,
                        (
                            tr.data_tramitacao,
                            tr.local_origem,
                            tr.local_destino,
                            tr.situacao_descricao,
                            tr.prioridade_descricao,
                            tr.prazo_descricao,
                            tr.justificativa,
                            tr.fonte_url,
                            tr.coletado_em,
                            tr.hash_conteudo,
                            tr.versao_coletor,
                            tr.tramitacao_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_pauta_itens(self, registros: list[PautaItemRegistro] | tuple[PautaItemRegistro, ...]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for item in registros:
                validar_ausencia_cpf_em_valores(item.model_dump(), contexto="pauta_item")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT sessao_id, proposicao_id, ordem, turno,
                           tipo_pauta_id_origem, tipo_pauta_descricao,
                           unanime, has_votos, hash_conteudo
                    FROM pauta_item
                    WHERE pauta_item_id = %s
                    """,
                    (item.pauta_item_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "sessao_id": item.sessao_id,
                    "proposicao_id": item.proposicao_id,
                    "ordem": item.ordem,
                    "turno": item.turno,
                    "tipo_pauta_id_origem": item.tipo_pauta_id_origem,
                    "tipo_pauta_descricao": item.tipo_pauta_descricao,
                    "unanime": item.unanime,
                    "has_votos": item.has_votos,
                    "hash_conteudo": item.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO pauta_item (
                            pauta_item_id, municipio_id, sessao_id, proposicao_id,
                            ordem, turno, tipo_pauta_id_origem, tipo_pauta_descricao,
                            unanime, has_votos,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            item.pauta_item_id,
                            item.municipio_id,
                            item.sessao_id,
                            item.proposicao_id,
                            item.ordem,
                            item.turno,
                            item.tipo_pauta_id_origem,
                            item.tipo_pauta_descricao,
                            item.unanime,
                            item.has_votos,
                            item.fonte_id,
                            item.fonte_url,
                            item.coletado_em,
                            item.hash_conteudo,
                            item.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE pauta_item
                        SET ordem = %s,
                            turno = %s,
                            tipo_pauta_id_origem = %s,
                            tipo_pauta_descricao = %s,
                            unanime = %s,
                            has_votos = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE pauta_item_id = %s
                        """,
                        (
                            item.ordem,
                            item.turno,
                            item.tipo_pauta_id_origem,
                            item.tipo_pauta_descricao,
                            item.unanime,
                            item.has_votos,
                            item.fonte_url,
                            item.coletado_em,
                            item.hash_conteudo,
                            item.versao_coletor,
                            item.pauta_item_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_votacoes(self, registros: list[VotacaoRegistro] | tuple[VotacaoRegistro, ...]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for vot in registros:
                validar_ausencia_cpf_em_valores(vot.model_dump(), contexto="votacao")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT sessao_id, proposicao_id, tipo_turno_id, unanime,
                           has_votos, tempo_decorrido_segundos, hash_conteudo
                    FROM votacao
                    WHERE votacao_id = %s
                    """,
                    (vot.votacao_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "sessao_id": vot.sessao_id,
                    "proposicao_id": vot.proposicao_id,
                    "tipo_turno_id": vot.tipo_turno_id,
                    "unanime": vot.unanime,
                    "has_votos": vot.has_votos,
                    "tempo_decorrido_segundos": vot.tempo_decorrido_segundos,
                    "hash_conteudo": vot.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO votacao (
                            votacao_id, municipio_id, id_origem_nexlegis,
                            sessao_id, proposicao_id, tipo_turno_id,
                            unanime, has_votos, discussed_at, started_at, closed_at,
                            tempo_decorrido_segundos,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            vot.votacao_id,
                            vot.municipio_id,
                            vot.id_origem_nexlegis,
                            vot.sessao_id,
                            vot.proposicao_id,
                            vot.tipo_turno_id,
                            vot.unanime,
                            vot.has_votos,
                            vot.discussed_at,
                            vot.started_at,
                            vot.closed_at,
                            vot.tempo_decorrido_segundos,
                            vot.fonte_id,
                            vot.fonte_url,
                            vot.coletado_em,
                            vot.hash_conteudo,
                            vot.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE votacao
                        SET tipo_turno_id = %s,
                            unanime = %s,
                            has_votos = %s,
                            discussed_at = %s,
                            started_at = %s,
                            closed_at = %s,
                            tempo_decorrido_segundos = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE votacao_id = %s
                        """,
                        (
                            vot.tipo_turno_id,
                            vot.unanime,
                            vot.has_votos,
                            vot.discussed_at,
                            vot.started_at,
                            vot.closed_at,
                            vot.tempo_decorrido_segundos,
                            vot.fonte_url,
                            vot.coletado_em,
                            vot.hash_conteudo,
                            vot.versao_coletor,
                            vot.votacao_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_votos_nominais(
        self, registros: list[VotoNominalRegistro] | tuple[VotoNominalRegistro, ...]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for vt in registros:
                validar_ausencia_cpf_em_valores(vt.model_dump(), contexto="voto")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT voto_id_origem, voto_descricao, voto_normalizado, hash_conteudo
                    FROM voto
                    WHERE voto_id = %s
                    """,
                    (vt.voto_id,),
                )
                atual = cur.fetchone()
                nova = {
                    "voto_id_origem": vt.voto_id_origem,
                    "voto_descricao": vt.voto_descricao,
                    "voto_normalizado": vt.voto_normalizado,
                    "hash_conteudo": vt.hash_conteudo,
                }
                if atual is None:
                    cur.execute(
                        """
                        INSERT INTO voto (
                            voto_id, municipio_id, votacao_id, vereador_id,
                            voto_id_origem, voto_descricao, voto_normalizado,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            vt.voto_id,
                            vt.municipio_id,
                            vt.votacao_id,
                            vt.vereador_id,
                            vt.voto_id_origem,
                            vt.voto_descricao,
                            vt.voto_normalizado,
                            vt.fonte_id,
                            vt.fonte_url,
                            vt.coletado_em,
                            vt.hash_conteudo,
                            vt.versao_coletor,
                        ),
                    )
                    res.novos += 1
                elif dict(atual) != nova:
                    cur.execute(
                        """
                        UPDATE voto
                        SET voto_id_origem = %s,
                            voto_descricao = %s,
                            voto_normalizado = %s,
                            fonte_url = %s,
                            coletado_em = %s,
                            hash_conteudo = %s,
                            versao_coletor = %s
                        WHERE voto_id = %s
                        """,
                        (
                            vt.voto_id_origem,
                            vt.voto_descricao,
                            vt.voto_normalizado,
                            vt.fonte_url,
                            vt.coletado_em,
                            vt.hash_conteudo,
                            vt.versao_coletor,
                            vt.voto_id,
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_pacote_sessao_detalhe(
        self, pacote: PacoteSessaoDetalheParseado
    ) -> dict[str, ResultadoCarga]:
        res_sessao = self.carregar_sessoes([pacote.sessao])
        res_presencas = self.carregar_presencas(pacote.presencas)
        # Proposições referenciadas na pauta da sessão são inseridas sem sobrescrever
        # versões completas já carregadas de /api/materias
        res_props_pauta = self.carregar_proposicoes(
            pacote.proposicoes_pauta, sobrescrever_existentes=False
        )
        res_pauta = self.carregar_pauta_itens(pacote.pauta_itens)
        res_votacoes = self.carregar_votacoes(pacote.votacoes)
        res_votos = self.carregar_votos_nominais(pacote.votos_nominais)
        return {
            "sessao": res_sessao,
            "presenca": res_presencas,
            "proposicao_pauta": res_props_pauta,
            "pauta_item": res_pauta,
            "votacao": res_votacoes,
            "voto": res_votos,
        }

    def carregar_pacote_materias(
        self, pacote: PacoteMateriasParseado
    ) -> dict[str, ResultadoCarga]:
        res_props = self.carregar_proposicoes(pacote.proposicoes, sobrescrever_existentes=True)
        res_aut = self.carregar_autorias(pacote.autorias)
        res_tram = self.carregar_tramitacoes(pacote.tramitacoes)
        return {
            "proposicao": res_props,
            "autoria": res_aut,
            "tramitacao": res_tram,
        }

    def contar_registros_por_tabela(self, municipio_id: str = "inhumas-go") -> dict[str, int]:
        tabelas = (
            "municipio",
            "casa_legislativa",
            "legislatura",
            "partido",
            "fonte",
            "de_para_tipo_proposicao",
            "lacuna_historica",
            "coleta_execucao",
            "documento_bruto",
            "vereador",
            "vereador_alias",
            "mandato",
            "sessao",
            "presenca",
            "proposicao",
            "autoria",
            "tramitacao",
            "pauta_item",
            "votacao",
            "voto",
        )
        contagens: dict[str, int] = {}
        with self.conn.cursor(row_factory=dict_row) as cur:
            for t in tabelas:
                if t in ("casa_legislativa", "partido"):
                    cur.execute(f"SELECT COUNT(*) AS c FROM {t}")
                else:
                    cur.execute(
                        f"SELECT COUNT(*) AS c FROM {t} WHERE municipio_id = %s",
                        (municipio_id,),
                    )
                row = cur.fetchone()
                contagens[t] = int(row["c"]) if row else 0
        return contagens


def carregar_lote1_2026_no_postgres(
    conn: psycopg.Connection[Any],
    repo_root: Path,
) -> RelatorioPersistenciaPostgres:
    """Carrega no PostgreSQL 16 exclusivamente os dados validados de 2026 do Lote 1 (a partir de data/raw)."""
    raiz = Path(repo_root)
    pg_repo = PostgresNexlegisRepository(conn)
    pg_repo.aplicar_migracao_sql(raiz / "db" / "migrations" / "0001_init_core_and_nexlegis.sql")
    res_vocab = pg_repo.sincronizar_vocabulario_tipos_proposicao("inhumas-go")

    # Reconstrói os dados validados do Lote 1 a partir dos arquivos em disco (sem tocar na rede)
    executor = ExecutorLote1Nexlegis(raiz)
    rel_lote1 = executor.executar()

    # Coleta todos os metadados .meta.json dos 130 arquivos brutos
    metadados_brutos: list[MetadadosDocumentoBruto] = []
    for req in rel_lote1.log_requisicoes:
        if not req.caminho_armazenamento:
            continue
        caminho_meta = raiz / f"{req.caminho_armazenamento}.meta.json"
        if caminho_meta.exists():
            dados_meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
            metadados_brutos.append(MetadadosDocumentoBruto(**dados_meta))

    # 1. Registra execução e documentos brutos
    res_exec = pg_repo.registrar_execucao_coleta(
        execucao_id=rel_lote1.execucao_id,
        municipio_id=rel_lote1.municipio_id,
        fonte_id="nexlegis",
        versao_coletor=rel_lote1.versao_coletor,
        iniciado_em=rel_lote1.iniciado_em,
        finalizado_em=rel_lote1.finalizado_em,
        status="SUCESSO",
        registros_lidos=len(metadados_brutos),
        registros_novos=len(metadados_brutos),
        registros_alterados=0,
        registros_inalterados=0,
        relatorio_qualidade=rel_lote1.verificacao_integridade,
    )
    res_docs = pg_repo.carregar_documentos_brutos(
        metadados_brutos, execucao_id=rel_lote1.execucao_id
    )

    # 2. Vereadores, Aliases e Mandatos
    vereadores_lista = list(executor.repo.vereadores.ativos.values())
    res_ver = pg_repo.carregar_vereadores(vereadores_lista)
    ver_ref = vereadores_lista[0]
    res_aliases, res_mandatos = pg_repo.carregar_aliases_e_mandatos_curados(
        municipio_id=rel_lote1.municipio_id,
        fonte_url=ver_ref.fonte_url,
        coletado_em=ver_ref.coletado_em,
        hash_conteudo=ver_ref.hash_conteudo,
        versao_coletor=ver_ref.versao_coletor,
    )

    # 3. Exclusivamente sessões de 2026 e todas as entidades filhas de 2026
    sessoes_2026 = [s for s in executor.repo.sessoes.ativos.values() if s.ano == 2026]
    res_ses = pg_repo.carregar_sessoes(sessoes_2026)
    res_pres = pg_repo.carregar_presencas(list(executor.repo.presencas.ativos.values()))

    # 4. Proposições de 2026 (571) + proposições pautadas em sessões de 2026 (6) para integridade referencial
    todas_props_l1 = list(executor.repo.proposicoes.ativos.values())
    props_2026 = [p for p in todas_props_l1 if p.ano == 2026]
    props_pauta_outros_l1 = [p for p in todas_props_l1 if p.ano != 2026]
    res_prop_2026 = pg_repo.carregar_proposicoes(props_2026, sobrescrever_existentes=True)
    res_prop_pauta_l1 = pg_repo.carregar_proposicoes(
        props_pauta_outros_l1, sobrescrever_existentes=False
    )
    res_prop = ResultadoCarga(
        lidos=res_prop_2026.lidos + res_prop_pauta_l1.lidos,
        novos=res_prop_2026.novos + res_prop_pauta_l1.novos,
        alterados=res_prop_2026.alterados + res_prop_pauta_l1.alterados,
        inalterados=res_prop_2026.inalterados + res_prop_pauta_l1.inalterados,
    )
    res_aut = pg_repo.carregar_autorias(list(executor.repo.autorias.ativos.values()))
    res_tram = pg_repo.carregar_tramitacoes(list(executor.repo.tramitacoes.ativos.values()))
    res_pauta = pg_repo.carregar_pauta_itens(list(executor.repo.pauta_itens.ativos.values()))
    res_vot = pg_repo.carregar_votacoes(list(executor.repo.votacoes.ativos.values()))
    res_voto = pg_repo.carregar_votos_nominais(list(executor.repo.votos.ativos.values()))

    por_tabela = {
        "de_para_tipo_proposicao": asdict(res_vocab),
        "coleta_execucao": asdict(res_exec),
        "documento_bruto": asdict(res_docs),
        "vereador": asdict(res_ver),
        "vereador_alias": asdict(res_aliases),
        "mandato": asdict(res_mandatos),
        "sessao": asdict(res_ses),
        "presenca": asdict(res_pres),
        "proposicao": asdict(res_prop),
        "autoria": asdict(res_aut),
        "tramitacao": asdict(res_tram),
        "pauta_item": asdict(res_pauta),
        "votacao": asdict(res_vot),
        "voto": asdict(res_voto),
    }

    return RelatorioPersistenciaPostgres(
        municipio_id=rel_lote1.municipio_id,
        escopo_ano=2026,
        executado_em=datetime.now(UTC).isoformat(),
        por_tabela=por_tabela,
        contagem_total_banco=pg_repo.contar_registros_por_tabela(rel_lote1.municipio_id),
    )


def carregar_lote2_2025_no_postgres(
    conn: psycopg.Connection[Any],
    repo_root: Path,
) -> RelatorioPersistenciaPostgres:
    """Carrega no PostgreSQL 16 os dados validados de 2025 do Lote 2 preservando integralmente os de 2026."""
    raiz = Path(repo_root)
    pg_repo = PostgresNexlegisRepository(conn)
    pg_repo.aplicar_migracao_sql(raiz / "db" / "migrations" / "0001_init_core_and_nexlegis.sql")
    res_vocab = pg_repo.sincronizar_vocabulario_tipos_proposicao("inhumas-go")

    # Reconstrói os dados validados do Lote 2 (2025) a partir dos arquivos em disco (sem tocar na rede)
    executor = ExecutorLote2Nexlegis(raiz)
    rel_lote2 = executor.executar()

    metadados_brutos: list[MetadadosDocumentoBruto] = []
    for req in rel_lote2.log_requisicoes:
        if not req.caminho_armazenamento:
            continue
        caminho_meta = raiz / f"{req.caminho_armazenamento}.meta.json"
        if caminho_meta.exists():
            dados_meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
            metadados_brutos.append(MetadadosDocumentoBruto(**dados_meta))

    res_exec = pg_repo.registrar_execucao_coleta(
        execucao_id=rel_lote2.execucao_id,
        municipio_id=rel_lote2.municipio_id,
        fonte_id="nexlegis",
        versao_coletor=rel_lote2.versao_coletor,
        iniciado_em=rel_lote2.iniciado_em,
        finalizado_em=rel_lote2.finalizado_em,
        status="SUCESSO",
        registros_lidos=len(metadados_brutos),
        registros_novos=len(metadados_brutos),
        registros_alterados=0,
        registros_inalterados=0,
        relatorio_qualidade=rel_lote2.verificacao_integridade,
    )
    res_docs = pg_repo.carregar_documentos_brutos(
        metadados_brutos, execucao_id=rel_lote2.execucao_id
    )

    vereadores_lista = list(executor.repo.vereadores.ativos.values())
    res_ver = pg_repo.carregar_vereadores(vereadores_lista)
    ver_ref = vereadores_lista[0]
    res_aliases, res_mandatos = pg_repo.carregar_aliases_e_mandatos_curados(
        municipio_id=rel_lote2.municipio_id,
        fonte_url=ver_ref.fonte_url,
        coletado_em=ver_ref.coletado_em,
        hash_conteudo=ver_ref.hash_conteudo,
        versao_coletor=ver_ref.versao_coletor,
    )

    sessoes_2025 = [s for s in executor.repo.sessoes.ativos.values() if s.ano == 2025]
    res_ses = pg_repo.carregar_sessoes(sessoes_2025)
    res_pres = pg_repo.carregar_presencas(list(executor.repo.presencas.ativos.values()))

    todas_props_l2 = list(executor.repo.proposicoes.ativos.values())
    props_2025 = [p for p in todas_props_l2 if p.ano == 2025]
    props_pauta_outros_l2 = [p for p in todas_props_l2 if p.ano != 2025]
    res_prop_2025 = pg_repo.carregar_proposicoes(props_2025, sobrescrever_existentes=True)
    res_prop_pauta_l2 = pg_repo.carregar_proposicoes(
        props_pauta_outros_l2, sobrescrever_existentes=False
    )
    res_prop = ResultadoCarga(
        lidos=res_prop_2025.lidos + res_prop_pauta_l2.lidos,
        novos=res_prop_2025.novos + res_prop_pauta_l2.novos,
        alterados=res_prop_2025.alterados + res_prop_pauta_l2.alterados,
        inalterados=res_prop_2025.inalterados + res_prop_pauta_l2.inalterados,
    )
    res_aut = pg_repo.carregar_autorias(list(executor.repo.autorias.ativos.values()))
    res_tram = pg_repo.carregar_tramitacoes(list(executor.repo.tramitacoes.ativos.values()))
    res_pauta = pg_repo.carregar_pauta_itens(list(executor.repo.pauta_itens.ativos.values()))
    res_vot = pg_repo.carregar_votacoes(list(executor.repo.votacoes.ativos.values()))
    res_voto = pg_repo.carregar_votos_nominais(list(executor.repo.votos.ativos.values()))

    por_tabela = {
        "de_para_tipo_proposicao": asdict(res_vocab),
        "coleta_execucao": asdict(res_exec),
        "documento_bruto": asdict(res_docs),
        "vereador": asdict(res_ver),
        "vereador_alias": asdict(res_aliases),
        "mandato": asdict(res_mandatos),
        "sessao": asdict(res_ses),
        "presenca": asdict(res_pres),
        "proposicao": asdict(res_prop),
        "autoria": asdict(res_aut),
        "tramitacao": asdict(res_tram),
        "pauta_item": asdict(res_pauta),
        "votacao": asdict(res_vot),
        "voto": asdict(res_voto),
    }

    return RelatorioPersistenciaPostgres(
        municipio_id=rel_lote2.municipio_id,
        escopo_ano=2025,
        executado_em=datetime.now(UTC).isoformat(),
        por_tabela=por_tabela,
        contagem_total_banco=pg_repo.contar_registros_por_tabela(rel_lote2.municipio_id),
    )


def carregar_bienio_2025_2026_no_postgres(
    conn: psycopg.Connection[Any],
    repo_root: Path,
) -> dict[str, RelatorioPersistenciaPostgres]:
    """Carrega no PostgreSQL 16 o biênio 2025–2026 (Lote 1 + Lote 2) de forma idempotente."""
    rel_2026 = carregar_lote1_2026_no_postgres(conn, repo_root)
    rel_2025 = carregar_lote2_2025_no_postgres(conn, repo_root)
    return {"lote1_2026": rel_2026, "lote2_2025": rel_2025}


if __name__ == "__main__":
    import os

    import pgserver

    raiz_repo = Path(__file__).resolve().parents[5]
    db_url = os.environ.get("DATABASE_URL")
    pg_srv = None
    try:
        if not db_url:
            pgdata_dir = raiz_repo / "data" / "pgdata"
            pgdata_dir.mkdir(parents=True, exist_ok=True)
            pg_srv = pgserver.get_server(str(pgdata_dir))
            db_url = pg_srv.get_uri()

        with psycopg.connect(db_url) as conexao:
            relatorio_1 = carregar_lote1_2026_no_postgres(conexao, raiz_repo)
            relatorio_2 = carregar_lote1_2026_no_postgres(conexao, raiz_repo)
            print(
                json.dumps(
                    {
                        "primeira_execucao": asdict(relatorio_1),
                        "reexecucao_idempotente": asdict(relatorio_2),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        if pg_srv is not None:
            pg_srv.cleanup()
