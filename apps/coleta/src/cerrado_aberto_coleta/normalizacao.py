"""Funções puras de normalização de dados públicos brasileiros (skill normalizacao-e-entidades)."""

from __future__ import annotations

import html
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

_RE_ESPACOS = re.compile(r"\s+")
_RE_TAGS_HTML = re.compile(r"<[^>]+>")
_RE_PREFIXOS_TITULO = re.compile(
    r"^(?:gab\.?\s*(?:do|da)?\s*vereador(?:a)?\s+|vereador(?:a)?\s+|prof(?:essor(?:a)?|[°ªº.]*)\s*\.?\s*|dr(?:a)?\.?\s+)",
    re.IGNORECASE,
)
_RE_CPF_FORMATADO = re.compile(r"^\d{3}\.[0-9xX*]{3}\.[0-9xX*]{3}-\d{2}$")


def normalizar_texto(valor: str | None) -> str | None:
    """Normaliza Unicode (NFC), desescapa entidades HTML, faz trim e remove espaços duplicados."""
    if valor is None:
        return None
    texto = html.unescape(valor)
    texto = unicodedata.normalize("NFC", texto)
    texto = _RE_ESPACOS.sub(" ", texto).strip()
    return texto if texto else None


def remover_acentos(valor: str) -> str:
    """Remove marcas diacríticas mantendo apenas caracteres base ASCII."""
    nfd = unicodedata.normalize("NFD", valor)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def gerar_chave_busca(valor: str | None, *, remover_titulos: bool = False) -> str:
    """Gera chave canônica em minúsculas, sem acentos e sem pontuação supérflua."""
    limpo = normalizar_texto(valor)
    if not limpo:
        return ""
    sem_acento = remover_acentos(limpo).lower()
    if remover_titulos:
        sem_acento = _RE_PREFIXOS_TITULO.sub("", sem_acento).strip()
    sem_pontuacao = re.sub(r"[^a-z0-9\s]", " ", sem_acento)
    return _RE_ESPACOS.sub(" ", sem_pontuacao).strip()


def limpar_html_biografia(html_bruto: str | None) -> str | None:
    """Converte biografia em HTML do Nexlegis para texto plano limpo."""
    if not html_bruto:
        return None
    sem_tags = _RE_TAGS_HTML.sub(" ", html_bruto)
    return normalizar_texto(sem_tags)


def parse_valor_brl(valor: str | float | Decimal | None) -> Decimal | None:
    """Converte valor monetário para Decimal(14,2).

    Regra inegociável (ADR-005):
    - Nunca retorna float.
    - Dados ausentes (None ou string vazia) permanecem None (nunca viram 0).
    """
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return valor.quantize(Decimal("0.01"))
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"))

    texto = str(valor).strip()
    if not texto:
        return None

    texto = re.sub(r"[R$\s]", "", texto)
    # Formato brasileiro: "4.989,80" ou "-1.234,56"
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: {valor!r}") from exc


def parse_data_iso(valor: str | date | datetime | None) -> date | None:
    """Converte datas ('YYYY-MM-DD', 'DD/MM/YYYY', 'YYYY-MM-DD HH:MM:SS') para date.

    Datas inválidas ou vazias retornam None (nunca inventadas).
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    texto = str(valor).strip()
    if not texto or texto.startswith("0001-01-01") or texto == "00/00/0000":
        return None

    formatos = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )
    # Trata sufixo ISO com timezone
    if "T" in texto and (texto.endswith("Z") or "+" in texto[10:] or "-" in texto[10:]):
        try:
            return datetime.fromisoformat(texto).date()
        except ValueError:
            pass

    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue

    return None


def parse_datetime_br(valor: str | None) -> datetime | None:
    """Converte timestamp 'YYYY-MM-DD HH:MM:SS' ou ISO 8601 para datetime com fuso America/Sao_Paulo."""
    if not valor:
        return None
    texto = valor.strip()
    if not texto:
        return None
    try:
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=FUSO_BRASIL)
        return dt.astimezone(FUSO_BRASIL)
    except ValueError:
        return None


def validar_cnpj(cnpj_digitos: str) -> bool:
    """Valida os dígitos verificadores de um CNPJ de 14 dígitos."""
    if len(cnpj_digitos) != 14 or len(set(cnpj_digitos)) == 1 or not cnpj_digitos.isdigit():
        return False

    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_1 = sum(int(d) * p for d, p in zip(cnpj_digitos[:12], pesos_1))
    resto_1 = soma_1 % 11
    dv_1 = 0 if resto_1 < 2 else 11 - resto_1

    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_2 = sum(int(d) * p for d, p in zip(cnpj_digitos[:13], pesos_2))
    resto_2 = soma_2 % 11
    dv_2 = 0 if resto_2 < 2 else 11 - resto_2

    return int(cnpj_digitos[12]) == dv_1 and int(cnpj_digitos[13]) == dv_2


def mascarar_documento_lgpd(documento: str | None) -> tuple[str | None, str]:
    """Sanitiza CPF/CNPJ conforme LGPD (skill normalizacao-e-entidades e ADR-003).

    Retorna `(documento_tratado, tipo_documento)`:
    - Se for CNPJ (14 dígitos), retorna apenas os 14 dígitos e `'CNPJ'` (ou `'CNPJ_INVALIDO'`).
    - Se for CPF completo (11 dígitos) ou parcialmente mascarado (`050.xxx.xxx-63`),
      retorna SEMPRE `'***.***.***-**'` e `'CPF_MASCARADO'`.
    - Se vazio/nulo, retorna `(None, 'AUSENTE')`.
    """
    if not documento:
        return None, "AUSENTE"

    texto = documento.strip()
    if not texto:
        return None, "AUSENTE"

    if _RE_CPF_FORMATADO.match(texto) or "x" in texto.lower() or "*" in texto:
        return "***.***.***-**", "CPF_MASCARADO"

    apenas_digitos = re.sub(r"\D", "", texto)
    if len(apenas_digitos) == 14:
        tipo = "CNPJ" if validar_cnpj(apenas_digitos) else "CNPJ_INVALIDO"
        return apenas_digitos, tipo

    if len(apenas_digitos) == 11:
        return "***.***.***-**", "CPF_MASCARADO"

    return "***.***.***-**", "DOCUMENTO_MASCARADO"
