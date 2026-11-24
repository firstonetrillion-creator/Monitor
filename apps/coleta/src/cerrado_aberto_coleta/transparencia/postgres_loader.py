"""Persistência PostgreSQL 16 idempotente para o Portal da Transparência CENTI/NúcleoGov e Custo da Estrutura do Mandato (Fase 2)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from cerrado_aberto_coleta.entidades import VEREADORES_MESTRE_INHUMAS
from cerrado_aberto_coleta.nexlegis.loader import ResultadoCarga
from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    RelatorioPersistenciaPostgres,
    validar_ausencia_cpf_em_valores,
)
from cerrado_aberto_coleta.normalizacao import gerar_chave_busca
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto
from cerrado_aberto_coleta.transparencia.lote_2026 import (
    ExecutorLoteTransparencia2026,
    PacoteLoteTransparencia2026,
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


class PostgresTransparenciaRepository:
    """Repositório PostgreSQL 16 idempotente para entidades financeiras/administrativas e Custo da Estrutura do Mandato."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self.conn = conn

    def aplicar_migracao_sql(self, caminho_sql: Path) -> None:
        sql = Path(caminho_sql).read_text(encoding="utf-8")
        with self.conn.cursor() as cur:
            cur.execute(sql)
        self.conn.commit()

    def sincronizar_nomes_civis_e_aliases_curados(
        self, municipio_id: str = "inhumas-go"
    ) -> ResultadoCarga:
        """Sincroniza nomes civis enriquecidos pela folha oficial e aliases de lotação em `vereador` e `vereador_alias`."""
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for seed in VEREADORES_MESTRE_INHUMAS:
                if seed.nome_civil:
                    cur.execute(
                        "SELECT nome_civil FROM vereador WHERE municipio_id = %s AND vereador_id = %s",
                        (municipio_id, seed.vereador_id),
                    )
                    ver_row = cur.fetchone()
                    if ver_row is not None and ver_row["nome_civil"] != seed.nome_civil:
                        cur.execute(
                            "UPDATE vereador SET nome_civil = %s WHERE municipio_id = %s AND vereador_id = %s",
                            (seed.nome_civil, municipio_id, seed.vereador_id),
                        )
                        res.alterados += 1

                for alias_texto in seed.aliases:
                    chave = gerar_chave_busca(alias_texto, remover_titulos=False)
                    if not chave:
                        continue
                    if alias_texto.upper().startswith("GAB"):
                        tipo_alias = "LOTACAO_GABINETE"
                        fonte_origem = "transparencia_centi"
                    elif seed.nome_civil and alias_texto.lower() == seed.nome_civil.lower():
                        tipo_alias = "NOME_CIVIL"
                        fonte_origem = "transparencia_centi"
                    else:
                        tipo_alias = "VARIACAO_GRAFIA"
                        fonte_origem = "curadoria_transparencia_2026"

                    res.lidos += 1
                    cur.execute(
                        """
                        SELECT alias_id FROM vereador_alias
                        WHERE municipio_id = %s AND alias_chave_busca = %s AND tipo_alias = %s
                        """,
                        (municipio_id, chave, tipo_alias),
                    )
                    if cur.fetchone() is None:
                        cur.execute(
                            """
                            INSERT INTO vereador_alias (
                                municipio_id, vereador_id, alias_texto, alias_chave_busca,
                                tipo_alias, fonte_origem, confianca, curado_por
                            ) VALUES (%s, %s, %s, %s, %s, %s, 'ALTA', 'curadoria_fase_2_centi')
                            """,
                            (
                                municipio_id,
                                seed.vereador_id,
                                alias_texto,
                                chave,
                                tipo_alias,
                                fonte_origem,
                            ),
                        )
                        res.novos += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_documentos_brutos(
        self, documentos: list[MetadadosDocumentoBruto]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for doc in documentos:
                validar_ausencia_cpf_em_valores(asdict(doc), contexto="documento_bruto")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT documento_id, tamanho_bytes, caminho_armazenamento
                    FROM documento_bruto
                    WHERE municipio_id = %s AND fonte_id = %s AND hash_conteudo = %s AND fonte_url = %s
                    """,
                    (doc.municipio_id, doc.fonte_id, doc.hash_conteudo, doc.fonte_url),
                )
                existente = cur.fetchone()
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO documento_bruto (
                            documento_id, municipio_id, fonte_id, fonte_url, coletado_em,
                            hash_conteudo, versao_coletor, storage_backend, caminho_armazenamento,
                            mime_type, tamanho_bytes, status_http, url_temporaria
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            doc.documento_id,
                            doc.municipio_id,
                            doc.fonte_id,
                            doc.fonte_url,
                            doc.coletado_em,
                            doc.hash_conteudo,
                            doc.versao_coletor,
                            doc.storage_backend,
                            doc.caminho_armazenamento,
                            doc.mime_type,
                            doc.tamanho_bytes,
                            doc.status_http,
                            doc.url_temporaria,
                        ),
                    )
                    res.novos += 1
                elif (
                    int(existente["tamanho_bytes"]) != doc.tamanho_bytes
                    or existente["caminho_armazenamento"] != doc.caminho_armazenamento
                ):
                    cur.execute(
                        """
                        UPDATE documento_bruto
                        SET tamanho_bytes = %s, caminho_armazenamento = %s, versao_coletor = %s
                        WHERE documento_id = %s
                        """,
                        (
                            doc.tamanho_bytes,
                            doc.caminho_armazenamento,
                            doc.versao_coletor,
                            existente["documento_id"],
                        ),
                    )
                    res.alterados += 1
                else:
                    res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_fornecedores(self, fornecedores: list[FornecedorRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for f in fornecedores:
                validar_ausencia_cpf_em_valores(asdict(f), contexto="fornecedor")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT nome, documento_mascarado_ou_cnpj, tipo_pessoa, cnpj_valido, hash_conteudo
                    FROM fornecedor
                    WHERE fornecedor_id = %s
                    """,
                    (f.fornecedor_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "nome": f.nome,
                    "documento_mascarado_ou_cnpj": f.documento_mascarado_ou_cnpj,
                    "tipo_pessoa": f.tipo_pessoa,
                    "cnpj_valido": f.cnpj_valido,
                    "hash_conteudo": f.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO fornecedor (
                            fornecedor_id, municipio_id, nome, chave_busca,
                            documento_mascarado_ou_cnpj, tipo_pessoa, cnpj_valido,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            f.fornecedor_id,
                            f.municipio_id,
                            f.nome,
                            f.chave_busca,
                            f.documento_mascarado_ou_cnpj,
                            f.tipo_pessoa,
                            f.cnpj_valido,
                            f.fonte_id,
                            f.fonte_url,
                            f.coletado_em,
                            f.hash_conteudo,
                            f.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE fornecedor
                            SET nome = %s, documento_mascarado_ou_cnpj = %s, tipo_pessoa = %s,
                                cnpj_valido = %s, hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE fornecedor_id = %s
                            """,
                            (
                                f.nome,
                                f.documento_mascarado_ou_cnpj,
                                f.tipo_pessoa,
                                f.cnpj_valido,
                                f.hash_conteudo,
                                f.coletado_em,
                                f.versao_coletor,
                                f.fornecedor_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_folha_pagamento(
        self, registros: list[FolhaPagamentoRegistro]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(asdict(r), contexto="folha_pagamento")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT nome_servidor, cargo, lotacao, salario_base, remuneracao_bruta,
                           descontos, remuneracao_liquida, vereador_id, gabinete_vereador_id, hash_conteudo
                    FROM folha_pagamento
                    WHERE folha_id = %s
                    """,
                    (r.folha_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "nome_servidor": r.nome_servidor,
                    "cargo": r.cargo,
                    "lotacao": r.lotacao,
                    "salario_base": r.salario_base,
                    "remuneracao_bruta": r.remuneracao_bruta,
                    "descontos": r.descontos,
                    "remuneracao_liquida": r.remuneracao_liquida,
                    "vereador_id": r.vereador_id,
                    "gabinete_vereador_id": r.gabinete_vereador_id,
                    "hash_conteudo": r.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO folha_pagamento (
                            folha_id, municipio_id, ano, mes, referencia, matricula,
                            nome_servidor, cpf_mascarado, situacao, orgao, cargo, funcao,
                            lotacao, local_trabalho, decreto_nomeacao, possui_estabilidade,
                            data_admissao, data_exoneracao, tipo_admissao, carga_horaria,
                            tipo_folha, movimentacao, salario_base, remuneracao_bruta,
                            descontos, remuneracao_liquida, eh_vereador, vereador_id,
                            gabinete_vereador_id, fonte_id, fonte_url, coletado_em,
                            hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s
                        )
                        """,
                        (
                            r.folha_id,
                            r.municipio_id,
                            r.ano,
                            r.mes,
                            r.referencia,
                            r.matricula,
                            r.nome_servidor,
                            r.cpf_mascarado,
                            r.situacao,
                            r.orgao,
                            r.cargo,
                            r.funcao,
                            r.lotacao,
                            r.local_trabalho,
                            r.decreto_nomeacao,
                            r.possui_estabilidade,
                            r.data_admissao,
                            r.data_exoneracao,
                            r.tipo_admissao,
                            r.carga_horaria,
                            r.tipo_folha,
                            r.movimentacao,
                            r.salario_base,
                            r.remuneracao_bruta,
                            r.descontos,
                            r.remuneracao_liquida,
                            r.eh_vereador,
                            r.vereador_id,
                            r.gabinete_vereador_id,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE folha_pagamento
                            SET nome_servidor = %s, cargo = %s, lotacao = %s,
                                salario_base = %s, remuneracao_bruta = %s, descontos = %s,
                                remuneracao_liquida = %s, vereador_id = %s, gabinete_vereador_id = %s,
                                hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE folha_id = %s
                            """,
                            (
                                r.nome_servidor,
                                r.cargo,
                                r.lotacao,
                                r.salario_base,
                                r.remuneracao_bruta,
                                r.descontos,
                                r.remuneracao_liquida,
                                r.vereador_id,
                                r.gabinete_vereador_id,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.folha_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_despesas_empenhos(
        self, registros: list[DespesaEmpenhoRegistro]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(asdict(r), contexto="despesa_empenho")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT valor_empenhado_bruto, valor_anulacao, valor_empenhado_liquido,
                           valor_liquidado, valor_pago, saldo_pagar, documento_favorecido,
                           eh_diaria, vereador_beneficiario_id, hash_conteudo
                    FROM despesa_empenho
                    WHERE empenho_id = %s
                    """,
                    (r.empenho_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "valor_empenhado_bruto": r.valor_empenhado_bruto,
                    "valor_anulacao": r.valor_anulacao,
                    "valor_empenhado_liquido": r.valor_empenhado_liquido,
                    "valor_liquidado": r.valor_liquidado,
                    "valor_pago": r.valor_pago,
                    "saldo_pagar": r.saldo_pagar,
                    "documento_favorecido": r.documento_favorecido,
                    "eh_diaria": r.eh_diaria,
                    "vereador_beneficiario_id": r.vereador_beneficiario_id,
                    "hash_conteudo": r.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO despesa_empenho (
                            empenho_id, municipio_id, numero_empenho, ano, mes, data_empenho,
                            fornecedor_id, favorecido_nome, documento_favorecido,
                            tipo_pessoa_favorecido, valor_empenhado_bruto, valor_anulacao,
                            valor_empenhado_liquido, valor_liquidado, valor_pago, saldo_pagar,
                            historico, orgao, processo_licitatorio, destinacao_recurso,
                            unidade, funcao, subfuncao, programa, acao, categoria_economica,
                            grupo_despesa, modalidade_aplicacao, elemento_despesa,
                            subelemento_despesa, fonte_recurso, eh_diaria,
                            vereador_beneficiario_id, fonte_id, fonte_url, coletado_em,
                            hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.empenho_id,
                            r.municipio_id,
                            r.numero_empenho,
                            r.ano,
                            r.mes,
                            r.data_empenho,
                            r.fornecedor_id,
                            r.favorecido_nome,
                            r.documento_favorecido,
                            r.tipo_pessoa_favorecido,
                            r.valor_empenhado_bruto,
                            r.valor_anulacao,
                            r.valor_empenhado_liquido,
                            r.valor_liquidado,
                            r.valor_pago,
                            r.saldo_pagar,
                            r.historico,
                            r.orgao,
                            r.processo_licitatorio,
                            r.destinacao_recurso,
                            r.unidade,
                            r.funcao,
                            r.subfuncao,
                            r.programa,
                            r.acao,
                            r.categoria_economica,
                            r.grupo_despesa,
                            r.modalidade_aplicacao,
                            r.elemento_despesa,
                            r.subelemento_despesa,
                            r.fonte_recurso,
                            r.eh_diaria,
                            r.vereador_beneficiario_id,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE despesa_empenho
                            SET valor_empenhado_bruto = %s, valor_anulacao = %s,
                                valor_empenhado_liquido = %s, valor_liquidado = %s,
                                valor_pago = %s, saldo_pagar = %s, documento_favorecido = %s,
                                eh_diaria = %s, vereador_beneficiario_id = %s,
                                hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE empenho_id = %s
                            """,
                            (
                                r.valor_empenhado_bruto,
                                r.valor_anulacao,
                                r.valor_empenhado_liquido,
                                r.valor_liquidado,
                                r.valor_pago,
                                r.saldo_pagar,
                                r.documento_favorecido,
                                r.eh_diaria,
                                r.vereador_beneficiario_id,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.empenho_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_diarias(self, registros: list[DiariaRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(asdict(r), contexto="diaria")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT beneficiario_nome, tipo_beneficiario, vereador_id_verificado,
                           gabinete_vereador_id, valor_empenhado_liquido, valor_liquidado,
                           valor_pago, hash_conteudo
                    FROM diaria
                    WHERE diaria_id = %s
                    """,
                    (r.diaria_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "beneficiario_nome": r.beneficiario_nome,
                    "tipo_beneficiario": r.tipo_beneficiario,
                    "vereador_id_verificado": r.vereador_id_verificado,
                    "gabinete_vereador_id": r.gabinete_vereador_id,
                    "valor_empenhado_liquido": r.valor_empenhado_liquido,
                    "valor_liquidado": r.valor_liquidado,
                    "valor_pago": r.valor_pago,
                    "hash_conteudo": r.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO diaria (
                            diaria_id, municipio_id, empenho_id, numero_empenho, ano, mes,
                            data_concessao, beneficiario_nome, cpf_mascarado, tipo_beneficiario,
                            vereador_id_verificado, gabinete_vereador_id, cargo_beneficiario,
                            identificacao_documental_verificavel, destino_ou_finalidade,
                            valor_empenhado_liquido, valor_liquidado, valor_pago,
                            origem_registro, fonte_id, fonte_url, coletado_em,
                            hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.diaria_id,
                            r.municipio_id,
                            r.empenho_id,
                            r.numero_empenho,
                            r.ano,
                            r.mes,
                            r.data_concessao,
                            r.beneficiario_nome,
                            r.cpf_mascarado,
                            r.tipo_beneficiario,
                            r.vereador_id_verificado,
                            r.gabinete_vereador_id,
                            r.cargo_beneficiario,
                            r.identificacao_documental_verificavel,
                            r.destino_ou_finalidade,
                            r.valor_empenhado_liquido,
                            r.valor_liquidado,
                            r.valor_pago,
                            r.origem_registro,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE diaria
                            SET beneficiario_nome = %s, tipo_beneficiario = %s,
                                vereador_id_verificado = %s, gabinete_vereador_id = %s,
                                valor_empenhado_liquido = %s, valor_liquidado = %s,
                                valor_pago = %s, hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE diaria_id = %s
                            """,
                            (
                                r.beneficiario_nome,
                                r.tipo_beneficiario,
                                r.vereador_id_verificado,
                                r.gabinete_vereador_id,
                                r.valor_empenhado_liquido,
                                r.valor_liquidado,
                                r.valor_pago,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.diaria_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_duodecimos(self, registros: list[DuodecimoRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(asdict(r), contexto="receita_duodecimo")
                res.lidos += 1
                cur.execute(
                    """
                    SELECT data_lancamento, tipo_natureza, descricao, valor, hash_conteudo
                    FROM receita_duodecimo
                    WHERE duodecimo_id = %s
                    """,
                    (r.duodecimo_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "data_lancamento": r.data_lancamento,
                    "tipo_natureza": r.tipo_natureza,
                    "descricao": r.descricao,
                    "valor": r.valor,
                    "hash_conteudo": r.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO receita_duodecimo (
                            duodecimo_id, municipio_id, id_origem, ano, mes, data_lancamento,
                            tipo_codigo, tipo_natureza, descricao, valor, arquivo_nome,
                            fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            r.duodecimo_id,
                            r.municipio_id,
                            r.id_origem,
                            r.ano,
                            r.mes,
                            r.data_lancamento,
                            r.tipo_codigo,
                            r.tipo_natureza,
                            r.descricao,
                            r.valor,
                            r.arquivo_nome,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE receita_duodecimo
                            SET data_lancamento = %s, tipo_natureza = %s, descricao = %s,
                                valor = %s, hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE duodecimo_id = %s
                            """,
                            (
                                r.data_lancamento,
                                r.tipo_natureza,
                                r.descricao,
                                r.valor,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.duodecimo_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_declaracoes(
        self, registros: list[DeclaracaoTransparenciaRegistro]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(
                    asdict(r), contexto="declaracao_oficial_transparencia"
                )
                res.lidos += 1
                cur.execute(
                    """
                    SELECT titulo_oficial, texto_integral, data_inicio_cobertura,
                           data_fim_cobertura, observacao_cruzamento, hash_conteudo
                    FROM declaracao_oficial_transparencia
                    WHERE declaracao_id = %s
                    """,
                    (r.declaracao_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "titulo_oficial": r.titulo_oficial,
                    "texto_integral": r.texto_integral,
                    "data_inicio_cobertura": r.data_inicio_cobertura,
                    "data_fim_cobertura": r.data_fim_cobertura,
                    "observacao_cruzamento": r.observacao_cruzamento,
                    "hash_conteudo": r.hash_conteudo,
                }
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO declaracao_oficial_transparencia (
                            declaracao_id, municipio_id, tipo_declaracao, titulo_oficial,
                            texto_integral, data_inicio_cobertura, data_fim_cobertura,
                            data_atualizacao, signatario_presidente, signatario_certificador,
                            observacao_cruzamento, fonte_id, fonte_url, coletado_em,
                            hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.declaracao_id,
                            r.municipio_id,
                            r.tipo_declaracao,
                            r.titulo_oficial,
                            r.texto_integral,
                            r.data_inicio_cobertura,
                            r.data_fim_cobertura,
                            r.data_atualizacao,
                            r.signatario_presidente,
                            r.signatario_certificador,
                            r.observacao_cruzamento,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE declaracao_oficial_transparencia
                            SET titulo_oficial = %s, texto_integral = %s,
                                data_inicio_cobertura = %s, data_fim_cobertura = %s,
                                observacao_cruzamento = %s, hash_conteudo = %s,
                                coletado_em = %s, versao_coletor = %s
                            WHERE declaracao_id = %s
                            """,
                            (
                                r.titulo_oficial,
                                r.texto_integral,
                                r.data_inicio_cobertura,
                                r.data_fim_cobertura,
                                r.observacao_cruzamento,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.declaracao_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def salvar_custos_estrutura_mandato(
        self, registros: list[CustoEstruturaMandatoMensalRegistro]
    ) -> ResultadoCarga:
        res = ResultadoCarga()
        with self.conn.cursor(row_factory=dict_row) as cur:
            for r in registros:
                validar_ausencia_cpf_em_valores(
                    asdict(r), contexto="custo_estrutura_mandato_mensal"
                )
                res.lidos += 1
                cur.execute(
                    """
                    SELECT competencia_status, subsidio_bruto_vereador,
                           folha_bruta_gabinete, quantidade_servidores_gabinete,
                           diarias_atribuiveis_pagas, custo_estrutura_mandato_total,
                           hash_conteudo
                    FROM custo_estrutura_mandato_mensal
                    WHERE custo_mensal_id = %s
                    """,
                    (r.custo_mensal_id,),
                )
                existente = cur.fetchone()
                assinatura_nova = {
                    "competencia_status": r.competencia_status,
                    "subsidio_bruto_vereador": r.subsidio_bruto_vereador,
                    "folha_bruta_gabinete": r.folha_bruta_gabinete,
                    "quantidade_servidores_gabinete": r.quantidade_servidores_gabinete,
                    "diarias_atribuiveis_pagas": r.diarias_atribuiveis_pagas,
                    "custo_estrutura_mandato_total": r.custo_estrutura_mandato_total,
                    "hash_conteudo": r.hash_conteudo,
                }
                avisos_json = json.dumps(r.avisos, ensure_ascii=False)
                if existente is None:
                    cur.execute(
                        """
                        INSERT INTO custo_estrutura_mandato_mensal (
                            custo_mensal_id, municipio_id, vereador_id, ano, mes,
                            competencia_status, subsidio_bruto_vereador,
                            subsidio_mensal_base, adicionais_ferias_decimo_terceiro_vereador,
                            folha_bruta_gabinete, folha_mensal_gabinete,
                            adicionais_ferias_decimo_terceiro_gabinete,
                            quantidade_servidores_gabinete, diarias_atribuiveis_empenhadas,
                            diarias_atribuiveis_liquidadas, diarias_atribuiveis_pagas,
                            custo_estrutura_mandato_total, nota_cota_parlamentar,
                            periodo_declaracao_ceap, metodologia_resumo,
                            limitacoes_dados, avisos, fonte_id, fonte_url,
                            coletado_em, hash_conteudo, versao_coletor
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            r.custo_mensal_id,
                            r.municipio_id,
                            r.vereador_id,
                            r.ano,
                            r.mes,
                            r.competencia_status,
                            r.subsidio_bruto_vereador,
                            r.subsidio_mensal_base,
                            r.adicionais_ferias_decimo_terceiro_vereador,
                            r.folha_bruta_gabinete,
                            r.folha_mensal_gabinete,
                            r.adicionais_ferias_decimo_terceiro_gabinete,
                            r.quantidade_servidores_gabinete,
                            r.diarias_atribuiveis_empenhadas,
                            r.diarias_atribuiveis_liquidadas,
                            r.diarias_atribuiveis_pagas,
                            r.custo_estrutura_mandato_total,
                            r.nota_cota_parlamentar,
                            r.periodo_declaracao_ceap,
                            r.metodologia_resumo,
                            r.limitacoes_dados,
                            avisos_json,
                            r.fonte_id,
                            r.fonte_url,
                            r.coletado_em,
                            r.hash_conteudo,
                            r.versao_coletor,
                        ),
                    )
                    res.novos += 1
                else:
                    ex_norm = {
                        **dict(existente),
                        "hash_conteudo": str(existente["hash_conteudo"]).strip(),
                    }
                    if ex_norm != assinatura_nova:
                        cur.execute(
                            """
                            UPDATE custo_estrutura_mandato_mensal
                            SET competencia_status = %s, subsidio_bruto_vereador = %s,
                                subsidio_mensal_base = %s,
                                adicionais_ferias_decimo_terceiro_vereador = %s,
                                folha_bruta_gabinete = %s, folha_mensal_gabinete = %s,
                                adicionais_ferias_decimo_terceiro_gabinete = %s,
                                quantidade_servidores_gabinete = %s,
                                diarias_atribuiveis_empenhadas = %s,
                                diarias_atribuiveis_liquidadas = %s,
                                diarias_atribuiveis_pagas = %s,
                                custo_estrutura_mandato_total = %s,
                                limitacoes_dados = %s, avisos = %s::jsonb,
                                hash_conteudo = %s, coletado_em = %s, versao_coletor = %s
                            WHERE custo_mensal_id = %s
                            """,
                            (
                                r.competencia_status,
                                r.subsidio_bruto_vereador,
                                r.subsidio_mensal_base,
                                r.adicionais_ferias_decimo_terceiro_vereador,
                                r.folha_bruta_gabinete,
                                r.folha_mensal_gabinete,
                                r.adicionais_ferias_decimo_terceiro_gabinete,
                                r.quantidade_servidores_gabinete,
                                r.diarias_atribuiveis_empenhadas,
                                r.diarias_atribuiveis_liquidadas,
                                r.diarias_atribuiveis_pagas,
                                r.custo_estrutura_mandato_total,
                                r.limitacoes_dados,
                                avisos_json,
                                r.hash_conteudo,
                                r.coletado_em,
                                r.versao_coletor,
                                r.custo_mensal_id,
                            ),
                        )
                        res.alterados += 1
                    else:
                        res.inalterados += 1
        self.conn.commit()
        return res

    def carregar_pacote_transparencia_2026(
        self, pacote: PacoteLoteTransparencia2026
    ) -> RelatorioPersistenciaPostgres:
        rel = RelatorioPersistenciaPostgres(
            municipio_id=pacote.municipio_id,
            escopo_ano=pacote.ano,
            executado_em=datetime.now(UTC).isoformat(),
        )

        res_aliases = self.sincronizar_nomes_civis_e_aliases_curados(pacote.municipio_id)
        rel.por_tabela["vereador_alias_curados_centi"] = asdict(res_aliases)

        res_docs = self.salvar_documentos_brutos(pacote.documentos_brutos)
        rel.por_tabela["documento_bruto"] = asdict(res_docs)

        res_forn = self.salvar_fornecedores(pacote.fornecedores)
        rel.por_tabela["fornecedor"] = asdict(res_forn)

        res_folha = self.salvar_folha_pagamento(pacote.folha_pagamento)
        rel.por_tabela["folha_pagamento"] = asdict(res_folha)

        res_desp = self.salvar_despesas_empenhos(pacote.despesas_empenhos)
        rel.por_tabela["despesa_empenho"] = asdict(res_desp)

        res_dia = self.salvar_diarias(pacote.diarias)
        rel.por_tabela["diaria"] = asdict(res_dia)

        res_duo = self.salvar_duodecimos(pacote.duodecimos)
        rel.por_tabela["receita_duodecimo"] = asdict(res_duo)

        res_decl = self.salvar_declaracoes(pacote.declaracoes)
        rel.por_tabela["declaracao_oficial_transparencia"] = asdict(res_decl)

        res_custo = self.salvar_custos_estrutura_mandato(pacote.custos_mandato_mensais)
        rel.por_tabela["custo_estrutura_mandato_mensal"] = asdict(res_custo)

        with self.conn.cursor(row_factory=dict_row) as cur:
            for tabela in (
                "fornecedor",
                "folha_pagamento",
                "despesa_empenho",
                "diaria",
                "receita_duodecimo",
                "declaracao_oficial_transparencia",
                "custo_estrutura_mandato_mensal",
                "documento_bruto",
                "vereador",
                "vereador_alias",
            ):
                cur.execute(
                    f"SELECT COUNT(*) AS c FROM {tabela} WHERE municipio_id = %s",
                    (pacote.municipio_id,),
                )
                row = cur.fetchone()
                rel.contagem_total_banco[tabela] = int(row["c"]) if row else 0

        return rel


def persistir_lote_transparencia_2026_no_postgres(
    *,
    conn: psycopg.Connection[Any],
    diretorio_raiz_lote: Path,
    caminho_migracao_0001: Path | None = None,
    caminho_migracao_0002: Path | None = None,
    municipio_id: str = "inhumas-go",
) -> RelatorioPersistenciaPostgres:
    repo = PostgresTransparenciaRepository(conn)
    if caminho_migracao_0001 is not None:
        repo.aplicar_migracao_sql(caminho_migracao_0001)
    if caminho_migracao_0002 is not None:
        repo.aplicar_migracao_sql(caminho_migracao_0002)

    exec_lote = ExecutorLoteTransparencia2026(
        diretorio_raiz_lote=diretorio_raiz_lote,
        municipio_id=municipio_id,
    )
    pacote = exec_lote.carregar_pacote_do_disco()
    return repo.carregar_pacote_transparencia_2026(pacote)
