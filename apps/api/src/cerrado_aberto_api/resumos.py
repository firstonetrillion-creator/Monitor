"""Motor determinístico de resumos em linguagem simples, alertas WhatsApp e cards Instagram (Fase 4).

Regras editoriais obrigatórias (`docs/05-etica-legal-editorial.md` e skill `texto-cidadao`):
- Todo resumo carrega o selo explícito "Resumo automático" + link para o documento original.
- Frases curtas, voz ativa, explicação de termos técnicos sem juridiquês e sem inventar dados.
- Neutralidade absoluta: zero adjetivos avaliativos e zero vocabulário proibido.
- Alertas de WhatsApp com limite estrito de 400 caracteres, 1 ideia central, fonte e opção de sair.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from cerrado_aberto_api.schemas import (
    DestaquePautaBoletimOut,
    PanoramaFinanceiroBoletimOut,
    ResumoCidadaoOut,
    SlideInstagramOut,
)

PALAVRAS_PROIBIDAS_TEXTO_CIDADAO: tuple[str, ...] = (
    "fraude",
    "desvio",
    "esquema",
    "irregular",
    "suspeito",
    "escândalo",
    "absurdo",
    "farra",
    "mamata",
)

_SIGLAS_PRESERVADAS: tuple[str, ...] = (
    "SUS",
    "IPTU",
    "ITBI",
    "ISS",
    "LDO",
    "LOA",
    "PPA",
    "CEAP",
    "LGPD",
    "LAI",
    "IBGE",
    "IFG",
    "UEG",
    "UBSF",
    "UBS",
    "UPA",
    "CRAS",
    "CREAS",
    "CAPS",
    "CMI",
    "CMEI",
    "GO",
    "GO-070",
    "GO-222",
    "BR",
    "CNPJ",
    "CPF",
    "TCM",
    "TCM-GO",
    "SAMU",
    "PM",
    "INSS",
    "DETRAN",
    "SANEAGO",
    "EQUATORIAL",
    "PJ",
    "PF",
)

_PREAMBULOS_BUROCRATICOS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"^(requer|requerer)\s+(à\s+mesa\s+diretora\s+)?(que\s+seja\s+)?"
            r"(encaminhado\s+|enviado\s+)?(of[íi]cio|expediente)\s+"
            r"(ao\s+|à\s+)?(excelent[íi]ssimo\s+|exmo\.?\s+)?(senhor\s+|sr\.?\s+)?"
            r"prefeito\s+municipal[\s,:-]*(solicitando|requerendo|pedindo|para\s+que)?\s*",
            re.IGNORECASE,
        ),
        "Solicita ao Prefeito Municipal ",
    ),
    (
        re.compile(
            r"^(requer|requerer)\s+(que\s+seja\s+)?(realizado|realizada|feito|feita|providenciado|providenciada)\s+",
            re.IGNORECASE,
        ),
        "Solicita que seja feito(a) ",
    ),
    (
        re.compile(r"^requer\s+", re.IGNORECASE),
        "Solicita ",
    ),
    (
        re.compile(r"^disp[õo]e\s+sobre\s+", re.IGNORECASE),
        "Trata sobre ",
    ),
    (
        re.compile(r"^altera\s+dispositivos?\s+da\s+lei", re.IGNORECASE),
        "Propõe alteração na Lei",
    ),
    (
        re.compile(r"^institui\s+", re.IGNORECASE),
        "Propõe criar ",
    ),
    (
        re.compile(r"^concede\s+", re.IGNORECASE),
        "Propõe conceder ",
    ),
)

_ROTULO_TRANSPARENCIA_PADRAO = (
    "Resumo automático gerado a partir dos registros oficiais — confira sempre o documento original."
)
_FUSO_GOIAS = timezone(timedelta(hours=-3))


def _formatar_data_br(d: date | None) -> str:
    if d is None:
        return "data não informada"
    return d.strftime("%d/%m/%Y")


def _formatar_coleta_br(dt: datetime) -> str:
    dt_local = dt.astimezone(_FUSO_GOIAS) if dt.tzinfo is not None else dt
    return dt_local.strftime("%d/%m/%Y")


def _truncar_palavras(texto: str, limite: int) -> str:
    limpo = re.sub(r"\s+", " ", texto).strip()
    if len(limpo) <= limite:
        return limpo
    corte = limpo[: max(1, limite - 1)]
    if " " in corte:
        corte = corte.rsplit(" ", 1)[0]
    corte = corte.rstrip(".,;:—–-\"' ")
    return f"{corte}…"


def _formatar_brl(valor: Decimal | None) -> str:
    if valor is None:
        return "não apurado"
    bruto = f"{valor:,.2f}"
    return f"R$ {bruto.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def explicar_tipo_proposicao(tipo_descricao: str) -> str:
    """Traduz o tipo legislativo oficial para uma explicação curta em português claro."""
    t = (tipo_descricao or "").strip().lower()
    if "requerimento" in t:
        return (
            "Requerimento: pedido formal feito por vereador à Prefeitura ou a um órgão público "
            "(como manutenção de rua, iluminação ou informação). Não cria lei, mas registra a solicitação oficial."
        )
    if "indica" in t:
        return (
            "Indicação: sugestão de obra, serviço ou melhoria encaminhada ao Poder Executivo. "
            "Serve para registrar uma demanda da população, sem força de lei."
        )
    if "projeto de lei" in t and "executivo" in t:
        return (
            "Projeto de Lei do Executivo: proposta de lei enviada pela Prefeitura para análise "
            "e votação dos vereadores em plenário."
        )
    if "projeto de lei" in t:
        return (
            "Projeto de Lei do Legislativo: proposta de nova lei municipal apresentada por vereador. "
            "Para valer, precisa ser aprovada pelos vereadores e sancionada pela Prefeitura."
        )
    if "decreto" in t or "resolu" in t:
        return (
            f"{tipo_descricao}: proposta que trata de regras internas da Câmara Municipal "
            "ou da concessão de homenagens e títulos oficiais."
        )
    if "mo" in t and ("ção" in t or "cao" in t):
        return (
            "Moção: manifestação formal da Câmara (aplauso, apoio, pesar ou repúdio) registrada em plenário. "
            "Não altera leis nem despesas."
        )
    if "ata" in t:
        return (
            "Ata de Sessão: documento administrativo que registra o resumo da reunião anterior. "
            "Não entra na contagem individual de produção dos vereadores."
        )
    return f"{tipo_descricao or 'Proposição'}: documento oficial registrado no sistema legislativo da Câmara Municipal."


def limpar_ementa_cidada(ementa: str | None) -> str:
    """Limpa fórmulas burocráticas e caixa alta excessiva preservando fidelidade ao texto oficial."""
    texto = re.sub(r"\s+", " ", (ementa or "").strip())
    if len(texto) < 12:
        return (
            "A ementa oficial publicada é breve e não detalha o conteúdo completo; "
            "consulte o documento original na fonte."
        )

    # Se estiver quase todo em CAIXA ALTA, normaliza para frase legível preservando siglas
    letras = [c for c in texto if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.7:
        texto = texto.lower()
        texto = texto[0].upper() + texto[1:]
        for sigla in _SIGLAS_PRESERVADAS:
            texto = re.sub(rf"\b{re.escape(sigla.lower())}\b", sigla, texto)
        # Preserva nomes próprios de meses/unidades comuns e "Prefeito Municipal"
        texto = re.sub(r"\binhumas\b", "Inhumas", texto)
        texto = re.sub(r"\bgoi[áa]s\b", "Goiás", texto)
        texto = re.sub(r"\bprefeito municipal\b", "Prefeito Municipal", texto)
        texto = re.sub(r"\bc[âa]mara municipal\b", "Câmara Municipal", texto)

    for padrao, substituto in _PREAMBULOS_BUROCRATICOS:
        novo = padrao.sub(substituto, texto, count=1)
        if novo != texto:
            texto = novo.strip()
            break

    # Corrige duplicação acidental de verbo no início (ex.: "Solicita solicitam ...") presente na fonte
    texto = re.sub(r"^solicita\s+solicita[mr]?\b", "Solicita", texto, count=1, flags=re.IGNORECASE)

    if texto and not texto[0].isupper():
        texto = texto[0].upper() + texto[1:]
    if texto and texto[-1] not in ".!?":
        texto = f"{texto}."
    return texto


def gerar_resumo_materia(
    *,
    nome_materia: str,
    tipo_descricao: str,
    ementa: str | None,
    autores_nomes: list[str],
    situacao_atual: str | None,
    data_referencia: date | None,
    placar_resumo: str | None,
    fonte_url: str,
    coletado_em: datetime,
) -> ResumoCidadaoOut:
    """Monta resumo estruturado em 3 linhas para uma proposição legislativa."""
    o_que_e = explicar_tipo_proposicao(tipo_descricao)
    o_que_propoe = limpar_ementa_cidada(ementa)

    autoria_txt = (
        f"Autoria: {', '.join(autores_nomes)}."
        if autores_nomes
        else "Autoria institucional ou não discriminada na fonte."
    )
    partes_sit: list[str] = [autoria_txt]
    if placar_resumo:
        partes_sit.append(f"Deliberação: {placar_resumo}.")
    elif situacao_atual:
        partes_sit.append(f"Situação publicada: {situacao_atual}.")
    else:
        partes_sit.append("Situação de votação não publicada até a última coleta.")

    if data_referencia:
        partes_sit.append(f"Último registro em {_formatar_data_br(data_referencia)}.")

    situacao_e_resultado = " ".join(partes_sit)
    ementa_curta = _truncar_palavras(o_que_propoe, 220)
    texto_3_linhas = f"{nome_materia}: {ementa_curta} {situacao_e_resultado}"

    return ResumoCidadaoOut(
        rotulo_transparencia=_ROTULO_TRANSPARENCIA_PADRAO,
        metodo_geracao="AUTOMATICO_DETERMINISTICO",
        revisado_por_humano=False,
        o_que_e=o_que_e,
        o_que_propoe=o_que_propoe,
        situacao_e_resultado=situacao_e_resultado,
        texto_resumo_3_linhas=texto_3_linhas,
        fonte_url=fonte_url,
        coletado_em=coletado_em,
    )


def gerar_resumo_sessao(
    *,
    nome_sessao: str,
    data_abertura: date,
    total_presentes: int,
    total_faltas_justificadas: int,
    total_ausentes: int,
    total_licencas: int,
    total_proposicoes_parlamentares: int,
    total_votacoes: int,
    contagem_por_tipo: dict[str, int],
    fonte_url: str,
    coletado_em: datetime,
) -> ResumoCidadaoOut:
    """Monta resumo cidadão neutro de uma sessão plenária."""
    data_br = _formatar_data_br(data_abertura)
    o_que_e = (
        f"{nome_sessao} realizada em {data_br} na Câmara Municipal de Inhumas "
        "(reunião plenária onde os vereadores discutem e votam propostas da cidade)."
    )

    if contagem_por_tipo:
        resumo_tipos = ", ".join(
            f"{qtd} {tipo}" for tipo, qtd in sorted(contagem_por_tipo.items(), key=lambda x: (-x[1], x[0]))
        )
        o_que_propoe = (
            f"A pauta reuniu {total_proposicoes_parlamentares} proposições parlamentares "
            f"({resumo_tipos}), além de eventuais registros administrativos como atas."
        )
    else:
        o_que_propoe = "A sessão não registrou proposições parlamentares listadas na pauta oficial."

    partes_presenca = [f"{total_presentes} vereadores registraram presença"]
    if total_faltas_justificadas > 0:
        partes_presenca.append(f"{total_faltas_justificadas} falta(s) justificada(s)")
    if total_licencas > 0:
        partes_presenca.append(f"{total_licencas} em licença")
    if total_ausentes > 0:
        partes_presenca.append(f"{total_ausentes} não registraram presença")

    situacao_e_resultado = (
        f"{', '.join(partes_presenca)} e houve {total_votacoes} votação(ões) registrada(s) no sistema."
    )
    texto_3_linhas = f"Na {nome_sessao} ({data_br}), {situacao_e_resultado} {o_que_propoe}"

    return ResumoCidadaoOut(
        rotulo_transparencia=_ROTULO_TRANSPARENCIA_PADRAO,
        metodo_geracao="AUTOMATICO_DETERMINISTICO",
        revisado_por_humano=False,
        o_que_e=o_que_e,
        o_que_propoe=o_que_propoe,
        situacao_e_resultado=situacao_e_resultado,
        texto_resumo_3_linhas=texto_3_linhas,
        fonte_url=fonte_url,
        coletado_em=coletado_em,
    )


def gerar_alerta_whatsapp(
    *,
    nome_sessao: str,
    data_abertura: date,
    total_presentes: int,
    total_proposicoes_parlamentares: int,
    contagem_por_tipo: dict[str, int],
    url_sessao: str,
    coletado_em: datetime,
) -> str:
    """Gera alerta pronto para WhatsApp estritamente dentro do limite de 400 caracteres."""
    data_br = _formatar_data_br(data_abertura)
    coleta_br = _formatar_coleta_br(coletado_em)
    tipos_top = ", ".join(
        f"{qtd} {tipo}"
        for tipo, qtd in sorted(contagem_por_tipo.items(), key=lambda x: (-x[1], x[0]))[:3]
    )
    bloco_pauta = (
        f"{total_proposicoes_parlamentares} proposições ({tipos_top})"
        if tipos_top
        else f"{total_proposicoes_parlamentares} proposições"
    )
    cabecalho = f"Cerrado Aberto | {nome_sessao} ({data_br})"
    corpo = f"Resumo automático: {total_presentes} presentes e {bloco_pauta} na pauta."
    rodape = f"Fonte: Nexlegis ({coleta_br}). Confira: {url_sessao}\nPara parar, responda SAIR."

    mensagem = f"{cabecalho}\n{corpo}\n{rodape}"
    if len(mensagem) <= 400:
        return mensagem

    # Reduz apenas o bloco_pauta caso nomes de tipos sejam longos, preservando fonte, link e opt-out
    corpo_curto = (
        f"Resumo automático: {total_presentes} presentes e "
        f"{total_proposicoes_parlamentares} proposições na pauta."
    )
    mensagem = f"{cabecalho}\n{corpo_curto}\n{rodape}"
    return mensagem[:400]


def gerar_legenda_instagram(
    *,
    nome_sessao: str,
    data_abertura: date,
    total_presentes: int,
    total_proposicoes_parlamentares: int,
    destaques: list[DestaquePautaBoletimOut],
    panorama: PanoramaFinanceiroBoletimOut,
    coletado_em: datetime,
    handle_instagram: str = "@cerradoaberto",
    dominio_oficial: str = "cerradoaberto.org.br",
) -> str:
    """Gera legenda neutra pronta para o Instagram Oficial do Cerrado Aberto."""
    data_br = _formatar_data_br(data_abertura)
    coleta_br = _formatar_coleta_br(coletado_em)
    linhas_destaque = [
        f"• {d.nome_materia}: {_truncar_palavras(d.resumo_cidadao.o_que_propoe, 130)}"
        for d in destaques[:4]
    ]
    bloco_destaques = (
        "\n".join(linhas_destaque)
        if linhas_destaque
        else "• Consulte os itens completos da pauta no portal."
    )
    per_capita_txt = (
        f"{_formatar_brl(panorama.valor_por_habitante_mes)} por habitante/mês "
        f"(base IBGE 2026: {panorama.populacao_ibge_2026:,} hab.)".replace(",", ".")
        if panorama.valor_por_habitante_mes is not None
        else "em apuração"
    )

    return (
        f"Resumo da Semana | {nome_sessao} ({data_br})\n\n"
        f"Na reunião de {data_br}, {total_presentes} vereadores registraram presença e "
        f"{total_proposicoes_parlamentares} proposições parlamentares entraram na pauta.\n\n"
        f"Destaques (Resumo automático):\n{bloco_destaques}\n\n"
        f"Panorama financeiro 2026: despesas pagas acumuladas de "
        f"{_formatar_brl(panorama.despesa_paga_acumulada)} — equivalente a {per_capita_txt}.\n\n"
        f"Fonte oficial: Nexlegis e Portal da Transparência da Câmara de Inhumas (coleta em {coleta_br}).\n"
        f"Confira os documentos originais em {dominio_oficial}\n\n"
        f"{handle_instagram} — Iniciativa cidadã independente, sem vínculo com a Câmara Municipal.\n"
        "#CerradoAberto #Inhumas #TransparenciaPublica #ControleSocial"
    )


def gerar_slides_instagram(
    *,
    nome_sessao: str,
    data_abertura: date,
    total_presentes: int,
    total_proposicoes_parlamentares: int,
    total_votacoes: int,
    destaques: list[DestaquePautaBoletimOut],
    panorama: PanoramaFinanceiroBoletimOut,
    coletado_em: datetime,
    handle_instagram: str = "@cerradoaberto",
    dominio_oficial: str = "cerradoaberto.org.br",
) -> list[SlideInstagramOut]:
    """Estrutura 3 slides para o gerador de carrossel PNG (1080×1350) do Instagram Oficial."""
    data_br = _formatar_data_br(data_abertura)
    coleta_br = _formatar_coleta_br(coletado_em)
    rodape = (
        f"Fonte: Nexlegis e Transparência (coleta {coleta_br}) · "
        f"{handle_instagram} · {dominio_oficial}"
    )

    itens_pauta_slide2 = [
        f"{d.nome_materia} — {_truncar_palavras(d.resumo_cidadao.o_que_propoe, 98)}"
        for d in destaques[:4]
    ]
    if not itens_pauta_slide2:
        itens_pauta_slide2 = ["Consulte a pauta completa na página da sessão."]

    per_capita_str = (
        f"{_formatar_brl(panorama.valor_por_habitante_mes)} / habitante / mês"
        if panorama.valor_por_habitante_mes is not None
        else "Não apurado"
    )

    return [
        SlideInstagramOut(
            numero=1,
            etiqueta="BOLETIM DA SEMANA · INHUMAS (GO)",
            titulo=nome_sessao,
            subtitulo=f"Realizada em {data_br} · Resumo automático baseado em dados oficiais",
            itens=[
                f"{total_presentes} vereadores com presença registrada",
                f"{total_proposicoes_parlamentares} proposições parlamentares na pauta",
                f"{total_votacoes} votações registradas em plenário",
            ],
            rodape_fonte=rodape,
        ),
        SlideInstagramOut(
            numero=2,
            etiqueta="O QUE ENTROU NA PAUTA (RESUMO AUTOMÁTICO)",
            titulo="Principais propostas discutidas",
            subtitulo="Linguagem simples — confira a íntegra no documento oficial",
            itens=itens_pauta_slide2,
            rodape_fonte=rodape,
        ),
        SlideInstagramOut(
            numero=3,
            etiqueta="PARA ONDE VAI O DINHEIRO (2026)",
            titulo=per_capita_str,
            subtitulo=(
                f"Despesa paga em {panorama.meses_apurados} meses: "
                f"{_formatar_brl(panorama.despesa_paga_acumulada)}"
            ),
            itens=[
                f"Duodécimo recebido: {_formatar_brl(panorama.duodecimo_recebido_acumulado)}",
                f"Devoluções à Prefeitura: {_formatar_brl(panorama.duodecimo_devolvido_acumulado)}",
                f"População oficial IBGE 2026: {panorama.populacao_ibge_2026:,} hab.".replace(",", "."),
                "Cota parlamentar (CEAP): inexistente em Inhumas",
            ],
            rodape_fonte=rodape,
        ),
    ]
