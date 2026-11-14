"""各種文件格式 → 統一的 ``LoadedDocument``（文字片段＋表格，皆保留來源位置）。

支援：.txt／.md（含 Markdown pipe table）、.csv、.pdf（pypdf，逐頁文字）、
.docx（python-docx，段落＋表格）、.xlsx（openpyxl，每個工作表視為一張表）。

限制（MVP）：PDF 只取文字層（layout 模式，逐行），不做 OCR；PDF 中的表格只有在
文字層保留 ``|`` 或 Tab 分隔時才會被規則抽取器辨識成表格，其餘交給 LLMFactExtractor。
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILE_BYTES = 20 * 1024 * 1024
SUPPORTED_SUFFIXES = (".txt", ".md", ".csv", ".pdf", ".docx", ".xlsx")


class DocumentLoadError(ValueError):
    pass


@dataclass(frozen=True)
class TextSegment:
    page: int | None
    locator: str
    text: str


@dataclass
class Table:
    page: int | None
    locator: str  # 表格本身的位置，例如 "table 1" 或 "sheet 活動"
    header: list[str]
    rows: list[list[str]]
    row_locators: list[str] = field(default_factory=list)

    def row_text(self, index: int) -> str:
        """回傳該列的原文（用於 EvidenceSpan.source_text）。"""
        return " | ".join(self.rows[index])


@dataclass
class LoadedDocument:
    document_id: str  # 檔案內容 SHA-256，同內容 → 同 id，可用於版本比對
    file_name: str
    segments: list[TextSegment] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)

    def contains_text(self, text: str) -> bool:
        """供 LLM 抽取結果驗證引文確實出現在文件中。"""
        needle = _normalize_ws(text)
        if not needle:
            return False
        haystacks = [s.text for s in self.segments]
        for t in self.tables:
            haystacks.append(" | ".join(t.header))
            haystacks.extend(t.row_text(i) for i in range(len(t.rows)))
        return any(needle in _normalize_ws(h) for h in haystacks)


def load_document(file_path: str | Path) -> LoadedDocument:
    path = Path(file_path)
    if not path.is_file():
        raise DocumentLoadError(f"找不到檔案：{path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentLoadError(f"不支援的檔案格式 {suffix}；支援 {', '.join(SUPPORTED_SUFFIXES)}")
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise DocumentLoadError(f"檔案超過 {MAX_FILE_BYTES // (1024 * 1024)} MB 上限")
    return load_bytes(data, path.name)


def load_bytes(data: bytes, file_name: str) -> LoadedDocument:
    suffix = Path(file_name).suffix.lower()
    doc = LoadedDocument(document_id=hashlib.sha256(data).hexdigest(), file_name=file_name)
    if suffix in (".txt", ".md"):
        _load_plain_text(doc, _decode(data), page=None)
    elif suffix == ".csv":
        _load_csv(doc, _decode(data))
    elif suffix == ".pdf":
        _load_pdf(doc, data)
    elif suffix == ".docx":
        _load_docx(doc, data)
    elif suffix == ".xlsx":
        _load_xlsx(doc, data)
    else:
        raise DocumentLoadError(f"不支援的檔案格式 {suffix}")
    return doc


# ---------------------------------------------------------------- helpers

def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "big5", "cp950"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentLoadError("無法判斷文字編碼（請使用 UTF-8）")


def _require(module: str, package: str):
    try:
        return __import__(module)
    except ImportError as exc:  # pragma: no cover - 依安裝環境而定
        raise DocumentLoadError(f"讀取此格式需要安裝 {package}（pip install {package}）") from exc


def _clean_row(cells) -> list[str]:
    return [_normalize_ws("" if c is None else str(c)) for c in cells]


def _add_table(doc: LoadedDocument, page: int | None, locator: str,
               rows: list[list[str]], row_locators: list[str]):
    """第一個非空列視為表頭；全空列丟掉。"""
    pairs = [(r, loc) for r, loc in zip(rows, row_locators) if any(c for c in r)]
    if len(pairs) < 2:
        return
    (header, _), body = pairs[0], pairs[1:]
    width = len(header)
    doc.tables.append(Table(
        page=page, locator=locator, header=header,
        rows=[(r + [""] * width)[:width] for r, _ in body],
        row_locators=[loc for _, loc in body],
    ))


_PIPE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _split_table_line(line: str) -> list[str] | None:
    if "|" in line:
        cells = line.strip().strip("|").split("|")
    elif "\t" in line:
        cells = line.split("\t")
    else:
        return None
    cells = _clean_row(cells)
    return cells if len(cells) >= 2 else None


def _load_plain_text(doc: LoadedDocument, text: str, page: int | None):
    """一般文字逐行成為 segment；連續的 pipe／Tab 行組成表格。"""
    prefix = f"page {page} " if page is not None else ""
    pending_rows: list[list[str]] = []
    pending_locs: list[str] = []

    def flush():
        if pending_rows:
            _add_table(doc, page, f"{prefix}table {len(doc.tables) + 1}",
                       list(pending_rows), list(pending_locs))
            pending_rows.clear()
            pending_locs.clear()

    for line_no, line in enumerate(text.splitlines(), start=1):
        if _PIPE_SEPARATOR.match(line) and pending_rows:
            continue
        cells = _split_table_line(line)
        if cells is not None:
            pending_rows.append(cells)
            pending_locs.append(f"{prefix}line {line_no}")
            continue
        flush()
        if line.strip():
            doc.segments.append(TextSegment(page, f"{prefix}line {line_no}", line.strip()))
    flush()


def _load_csv(doc: LoadedDocument, text: str):
    rows = [_clean_row(r) for r in csv.reader(io.StringIO(text))]
    _add_table(doc, None, "table 1", rows, [f"row {i}" for i in range(1, len(rows) + 1)])


def _load_pdf(doc: LoadedDocument, data: bytes):
    pypdf = _require("pypdf", "pypdf")
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise DocumentLoadError(f"PDF 無法讀取：{type(exc).__name__}") from exc
    if reader.is_encrypted:
        raise DocumentLoadError("不支援加密的 PDF")
    for page_no, page in enumerate(reader.pages, start=1):
        # layout 模式保留行與欄位對齊；預設模式對某些 PDF（如 Google 文件匯出）會一字一行
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            text = page.extract_text() or ""
        text = "\n".join(re.sub(r" {3,}", "   ", line).rstrip() for line in text.splitlines())
        _load_plain_text(doc, text, page=page_no)


def _load_docx(doc: LoadedDocument, data: bytes):
    docx = _require("docx", "python-docx")
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentLoadError(f"Word 檔無法讀取：{type(exc).__name__}") from exc
    for i, para in enumerate(document.paragraphs, start=1):
        if para.text.strip():
            doc.segments.append(TextSegment(None, f"paragraph {i}", para.text.strip()))
    for t_no, table in enumerate(document.tables, start=1):
        rows = [_clean_row(cell.text for cell in row.cells) for row in table.rows]
        _add_table(doc, None, f"table {t_no}", rows,
                   [f"table {t_no} row {r}" for r in range(1, len(rows) + 1)])


def _load_xlsx(doc: LoadedDocument, data: bytes):
    openpyxl = _require("openpyxl", "openpyxl")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise DocumentLoadError(f"Excel 檔無法讀取：{type(exc).__name__}") from exc
    try:
        for ws in wb.worksheets:
            rows = [_clean_row(_xlsx_cell(c) for c in row) for row in ws.iter_rows(values_only=True)]
            _add_table(doc, None, f"sheet {ws.title}", rows,
                       [f"sheet {ws.title} row {r}" for r in range(1, len(rows) + 1)])
    finally:
        wb.close()


def _xlsx_cell(value):
    """Excel 時間格（datetime.time）轉成 HH:MM，整數浮點去掉 .0。"""
    if value is None:
        return ""
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return f"{value.hour:02d}:{value.minute:02d}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return value
