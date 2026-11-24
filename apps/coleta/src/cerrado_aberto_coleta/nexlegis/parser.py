"""Etapa 2 (Parse) do coletor Nexlegis: lê o bruto imutável, valida schema e normaliza entidades."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from cerrado_aberto_coleta.entidades import (
    ResolvedorVereadores,
    classificar_tipo_proposicao,
)
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
from cerrado_aberto_coleta.normalizacao import (
    gerar_chave_busca,
    limpar_html_biografia,
    normalizar_texto,
    parse_data_iso,
    parse_datetime_br,
)
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto, calcular_sha256


class LayoutQuebradoError(ValueError):
    """Exceção explícita quando o JSON da fonte muda de estrutura ou omite campos obrigatórios."""

    def __init__(self, mensagem: str, *, fonte_url: str, hash_conteudo: str) -> None:
        super().__init__(f"{mensagem} [fonte_url={fonte_url}, hash={hash_conteudo}]")
        self.fonte_url = fonte_url
        self.hash_conteudo = hash_conteudo


def _normalizar_status_presenca(descricao: str) -> str:
    chave = gerar_chave_busca(descricao)
    if "presente" in chave:
        return "PRESENTE"
    if "justificad" in chave:
        return "FALTA_JUSTIFICADA"
    if "licenc" in chave or "afastad" in chave:
        return "LICENCA"
    return "AUSENTE"


def _normalizar_voto(descricao: str) -> str:
    chave = gerar_chave_busca(descricao)
    if "favoravel" in chave or chave == "sim":
        return "FAVORAVEL"
    if "contrario" in chave or "contra" in chave or chave == "nao":
        return "CONTRARIO"
    if "abstencao" in chave or "absten" in chave:
        return "ABSTENCAO"
    return "AUSENTE"


class NexlegisParser:
    """Parser determinístico e offline para payloads JSON da API Nexlegis."""

    def __init__(self, municipio_id: str, resolvedor: ResolvedorVereadores | None = None) -> None:
        self.municipio_id = municipio_id
        self.resolvedor = resolvedor or ResolvedorVereadores(municipio_id=municipio_id)

    def _carregar_json(self, bruto: bytes, meta: MetadadosDocumentoBruto) -> dict[str, Any]:
        hash_real = calcular_sha256(bruto)
        if hash_real != meta.hash_conteudo:
            raise LayoutQuebradoError(
                "Divergência de hash SHA-256 no arquivo bruto",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )
        try:
            payload = json.loads(bruto.decode("utf-8"))
        except Exception as exc:
            raise LayoutQuebradoError(
                f"JSON malformado na resposta da API: {exc}",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            ) from exc

        if not isinstance(payload, dict):
            raise LayoutQuebradoError(
                "Raiz do JSON não é um objeto dicionário",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )
        return payload

    def parse_vereadores_list(
        self, bruto: bytes, meta: MetadadosDocumentoBruto
    ) -> list[VereadorRegistro]:
        payload = self._carregar_json(bruto, meta)
        lista = payload.get("data")
        if not isinstance(lista, list):
            raise LayoutQuebradoError(
                "Campo obrigatório 'data' (lista de vereadores) ausente ou inválido",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        registros: list[VereadorRegistro] = []
        for idx, item in enumerate(lista):
            if not isinstance(item, dict) or "id" not in item or not item.get("nome"):
                raise LayoutQuebradoError(
                    f"Item de vereador inválido na posição {idx}: campos 'id'/'nome' ausentes",
                    fonte_url=meta.fonte_url,
                    hash_conteudo=meta.hash_conteudo,
                )
            id_origem = int(item["id"])
            vereador_id = self.resolvedor.gerar_id_canonico(id_origem)
            nome_politico = normalizar_texto(item.get("nome_politico") or item.get("nome")) or ""
            nome_exibicao = normalizar_texto(item.get("nome_exibicao") or nome_politico) or nome_politico
            slug = normalizar_texto(item.get("slug")) or gerar_chave_busca(nome_politico).replace(" ", "-")
            bio_html = item.get("biografia")
            bio_texto = limpar_html_biografia(bio_html)

            registros.append(
                VereadorRegistro(
                    municipio_id=self.municipio_id,
                    fonte_id=meta.fonte_id,
                    fonte_url=meta.fonte_url,
                    coletado_em=meta.coletado_em,
                    hash_conteudo=meta.hash_conteudo,
                    versao_coletor=meta.versao_coletor,
                    vereador_id=vereador_id,
                    id_origem_nexlegis=id_origem,
                    nome_civil=None,
                    nome_politico=nome_politico,
                    nome_exibicao=nome_exibicao,
                    slug=slug,
                    chave_busca=gerar_chave_busca(nome_politico, remover_titulos=True),
                    email_publico=normalizar_texto(item.get("email_publico")),
                    avatar_url=normalizar_texto(item.get("avatar")),
                    biografia_html=bio_html,
                    biografia_texto=bio_texto,
                )
            )
        return registros

    def parse_sessoes_list(
        self, bruto: bytes, meta: MetadadosDocumentoBruto
    ) -> list[SessaoRegistro]:
        """Parseia uma página de `/api/sessoes` e deduplica sessões com mesma chave natural."""
        payload = self._carregar_json(bruto, meta)
        lista = payload.get("data")
        if not isinstance(lista, list):
            raise LayoutQuebradoError(
                "Campo obrigatório 'data' (lista de sessões) ausente ou inválido",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        por_chave_natural: dict[tuple[str, int, str, int, date], SessaoRegistro] = {}

        for idx, item in enumerate(lista):
            sessao = self._parse_sessao_dict(item, meta, idx=idx)
            chave = (
                sessao.municipio_id,
                sessao.tipo_id_origem,
                sessao.numero,
                sessao.ano,
                sessao.data_abertura,
            )
            if chave not in por_chave_natural:
                por_chave_natural[chave] = sessao
            else:
                existente = por_chave_natural[chave]
                duplicados = tuple(
                    sorted(set(existente.ids_origem_duplicados + (sessao.id_origem_nexlegis,)))
                )
                por_chave_natural[chave] = existente.model_copy(
                    update={"ids_origem_duplicados": duplicados}
                )

        return list(por_chave_natural.values())

    def _parse_sessao_dict(
        self, item: dict[str, Any], meta: MetadadosDocumentoBruto, *, idx: int = 0
    ) -> SessaoRegistro:
        if not isinstance(item, dict):
            raise LayoutQuebradoError(
                f"Item de sessão na posição {idx} não é um objeto",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )
        campos_obrigatorios = ("id", "numero", "ano", "data", "tipo_id", "nome_sessao")
        faltantes = [
            c
            for c in campos_obrigatorios
            if c not in item or (c in ("id", "ano", "data", "tipo_id") and item.get(c) is None)
        ]
        if faltantes:
            raise LayoutQuebradoError(
                f"Sessão na posição {idx} sem campos obrigatórios: {faltantes}",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        id_origem = int(item["id"])
        data_abertura = parse_data_iso(item.get("data"))
        if data_abertura is None:
            raise LayoutQuebradoError(
                f"Sessão id={id_origem} com data de abertura inválida: {item.get('data')!r}",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        tipo_obj = item.get("tipo") or {}
        tipo_id = int(item["tipo_id"])
        tipo_desc = normalizar_texto(tipo_obj.get("descricao")) or f"Tipo {tipo_id}"
        numero_raw = item.get("numero")
        numero = (
            normalizar_texto(str(numero_raw))
            if numero_raw is not None and str(numero_raw).strip()
            else "S/N"
        )
        ano = int(item["ano"])
        nome_sessao = (
            normalizar_texto(str(item.get("nome_sessao") or ""))
            or f"Sessão {numero}/{ano}"
        )
        slug = normalizar_texto(item.get("slug")) or f"sessao-{id_origem}"

        midias = item.get("midias") or []
        ata_pdf_url = None
        if isinstance(midias, list) and midias:
            ata_pdf_url = normalizar_texto(midias[0].get("url"))

        presidente_id_raw = item.get("presidente_id")
        presidente_ver_id = (
            self.resolvedor.gerar_id_canonico(int(presidente_id_raw))
            if presidente_id_raw is not None
            else None
        )

        return SessaoRegistro(
            municipio_id=self.municipio_id,
            fonte_id=meta.fonte_id,
            fonte_url=meta.fonte_url,
            coletado_em=meta.coletado_em,
            hash_conteudo=meta.hash_conteudo,
            versao_coletor=meta.versao_coletor,
            sessao_id=f"{self.municipio_id}-sessao-{id_origem}",
            id_origem_nexlegis=id_origem,
            tipo_id_origem=tipo_id,
            tipo_descricao=tipo_desc,
            numero=numero,
            ano=ano,
            nome_sessao=nome_sessao,
            slug=slug,
            data_abertura=data_abertura,
            horario_abertura=normalizar_texto(item.get("horario_abertura")),
            data_encerramento=parse_data_iso(item.get("data_encerramento")),
            horario_encerramento=normalizar_texto(item.get("horario_encerramento")),
            inicio_sessao_real=parse_datetime_br(item.get("inicio_sessao")),
            presidente_vereador_id=presidente_ver_id,
            quorum=int(item["quorum"]) if item.get("quorum") is not None else None,
            ata_pdf_url=ata_pdf_url,
        )

    def parse_sessao_detalhe(
        self, bruto: bytes, meta: MetadadosDocumentoBruto
    ) -> PacoteSessaoDetalheParseado:
        """Parseia `/api/sessoes/{id}` extraindo sessão, presenças, pautas, votações e votos nominais."""
        payload = self._carregar_json(bruto, meta)
        sessao = self._parse_sessao_dict(payload, meta)

        presencas_raw = payload.get("presenca")
        if not isinstance(presencas_raw, list):
            raise LayoutQuebradoError(
                f"Sessão id={sessao.id_origem_nexlegis} sem lista 'presenca' no detalhe",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        presencas: list[PresencaRegistro] = []
        for idx, p_item in enumerate(presencas_raw):
            if not isinstance(p_item, dict) or p_item.get("vereador_id") is None:
                raise LayoutQuebradoError(
                    f"Registro de presença inválido na posição {idx}",
                    fonte_url=meta.fonte_url,
                    hash_conteudo=meta.hash_conteudo,
                )
            ver_id_origem = int(p_item["vereador_id"])
            vereador_id = self.resolvedor.gerar_id_canonico(ver_id_origem)
            sit_obj = p_item.get("situacao") or {}
            sit_id = int(p_item.get("situacao_id") or sit_obj.get("id") or 0)
            sit_desc = normalizar_texto(sit_obj.get("descricao")) or "Não informado"

            presencas.append(
                PresencaRegistro(
                    municipio_id=self.municipio_id,
                    fonte_id=meta.fonte_id,
                    fonte_url=meta.fonte_url,
                    coletado_em=meta.coletado_em,
                    hash_conteudo=meta.hash_conteudo,
                    versao_coletor=meta.versao_coletor,
                    presenca_id=f"{sessao.sessao_id}-ver-{ver_id_origem}",
                    sessao_id=sessao.sessao_id,
                    vereador_id=vereador_id,
                    situacao_id_origem=sit_id,
                    situacao_descricao=sit_desc,
                    status_normalizado=_normalizar_status_presenca(sit_desc),
                )
            )

        pautas_raw = payload.get("pautas")
        if not isinstance(pautas_raw, list):
            raise LayoutQuebradoError(
                f"Sessão id={sessao.id_origem_nexlegis} sem lista 'pautas' no detalhe",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        proposicoes_pauta: dict[str, ProposicaoRegistro] = {}
        pauta_itens: list[PautaItemRegistro] = []
        votacoes: list[VotacaoRegistro] = []
        votos_nominais: list[VotoNominalRegistro] = []

        for idx, pauta in enumerate(pautas_raw):
            if not isinstance(pauta, dict) or pauta.get("materia_id") is None:
                raise LayoutQuebradoError(
                    f"Item de pauta inválido na posição {idx}",
                    fonte_url=meta.fonte_url,
                    hash_conteudo=meta.hash_conteudo,
                )
            materia_dict = pauta.get("materia")
            if not isinstance(materia_dict, dict):
                raise LayoutQuebradoError(
                    f"Item de pauta na posição {idx} sem objeto 'materia'",
                    fonte_url=meta.fonte_url,
                    hash_conteudo=meta.hash_conteudo,
                )
            proposicao = self._parse_proposicao_dict(materia_dict, meta, idx=idx)
            proposicoes_pauta[proposicao.proposicao_id] = proposicao

            ordem = int(pauta.get("ordem") or 0)
            turno = int(pauta.get("turno") or 1)
            tipo_pauta_obj = pauta.get("tipo_pauta") or {}

            pauta_itens.append(
                PautaItemRegistro(
                    municipio_id=self.municipio_id,
                    fonte_id=meta.fonte_id,
                    fonte_url=meta.fonte_url,
                    coletado_em=meta.coletado_em,
                    hash_conteudo=meta.hash_conteudo,
                    versao_coletor=meta.versao_coletor,
                    pauta_item_id=f"{sessao.sessao_id}-mat-{proposicao.id_origem_nexlegis}-t{turno}-o{ordem}",
                    sessao_id=sessao.sessao_id,
                    proposicao_id=proposicao.proposicao_id,
                    ordem=ordem,
                    turno=turno,
                    tipo_pauta_id_origem=tipo_pauta_obj.get("id"),
                    tipo_pauta_descricao=normalizar_texto(tipo_pauta_obj.get("descricao")),
                    unanime=bool(pauta.get("unanime", False)),
                    has_votos=bool(pauta.get("has_votos", False)),
                )
            )

            votacao_dict = pauta.get("votacao")
            if isinstance(votacao_dict, dict) and votacao_dict.get("id") is not None:
                vot_id_origem = int(votacao_dict["id"])
                votacao_id = f"{self.municipio_id}-votacao-{vot_id_origem}"
                votacoes.append(
                    VotacaoRegistro(
                        municipio_id=self.municipio_id,
                        fonte_id=meta.fonte_id,
                        fonte_url=meta.fonte_url,
                        coletado_em=meta.coletado_em,
                        hash_conteudo=meta.hash_conteudo,
                        versao_coletor=meta.versao_coletor,
                        votacao_id=votacao_id,
                        id_origem_nexlegis=vot_id_origem,
                        sessao_id=sessao.sessao_id,
                        proposicao_id=proposicao.proposicao_id,
                        tipo_turno_id=votacao_dict.get("tipo_turno_id"),
                        unanime=bool(votacao_dict.get("unanime", False)),
                        has_votos=bool(votacao_dict.get("has_votos", False)),
                        discussed_at=parse_datetime_br(votacao_dict.get("discussed_at")),
                        started_at=parse_datetime_br(votacao_dict.get("started_at")),
                        closed_at=parse_datetime_br(votacao_dict.get("closed_at")),
                        tempo_decorrido_segundos=votacao_dict.get("tempo_decorrido"),
                    )
                )

                votos_raw = votacao_dict.get("votos") or []
                for v_item in votos_raw:
                    if not isinstance(v_item, dict) or v_item.get("vereador_id") is None:
                        continue
                    ver_id_voto = int(v_item["vereador_id"])
                    vereador_id_canonico = self.resolvedor.gerar_id_canonico(ver_id_voto)
                    voto_obj = v_item.get("voto") or {}
                    voto_id_orig = int(voto_obj.get("id") or 0)
                    voto_desc = normalizar_texto(voto_obj.get("descricao")) or "Não informado"

                    votos_nominais.append(
                        VotoNominalRegistro(
                            municipio_id=self.municipio_id,
                            fonte_id=meta.fonte_id,
                            fonte_url=meta.fonte_url,
                            coletado_em=meta.coletado_em,
                            hash_conteudo=meta.hash_conteudo,
                            versao_coletor=meta.versao_coletor,
                            voto_id=f"{votacao_id}-ver-{ver_id_voto}",
                            votacao_id=votacao_id,
                            vereador_id=vereador_id_canonico,
                            voto_id_origem=voto_id_orig,
                            voto_descricao=voto_desc,
                            voto_normalizado=_normalizar_voto(voto_desc),
                        )
                    )

        return PacoteSessaoDetalheParseado(
            sessao=sessao,
            presencas=tuple(presencas),
            proposicoes_pauta=tuple(proposicoes_pauta.values()),
            pauta_itens=tuple(pauta_itens),
            votacoes=tuple(votacoes),
            votos_nominais=tuple(votos_nominais),
        )

    def _parse_proposicao_dict(
        self, item: dict[str, Any], meta: MetadadosDocumentoBruto, *, idx: int = 0
    ) -> ProposicaoRegistro:
        campos_obrigatorios = ("id", "numero", "ano", "tipo_id", "ementa", "nome_materia")
        faltantes = [
            c
            for c in campos_obrigatorios
            if c not in item or (c in ("id", "ano", "tipo_id") and item.get(c) is None)
        ]
        if faltantes:
            raise LayoutQuebradoError(
                f"Matéria na posição {idx} sem campos obrigatórios: {faltantes}",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        id_origem = int(item["id"])
        tipo_id = int(item["tipo_id"])
        tipo_obj = item.get("tipo") or {}
        tipo_desc = normalizar_texto(tipo_obj.get("descricao")) or f"Tipo {tipo_id}"

        regra_tipo = classificar_tipo_proposicao(tipo_id, tipo_desc)

        midias = item.get("midias") or []
        anexo_url = None
        anexo_nome = None
        anexo_mime = None
        anexo_tam = None
        if isinstance(midias, list) and midias:
            m0 = midias[0]
            anexo_url = normalizar_texto(m0.get("url"))
            anexo_nome = normalizar_texto(m0.get("file_name") or m0.get("name"))
            anexo_mime = normalizar_texto(m0.get("mime_type"))
            anexo_tam = int(m0["size"]) if m0.get("size") is not None else None

        situacao_val = item.get("situacao")
        if isinstance(situacao_val, dict):
            situacao_str = normalizar_texto(situacao_val.get("descricao"))
        else:
            situacao_str = normalizar_texto(str(situacao_val)) if situacao_val is not None else None

        numero_limpo = normalizar_texto(str(item.get("numero") or "")) or "S/N"
        nome_mat_limpo = (
            normalizar_texto(str(item.get("nome_materia") or ""))
            or f"{tipo_desc} {numero_limpo}/{item['ano']}"
        )
        ementa_limpa = (
            normalizar_texto(str(item.get("ementa") or ""))
            or "[EMENTA VAZIA NA FONTE]"
        )

        return ProposicaoRegistro(
            municipio_id=self.municipio_id,
            fonte_id=meta.fonte_id,
            fonte_url=meta.fonte_url,
            coletado_em=meta.coletado_em,
            hash_conteudo=meta.hash_conteudo,
            versao_coletor=meta.versao_coletor,
            proposicao_id=f"{self.municipio_id}-prop-{id_origem}",
            id_origem_nexlegis=id_origem,
            tipo_id_origem=tipo_id,
            tipo_descricao_origem=tipo_desc,
            numero=numero_limpo,
            ano=int(item["ano"]),
            nome_materia=nome_mat_limpo,
            slug=normalizar_texto(item.get("slug")),
            ementa=ementa_limpa,
            data_publicacao=parse_data_iso(item.get("data_publicacao")),
            ultima_movimentacao=parse_data_iso(item.get("ultima_movimentacao")),
            situacao_atual=situacao_str,
            local_origem=normalizar_texto(item.get("local_origem"))
            if isinstance(item.get("local_origem"), str)
            else None,
            local_destino=normalizar_texto(item.get("local_destino"))
            if isinstance(item.get("local_destino"), str)
            else None,
            autoria_codigo_origem=int(item["autoria"]) if item.get("autoria") is not None else None,
            anexo_principal_url=anexo_url,
            anexo_principal_nome=anexo_nome,
            anexo_principal_mime=anexo_mime,
            anexo_principal_tamanho=anexo_tam,
            categoria_classificada=regra_tipo.categoria,
            eh_proposicao_parlamentar=regra_tipo.eh_proposicao_parlamentar,
            contabilizar_producao_vereador=regra_tipo.contabilizar_producao_vereador,
        )

    def parse_materia_detalhe(
        self, bruto: bytes, meta: MetadadosDocumentoBruto
    ) -> PacoteMateriasParseado:
        """Parseia um objeto individual de matéria (`/api/materias/{id}`)."""
        payload = self._carregar_json(bruto, meta)
        wrapper = {"data": [payload], "total": 1, "current_page": 1, "last_page": 1}
        return self._parse_lista_materias_interna(wrapper, meta)

    def parse_materias_list(
        self, bruto: bytes, meta: MetadadosDocumentoBruto
    ) -> PacoteMateriasParseado:
        """Parseia uma página de `/api/materias` preservando 100% dos registros e classificando-os."""
        payload = self._carregar_json(bruto, meta)
        return self._parse_lista_materias_interna(payload, meta)

    def _parse_lista_materias_interna(
        self, payload: dict[str, Any], meta: MetadadosDocumentoBruto
    ) -> PacoteMateriasParseado:
        lista = payload.get("data")
        if not isinstance(lista, list):
            raise LayoutQuebradoError(
                "Campo obrigatório 'data' (lista de matérias) ausente ou inválido",
                fonte_url=meta.fonte_url,
                hash_conteudo=meta.hash_conteudo,
            )

        proposicoes: list[ProposicaoRegistro] = []
        autorias: list[AutoriaRegistro] = []
        tramitacoes: list[TramitacaoRegistro] = []

        for idx, item in enumerate(lista):
            if not isinstance(item, dict):
                raise LayoutQuebradoError(
                    f"Matéria na posição {idx} não é um objeto",
                    fonte_url=meta.fonte_url,
                    hash_conteudo=meta.hash_conteudo,
                )
            prop = self._parse_proposicao_dict(item, meta, idx=idx)
            proposicoes.append(prop)

            # Autorias parlamentares
            vereadores_autoria = item.get("vereadores") or []
            if isinstance(vereadores_autoria, list) and vereadores_autoria:
                for v_aut in vereadores_autoria:
                    if not isinstance(v_aut, dict) or v_aut.get("vereador_id") is None:
                        continue
                    ver_id_orig = int(v_aut["vereador_id"])
                    ver_id_canon = self.resolvedor.gerar_id_canonico(ver_id_orig)
                    autorias.append(
                        AutoriaRegistro(
                            municipio_id=self.municipio_id,
                            fonte_id=meta.fonte_id,
                            fonte_url=meta.fonte_url,
                            coletado_em=meta.coletado_em,
                            hash_conteudo=meta.hash_conteudo,
                            versao_coletor=meta.versao_coletor,
                            autoria_id=f"{prop.proposicao_id}-aut-ver-{ver_id_orig}",
                            proposicao_id=prop.proposicao_id,
                            vereador_id=ver_id_canon,
                            autor_institucional=None,
                            tipo_autor="VEREADOR",
                        )
                    )
            else:
                # Autoria institucional (Executivo, Secretaria Geral, Mesa Diretora)
                origem_inst = prop.local_origem or "INSTITUCIONAL"
                tipo_aut = "EXECUTIVO" if prop.autoria_codigo_origem == 1 else "OUTRO"
                autorias.append(
                    AutoriaRegistro(
                        municipio_id=self.municipio_id,
                        fonte_id=meta.fonte_id,
                        fonte_url=meta.fonte_url,
                        coletado_em=meta.coletado_em,
                        hash_conteudo=meta.hash_conteudo,
                        versao_coletor=meta.versao_coletor,
                        autoria_id=f"{prop.proposicao_id}-aut-inst",
                        proposicao_id=prop.proposicao_id,
                        vereador_id=None,
                        autor_institucional=origem_inst,
                        tipo_autor=tipo_aut,
                    )
                )

            # Tramitação atual
            tram_dict = item.get("tramitacao")
            if isinstance(tram_dict, dict) and tram_dict.get("id") is not None:
                tram_id_orig = int(tram_dict["id"])
                data_tram = parse_data_iso(tram_dict.get("data")) or prop.data_publicacao
                if data_tram is not None:
                    loc_orig_obj = tram_dict.get("local_origem")
                    loc_dest_obj = tram_dict.get("local_destino")
                    sit_obj = tram_dict.get("situacao")
                    tramitacoes.append(
                        TramitacaoRegistro(
                            municipio_id=self.municipio_id,
                            fonte_id=meta.fonte_id,
                            fonte_url=meta.fonte_url,
                            coletado_em=meta.coletado_em,
                            hash_conteudo=meta.hash_conteudo,
                            versao_coletor=meta.versao_coletor,
                            tramitacao_id=f"{self.municipio_id}-tram-{tram_id_orig}",
                            proposicao_id=prop.proposicao_id,
                            id_origem_nexlegis=tram_id_orig,
                            data_tramitacao=data_tram,
                            local_origem=normalizar_texto(loc_orig_obj.get("descricao"))
                            if isinstance(loc_orig_obj, dict)
                            else None,
                            local_destino=normalizar_texto(loc_dest_obj.get("descricao"))
                            if isinstance(loc_dest_obj, dict)
                            else None,
                            situacao_descricao=normalizar_texto(sit_obj.get("descricao"))
                            if isinstance(sit_obj, dict)
                            else None,
                            prioridade_descricao=normalizar_texto(
                                tram_dict.get("prioridade_descricao")
                            ),
                            prazo_descricao=normalizar_texto(tram_dict.get("prazo_descricao")),
                            justificativa=normalizar_texto(tram_dict.get("justificativa")),
                        )
                    )

        meta_pag = payload.get("meta") or {}
        total_api = int(payload.get("total") or meta_pag.get("total") or len(proposicoes))
        pagina_atual = int(payload.get("current_page") or meta_pag.get("current_page") or 1)
        ultima_pagina = int(payload.get("last_page") or meta_pag.get("last_page") or 1)

        return PacoteMateriasParseado(
            proposicoes=tuple(proposicoes),
            autorias=tuple(autorias),
            tramitacoes=tuple(tramitacoes),
            total_api=total_api,
            pagina_atual=pagina_atual,
            ultima_pagina=ultima_pagina,
        )
