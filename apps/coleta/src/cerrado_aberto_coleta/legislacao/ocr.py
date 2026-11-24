"""Pipeline híbrido de extração de texto de PDFs de legislação (`pdfplumber` + Tesseract OCR — ADR-004).

Comportamento seguro:
1. Tenta extração textual nativa via `pdfplumber` sem custo.
2. Se a média de caracteres úteis por página for < 50 (PDF escaneado), procura o binário
   open-source `tesseract` (lang='por') e renderiza as páginas via `pypdfium2`.
3. Se `tesseract` não estiver instalado no ambiente, preserva o PDF original, nunca falha
   nem inventa texto, e marca `status_ocr = 'PENDENTE_OCR'` + `requer_revisao_humana = True`.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_MIN_CHARS_NATIVO_POR_PAGINA = 50


@dataclass(frozen=True)
class ResultadoExtracaoPDF:
    texto_extraido: str | None
    status_ocr: str  # 'TEXTO_NATIVO_PDF', 'OCR_CONCLUIDO', 'PENDENTE_OCR'
    extraido_por_ocr: bool
    ocr_engine_versao: str | None
    ocr_confianca_media: float | None
    requer_revisao_humana: bool
    motivo_revisao_humana: str | None
    total_paginas: int


def localizar_tesseract() -> str | None:
    """Retorna o caminho executável do Tesseract OCR se instalado no sistema."""
    no_path = shutil.which("tesseract")
    if no_path:
        return no_path
    for candidato in (
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ):
        if candidato.exists():
            return str(candidato)
    return None


def extrair_texto_pdf_hibrido(caminho_pdf: Path) -> ResultadoExtracaoPDF:
    """Extrai texto de um PDF com pdfplumber e fallback automático para Tesseract OCR (`por`)."""
    paginas_texto: list[str] = []
    with pdfplumber.open(str(caminho_pdf)) as pdf:
        total_paginas = len(pdf.pages)
        for pagina in pdf.pages:
            paginas_texto.append((pagina.extract_text() or "").strip())

    texto_nativo = "\n\n".join(p for p in paginas_texto if p).strip()
    media_chars = len(texto_nativo) / max(1, total_paginas)

    if media_chars >= _MIN_CHARS_NATIVO_POR_PAGINA:
        texto_limpo = _RE_CPF.sub("***.***.***-**", texto_nativo)
        return ResultadoExtracaoPDF(
            texto_extraido=texto_limpo,
            status_ocr="TEXTO_NATIVO_PDF",
            extraido_por_ocr=False,
            ocr_engine_versao=None,
            ocr_confianca_media=100.0,
            requer_revisao_humana=False,
            motivo_revisao_humana=None,
            total_paginas=total_paginas,
        )

    # PDF escaneado sem camada de texto -> tentar Tesseract OCR local
    tesseract_bin = localizar_tesseract()
    if not tesseract_bin:
        return ResultadoExtracaoPDF(
            texto_extraido=None,
            status_ocr="PENDENTE_OCR",
            extraido_por_ocr=False,
            ocr_engine_versao=None,
            ocr_confianca_media=None,
            requer_revisao_humana=True,
            motivo_revisao_humana=(
                "PDF digitalizado sem camada de texto nativa; instale Tesseract OCR (por) para extrair o texto integral."
            ),
            total_paginas=total_paginas,
        )

    import pypdfium2 as pdfium  # import tardio apenas quando OCR é executado

    versao_proc = subprocess.run(
        [tesseract_bin, "--version"], capture_output=True, text=True, check=False, timeout=10
    )
    versao_ocr = (versao_proc.stdout.splitlines()[0].strip() if versao_proc.stdout else "tesseract")[:64]

    doc = pdfium.PdfDocument(str(caminho_pdf))
    partes_ocr: list[str] = []
    for idx in range(len(doc)):
        pagina = doc[idx]
        bitmap = pagina.render(scale=2.0)
        pil_img = bitmap.to_pil()
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        proc = subprocess.run(
            [tesseract_bin, "stdin", "stdout", "-l", "por", "--psm", "6"],
            input=buf.getvalue(),
            capture_output=True,
            check=False,
            timeout=60,
        )
        if proc.returncode == 0:
            partes_ocr.append(proc.stdout.decode("utf-8", errors="replace").strip())

    texto_ocr = _RE_CPF.sub("***.***.***-**", "\n\n".join(p for p in partes_ocr if p).strip())
    baixa_densidade = len(texto_ocr) < _MIN_CHARS_NATIVO_POR_PAGINA
    return ResultadoExtracaoPDF(
        texto_extraido=texto_ocr or None,
        status_ocr="OCR_CONCLUIDO" if texto_ocr else "PENDENTE_OCR",
        extraido_por_ocr=bool(texto_ocr),
        ocr_engine_versao=versao_ocr,
        ocr_confianca_media=None,
        requer_revisao_humana=True,
        motivo_revisao_humana=(
            "Texto extraído automaticamente por OCR com baixa densidade — recomenda-se conferência do PDF."
            if baixa_densidade
            else "Texto extraído automaticamente por OCR (Tesseract por) — confira sempre o PDF oficial."
        ),
        total_paginas=total_paginas,
    )
