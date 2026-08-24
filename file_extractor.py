# -*- coding: utf-8 -*-
"""
첨부파일 텍스트 추출 모듈

나라장터 공고에 붙는 첨부파일(제안요청서, 규격서 등)은 보통 HWP/HWPX/PDF/DOCX/ZIP 형태입니다.
여기서는 "면접" 같은 특정 단어가 본문에 있는지만 확인하면 되므로,
완벽한 서식 보존보다는 "최대한 많은 텍스트를 뽑아내는 것"을 목표로 합니다.

지원 형식: .hwp, .hwpx, .pdf, .docx, .zip (zip 안에 위 형식이 있으면 재귀적으로 처리)
"""
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

try:
    import olefile
    HAS_OLEFILE = True
except ImportError:
    HAS_OLEFILE = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def extract_from_hwp(file_bytes: bytes) -> str:
    """
    HWP(구 버전, OLE 구조) 파일에서 텍스트 추출.
    완벽하진 않지만 PrvText(미리보기 텍스트)와 BodyText 스트림에서
    한글/영문/숫자 위주로 텍스트를 긁어옵니다. 키워드 검색 용도로는 충분합니다.
    """
    if not HAS_OLEFILE:
        return ""
    try:
        ole = olefile.OleFileIO(io.BytesIO(file_bytes))
        if ole.exists("EncryptedPackage"):
            return ""  # 암호화된 파일은 추출 불가

        text_parts = []
        if ole.exists("PrvText"):
            try:
                raw = ole.openstream("PrvText").read()
                decoded = raw.decode("utf-16-le", errors="ignore").replace("\x00", "")
                if decoded.strip():
                    text_parts.append(decoded)
            except Exception:
                pass

        i = 0
        while ole.exists(f"BodyText/Section{i}"):
            try:
                raw = ole.openstream(f"BodyText/Section{i}").read()
                decoded = raw.decode("utf-16-le", errors="ignore")
                readable = re.findall(r"[\uAC00-\uD7A3a-zA-Z0-9\s.,!?()\[\]/-]+", decoded)
                text_parts.extend(readable)
            except Exception:
                pass
            i += 1

        ole.close()
        return "\n".join(text_parts)
    except Exception:
        return ""


def extract_from_hwpx(file_bytes: bytes) -> str:
    """HWPX(신 버전, ZIP+XML 구조) 파일에서 텍스트 추출."""
    try:
        text_parts = []
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            section_files = sorted(
                n for n in zf.namelist()
                if n.startswith("Contents/section") and n.endswith(".xml")
            )
            for name in section_files:
                try:
                    content = zf.read(name).decode("utf-8", errors="ignore")
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            text_parts.append(elem.text.strip())
                except Exception:
                    continue
        return "\n".join(text_parts)
    except Exception:
        return ""


def extract_from_pdf(file_bytes: bytes) -> str:
    """PDF에서 페이지별 텍스트 추출 (이미지 스캔본은 텍스트가 없을 수 있음)."""
    if not HAS_PYPDF:
        return ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = []
        for page in reader.pages:
            try:
                t = page.extract_text()
                if t:
                    parts.append(t)
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""


def extract_from_docx(file_bytes: bytes) -> str:
    """DOCX 문단 + 표 텍스트 추출."""
    if not HAS_DOCX:
        return ""
    try:
        doc = Document(io.BytesIO(file_bytes))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        parts.append(cell.text.strip())
        return "\n".join(parts)
    except Exception:
        return ""


def _select_best_from_zip(names):
    """ZIP 안에 여러 파일이 있으면 제안요청서/과업지시서 > hwp/hwpx > pdf/docx 순으로 하나 고름."""
    valid = [n for n in names if not n.endswith("/") and not os.path.basename(n).startswith(".")]
    for n in valid:
        base = os.path.basename(n)
        if "제안요청서" in base or "과업지시서" in base:
            return n
    for n in valid:
        if n.lower().endswith((".hwp", ".hwpx")):
            return n
    for n in valid:
        if n.lower().endswith((".pdf", ".docx")):
            return n
    return None


def extract_from_zip(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            best = _select_best_from_zip(zf.namelist())
            if not best:
                return ""
            inner_bytes = zf.read(best)
            return extract_text(inner_bytes, best)
    except Exception:
        return ""


def extract_text(file_bytes: bytes, filename: str) -> str:
    """파일 확장자에 따라 알맞은 추출 함수로 분기."""
    ext = Path(filename).suffix.lower()
    if ext == ".hwp":
        return extract_from_hwp(file_bytes)
    if ext == ".hwpx":
        return extract_from_hwpx(file_bytes)
    if ext == ".pdf":
        return extract_from_pdf(file_bytes)
    if ext == ".docx":
        return extract_from_docx(file_bytes)
    if ext == ".zip":
        return extract_from_zip(file_bytes)
    return ""


def download_and_extract(url: str, filename: str = "") -> str:
    """
    URL에서 파일을 내려받아 텍스트를 추출합니다.
    실패하면 빈 문자열을 반환합니다 (호출부에서 "추출 실패"로 간주해 금액 기준으로 대체 처리).
    """
    if not url:
        return ""
    if not filename:
        filename = os.path.basename(url.split("?")[0])
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        text = extract_text(resp.content, filename)
        print(f"    [첨부파일 처리] {filename}: {len(resp.content)}바이트 다운로드, 텍스트 {len(text)}자 추출")
        return text
    except Exception as e:
        print(f"    [첨부파일 다운로드 실패] {filename}: {e}")
        return ""


def contains_keyword(text: str, keyword: str) -> bool:
    if not text:
        return False
    return keyword in text
