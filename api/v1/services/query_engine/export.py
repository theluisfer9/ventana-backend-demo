"""
Generacion de reportes CSV, Excel y PDF para consultas del Query Builder.

Excel y PDF se agrupan por departamento (un archivo por depto) y por municipio
(una hoja/seccion por municipio), entregados dentro de un ZIP.
CSV se entrega completo en streaming.
"""
from io import BytesIO, StringIO
from datetime import datetime
from collections import defaultdict
from collections.abc import Generator
import csv
import zipfile

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell import WriteOnlyCell
from fpdf import FPDF


# ── Helpers internos ────────────────────────────────────────────────

_GEO_DEPTO_KEYWORDS = ("departamento", "depto", "dpto", "department", "nombre_departamento", "nom_depto")
_GEO_MUNI_KEYWORDS = ("municipio", "muni", "municipality", "nombre_municipio", "nom_muni")


def _normalize_export_value(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("latin-1", errors="replace")
    return value


def _sanitize_for_pdf(text) -> str:
    """Remove characters not supported by Helvetica (latin-1 only)."""
    s = str(text) if text is not None else ""
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _find_geo_key(columns_meta: list[dict], keywords: tuple[str, ...]) -> str | None:
    """Encuentra la key de una columna geo en columns_meta.

    Prefiere columnas que NO contengan 'codigo'/'codigo' para usar el nombre
    descriptivo en vez del codigo numerico al agrupar.
    """
    candidates = []
    for c in columns_meta:
        name = c["column_name"].lower()
        if any(kw in name for kw in keywords):
            candidates.append(c["column_name"])

    if not candidates:
        return None

    # Preferir la columna sin "codigo"
    for cand in candidates:
        if "codigo" not in cand.lower():
            return cand

    return candidates[0]


def _group_rows_by_geo(
    rows: list[dict],
    depto_key: str | None,
    muni_key: str | None,
) -> dict[str, dict[str, list[dict]]]:
    """Agrupa rows en {departamento: {municipio: [rows]}}."""
    tree: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        depto = (
            str(_normalize_export_value(row.get(depto_key, "Sin Departamento")))
            if depto_key
            else "Sin Departamento"
        )
        muni = (
            str(_normalize_export_value(row.get(muni_key, "Sin Municipio")))
            if muni_key
            else "Sin Municipio"
        )
        tree[depto][muni].append(row)
    return tree


def _non_geo_meta(columns_meta: list[dict], depto_key: str | None, muni_key: str | None) -> tuple[list[str], list[str]]:
    """Retorna headers y keys excluyendo las columnas geo de agrupacion."""
    skip = {k for k in (depto_key, muni_key) if k}
    headers = [c["label"] for c in columns_meta if c["column_name"] not in skip]
    keys = [c["column_name"] for c in columns_meta if c["column_name"] not in skip]
    return headers, keys


# ── Estilos compartidos Excel ───────────────────────────────────────

_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
_CELL_ALIGN = Alignment(vertical="center", wrap_text=True)


# ── CSV (streaming por chunks) ───────────────────────────────────────

_CSV_CHUNK_SIZE = 5000


def generate_csv_streaming(rows: list[dict], columns_meta: list[dict]) -> Generator[bytes, None, None]:
    """Genera CSV en chunks para StreamingResponse. No carga todo en RAM."""
    headers = [c["label"] for c in columns_meta]
    keys = [c["column_name"] for c in columns_meta]

    # BOM + header
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    yield b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")

    # Datos en chunks
    for i in range(0, len(rows), _CSV_CHUNK_SIZE):
        chunk_buf = StringIO()
        chunk_writer = csv.writer(chunk_buf, lineterminator="\n")
        for row in rows[i:i + _CSV_CHUNK_SIZE]:
            chunk_writer.writerow(
                [_normalize_export_value(row.get(k, "")) for k in keys]
            )
        yield chunk_buf.getvalue().encode("utf-8")


# ── Excel (ZIP: un xlsx por departamento, una hoja por municipio) ───

def _write_excel_sheet(ws, headers: list[str], keys: list[str], rows: list[dict]):
    """Escribe headers + datos en una hoja ya creada (modo normal)."""
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN
        cell.border = _THIN_BORDER

    for row_idx, row in enumerate(rows, 2):
        for col_idx, key in enumerate(keys, 1):
            cell = ws.cell(
                row=row_idx,
                column=col_idx,
                value=_normalize_export_value(row.get(key, "")),
            )
            cell.border = _THIN_BORDER
            cell.alignment = _CELL_ALIGN

    # Auto-width (sample first 100 rows)
    for col_idx, key in enumerate(keys, 1):
        max_len = len(headers[col_idx - 1])
        for row in rows[:100]:
            val = _normalize_export_value(row.get(key, ""))
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 60)

    ws.freeze_panes = "A2"


def _write_excel_sheet_fast(ws, headers: list[str], keys: list[str], rows: list[dict]):
    """Escribe headers + datos usando write_only mode (optimizado para muchas filas)."""
    header_cells = []
    for h in headers:
        cell = WriteOnlyCell(ws, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN
        cell.border = _THIN_BORDER
        header_cells.append(cell)
    ws.append(header_cells)

    for row in rows:
        data_cells = []
        for key in keys:
            cell = WriteOnlyCell(ws, value=row.get(key, ""))
            cell.border = _THIN_BORDER
            cell.alignment = _CELL_ALIGN
            data_cells.append(cell)
        ws.append(data_cells)

    # Auto-width (sample first 100 rows)
    for col_idx, key in enumerate(keys, 1):
        max_len = len(headers[col_idx - 1])
        for row in rows[:100]:
            val = row.get(key, "")
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 60)

    ws.freeze_panes = "A2"


def generate_excel_zip(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera ZIP con un .xlsx por departamento; cada municipio es una hoja."""
    depto_key = _find_geo_key(columns_meta, _GEO_DEPTO_KEYWORDS)
    muni_key = _find_geo_key(columns_meta, _GEO_MUNI_KEYWORDS)
    tree = _group_rows_by_geo(rows, depto_key, muni_key)
    headers, keys = _non_geo_meta(columns_meta, depto_key, muni_key)

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for depto_name in sorted(tree.keys()):
            municipios = tree[depto_name]
            wb = Workbook(write_only=True)

            for muni_name in sorted(municipios.keys()):
                safe_sheet = muni_name[:31] or "Sin Municipio"
                ws = wb.create_sheet(title=safe_sheet)
                _write_excel_sheet_fast(ws, headers, keys, municipios[muni_name])

            xlsx_buf = BytesIO()
            wb.save(xlsx_buf)
            safe_depto = "".join(c if c.isalnum() or c in " _-" else "_" for c in depto_name).strip()
            zf.writestr(f"{safe_depto}.xlsx", xlsx_buf.getvalue())

    zip_buf.seek(0)
    return zip_buf


_CHUNK_SIZE = 5_000


def generate_excel_chunked_zip(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera ZIP con excels de max 10K filas cada uno, sin agrupar por geo."""
    headers = [c["label"] for c in columns_meta]
    keys = [c["column_name"] for c in columns_meta]

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        total_chunks = max(1, (len(rows) + _CHUNK_SIZE - 1) // _CHUNK_SIZE)
        for chunk_idx in range(total_chunks):
            start = chunk_idx * _CHUNK_SIZE
            chunk_rows = rows[start:start + _CHUNK_SIZE]

            wb = Workbook(write_only=True)
            ws = wb.create_sheet(title=title[:31])
            _write_excel_sheet_fast(ws, headers, keys, chunk_rows)

            xlsx_buf = BytesIO()
            wb.save(xlsx_buf)

            if total_chunks == 1:
                fname = f"{title}.xlsx"
            else:
                fname = f"{title}_parte_{chunk_idx + 1}.xlsx"
            zf.writestr(fname, xlsx_buf.getvalue())

    zip_buf.seek(0)
    return zip_buf


def generate_pdf_chunked_zip(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera ZIP con PDFs de max 10K filas cada uno, sin agrupar por geo.

    Usa formato listado estilo beneficiarios.
    """
    headers = [c["label"] for c in columns_meta]
    keys = [c["column_name"] for c in columns_meta]

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        total_chunks = max(1, (len(rows) + _CHUNK_SIZE - 1) // _CHUNK_SIZE)
        for chunk_idx in range(total_chunks):
            start = chunk_idx * _CHUNK_SIZE
            chunk_rows = rows[start:start + _CHUNK_SIZE]

            chunk_title = title if total_chunks == 1 else f"{title} - Parte {chunk_idx + 1}"
            pdf = _QueryPDF(chunk_title, orientation="P", unit="mm", format="A4")
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()

            _write_pdf_simple_header(pdf, chunk_title)
            _write_pdf_listing_rows(pdf, headers, keys, chunk_rows)

            pdf_buf = BytesIO()
            pdf.output(pdf_buf)

            if total_chunks == 1:
                fname = f"{title}.pdf"
            else:
                fname = f"{title}_parte_{chunk_idx + 1}.pdf"
            zf.writestr(fname, pdf_buf.getvalue())

    zip_buf.seek(0)
    return zip_buf


# Mantener la funcion original para uso simple (sin agrupacion)
def generate_excel(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera Excel (.xlsx) simple con estilos, bordes y freeze panes."""
    headers = [c["label"] for c in columns_meta]
    keys = [c["column_name"] for c in columns_meta]

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title=title[:31])
    _write_excel_sheet_fast(ws, headers, keys, rows)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ── PDF (ZIP: un pdf por departamento, separado por municipio) ──────

class _QueryPDF(FPDF):
    def __init__(self, report_title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._report_title = report_title

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self._report_title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.cell(
            0, 6,
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            new_x="LMARGIN", new_y="NEXT", align="C",
        )
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")


def _calc_col_widths(headers: list[str], keys: list[str], rows: list[dict]) -> list[float]:
    """Calcula anchos proporcionales para PDF."""
    usable_width = 277
    sample = rows[:100]
    raw_widths = []
    for i, key in enumerate(keys):
        max_len = len(headers[i])
        for row in sample:
            val = str(_normalize_export_value(row.get(key, "")))
            max_len = max(max_len, min(len(val), 35))
        raw_widths.append(max_len)

    total_raw = sum(raw_widths) or 1
    col_widths = [max(w / total_raw * usable_width, 15) for w in raw_widths]
    scale = usable_width / sum(col_widths)
    return [w * scale for w in col_widths]


def _write_pdf_table_header(pdf: FPDF, headers: list[str], col_widths: list[float]):
    """Escribe la fila de encabezados de tabla en el PDF."""
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(31, 78, 121)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        label = h[:20] + "..." if len(h) > 20 else h
        pdf.cell(col_widths[i], 8, label, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(0, 0, 0)


def _write_pdf_rows(pdf: FPDF, keys: list[str], col_widths: list[float], rows: list[dict], start_idx: int = 0):
    """Escribe filas de datos en el PDF."""
    for idx, row in enumerate(rows, start_idx):
        if idx % 2 == 1:
            pdf.set_fill_color(235, 241, 247)
        else:
            pdf.set_fill_color(255, 255, 255)

        for i, key in enumerate(keys):
            val = str(_normalize_export_value(row.get(key, "")))
            if len(val) > 35:
                val = val[:32] + "..."
            pdf.cell(col_widths[i], 7, val, border=1, fill=True, align="C")
        pdf.ln()


# ── PDF formato listado (estilo beneficiarios) ──────────────────────


def _write_pdf_section_header(
    pdf: FPDF,
    depto_name: str,
    muni_name: str,
    title: str = "Consulta",
):
    """Escribe header de seccion estilo beneficiarios con depto/muni."""
    # Linea superior: TITULO - MUNICIPIO DE X - DEPARTAMENTO DE Y
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    top_line = _sanitize_for_pdf(f"{title.upper()} - MUNICIPIO DE {muni_name.upper()} - DEPARTAMENTO DE {depto_name.upper()}")
    pdf.cell(0, 5, top_line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Titulo azul bold subrayado
    pdf.set_font("Helvetica", "BU", 11)
    pdf.set_text_color(31, 78, 121)
    detail_line = _sanitize_for_pdf(
        f"LISTADO DE REGISTROS IDENTIFICADOS EN EL "
        f"MUNICIPIO DE {muni_name.upper()} DEL DEPARTAMENTO DE {depto_name.upper()}"
    )
    pdf.multi_cell(0, 6, detail_line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _write_pdf_simple_header(pdf: FPDF, title: str):
    """Escribe header simple cuando no hay agrupacion geografica."""
    pdf.set_font("Helvetica", "BU", 11)
    pdf.set_text_color(31, 78, 121)
    pdf.multi_cell(0, 6, _sanitize_for_pdf(title.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _parse_familia(familia_str: str) -> list[dict]:
    """Parsea el campo familia: 'Nombre, Parentesco, CUI | ...' -> [{nombre, parentesco, cui}]."""
    if not familia_str:
        return []
    members = []
    for entry in familia_str.split(" | "):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.rsplit(", ", 2)
        if len(parts) == 3:
            members.append({"nombre": parts[0].strip(), "parentesco": parts[1].strip(), "cui": parts[2].strip()})
        elif len(parts) == 2:
            members.append({"nombre": parts[0].strip(), "parentesco": parts[1].strip(), "cui": ""})
        else:
            members.append({"nombre": entry, "parentesco": "", "cui": ""})
    return members


def _format_cui(cui) -> str:
    """Formatea CUI/DPI para mostrar."""
    cui_str = str(_normalize_export_value(cui) if cui else "")
    if not cui_str or cui_str in ("-1", "0", ""):
        return "SIN CUI REGISTRADO"
    return cui_str


def _write_pdf_listing_rows(
    pdf: FPDF,
    headers: list[str],
    keys: list[str],
    rows: list[dict],
):
    """Renderiza filas estilo beneficiarios con familia desglosada.

    Si el row tiene campo 'familia', renderiza:
      TOTAL DE HOGARES IDENTIFICADOS: N
      1. NOMBRE JEFE, jefa o jefe del hogar DPI: xxx
         * MIEMBRO, parentesco DPI: xxx
         * MIEMBRO, parentesco DPI: xxx

    Si no tiene 'familia', renderiza formato listado con campos.
    """
    has_familia = any("familia" in row for row in rows[:5])

    # Campos a excluir del detalle (ya se muestran en el formato familia)
    familia_skip = {
        "familia", "nombre_jefe_hogar", "cui_jefe_hogar", "sexo_jefe_hogar",
        "celular_jefe_hogar", "nombre_madre", "cui_madre", "sexo_madre",
        "celular_madre", "nombre_otro_integrante", "cui_otro_integrante",
        "celular_otro_integrante", "parentesco_otro_integrante",
    }

    # Total
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(0, 0, 0)
    label = "TOTAL DE HOGARES IDENTIFICADOS" if has_familia else "TOTAL DE REGISTROS IDENTIFICADOS"
    pdf.cell(0, 6, f"{label}: {len(rows)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    for idx, row in enumerate(rows, start=1):
        if pdf.get_y() > pdf.h - 30:
            pdf.add_page()

        if has_familia:
            # ── Formato familia ──
            familia_str = str(_normalize_export_value(row.get("familia", "") or ""))
            members = _parse_familia(familia_str)
            jefe = members[0] if members else None
            integrantes = members[1:] if len(members) > 1 else []

            # Jefe del hogar bold
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 0, 0)
            if jefe:
                jefe_line = f"{idx}. {jefe['nombre'].upper()}, {jefe['parentesco']} DPI: {_format_cui(jefe['cui'])}"
            else:
                nombre = str(_normalize_export_value(row.get("nombre_jefe_hogar", "") or "")).upper()
                cui = _format_cui(row.get("cui_jefe_hogar"))
                jefe_line = f"{idx}. {nombre}, jefa o jefe del hogar DPI: {cui}"
            pdf.multi_cell(0, 5, _sanitize_for_pdf(jefe_line), new_x="LMARGIN", new_y="NEXT")

            # Integrantes como bullets
            for member in integrantes:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(0, 0, 0)
                member_line = f"    *  {member['nombre'].upper()}, {member['parentesco']} DPI: {_format_cui(member['cui'])}"
                pdf.multi_cell(0, 5, _sanitize_for_pdf(member_line), new_x="LMARGIN", new_y="NEXT")

            # Campos adicionales seleccionados (excluyendo los de familia/geo)
            extra_fields = [(h, k) for h, k in zip(headers, keys) if k not in familia_skip]
            if extra_fields:
                parts = []
                for label_h, key in extra_fields:
                    val = str(_normalize_export_value(row.get(key, "") or ""))
                    if val:
                        parts.append(f"{label_h}: {val}")
                if parts:
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(8, 4, "", new_x="END")
                    pdf.multi_cell(0, 4, _sanitize_for_pdf("  |  ".join(parts)), new_x="LMARGIN", new_y="NEXT")

        else:
            # ── Formato listado generico ──
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 0, 0)

            first_val = _sanitize_for_pdf(str(_normalize_export_value(row.get(keys[0], "") or "")).upper())
            first_part = f"{idx}. {headers[0]}: {first_val}"
            if len(keys) > 1:
                second_val = _sanitize_for_pdf(str(_normalize_export_value(row.get(keys[1], "") or "")))
                first_part += f"  {headers[1]}: {second_val}"
            pdf.multi_cell(0, 5, first_part, new_x="LMARGIN", new_y="NEXT")

            remaining = list(zip(headers[2:], keys[2:]))
            for i in range(0, len(remaining), 2):
                chunk = remaining[i:i + 2]
                parts = []
                for label_h, key in chunk:
                    val = _sanitize_for_pdf(str(_normalize_export_value(row.get(key, "") or "")))
                    parts.append(f"{label_h}: {val}")
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(8, 5, "", new_x="END")
                pdf.multi_cell(0, 5, "  |  ".join(parts), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(1)


_PDF_ROWS_PER_DEPTO = 5_000


def generate_pdf_zip(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera ZIP con un .pdf por departamento, secciones por municipio.

    Usa formato listado estilo beneficiarios.
    Limita a _PDF_ROWS_PER_DEPTO filas por departamento.
    """
    depto_key = _find_geo_key(columns_meta, _GEO_DEPTO_KEYWORDS)
    muni_key = _find_geo_key(columns_meta, _GEO_MUNI_KEYWORDS)
    tree = _group_rows_by_geo(rows, depto_key, muni_key)
    headers, keys = _non_geo_meta(columns_meta, depto_key, muni_key)

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for depto_name in sorted(tree.keys()):
            municipios = tree[depto_name]

            pdf = _QueryPDF(
                f"{title} - {depto_name}",
                orientation="P", unit="mm", format="A4",
            )
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=20)

            depto_row_count = 0
            for muni_name in sorted(municipios.keys()):
                if depto_row_count >= _PDF_ROWS_PER_DEPTO:
                    break
                muni_rows = municipios[muni_name]
                remaining = _PDF_ROWS_PER_DEPTO - depto_row_count
                muni_rows = muni_rows[:remaining]
                depto_row_count += len(muni_rows)

                pdf.add_page()
                _write_pdf_section_header(pdf, depto_name, muni_name, title)
                _write_pdf_listing_rows(pdf, headers, keys, muni_rows)

            pdf_buf = BytesIO()
            pdf.output(pdf_buf)
            safe_depto = "".join(c if c.isalnum() or c in " _-" else "_" for c in depto_name).strip()
            zf.writestr(f"{safe_depto}.pdf", pdf_buf.getvalue())

    zip_buf.seek(0)
    return zip_buf


# Mantener la funcion original para uso simple
def generate_pdf(rows: list[dict], columns_meta: list[dict], title: str = "Consulta") -> BytesIO:
    """Genera PDF landscape con anchos calculados por columna."""
    headers = [c["label"] for c in columns_meta]
    keys = [c["column_name"] for c in columns_meta]

    max_cols = min(len(headers), 10)
    headers = headers[:max_cols]
    keys = keys[:max_cols]

    col_widths = _calc_col_widths(headers, keys, rows)

    pdf = _QueryPDF(title, orientation="L", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    _write_pdf_table_header(pdf, headers, col_widths)
    _write_pdf_rows(pdf, keys, col_widths, rows)

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
