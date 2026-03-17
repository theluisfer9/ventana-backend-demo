"""
Generacion de reportes de beneficiarios en Excel y PDF.
"""
from io import BytesIO
from io import StringIO
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import re
import csv

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from fpdf import FPDF


# ── Columnas del reporte ─────────────────────────────────────────────

COLUMNS = [
    "ID Hogar",
    "CUI Jefe",
    "Nombre Jefe Hogar",
    "Sexo Jefe",
    "Departamento",
    "Municipio",
    "Lugar Poblado",
    "Area",
    "No. Personas",
    "IPM",
    "Clasif. IPM",
    "PMT",
    "Clasif. PMT",
]

EXCEL_ZIP_THRESHOLD = 10_000


def _sanitize_excel_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[\[\]\*:/\\\?]", " ", (value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned or fallback)[:31]


def _sanitize_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", (value or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    return cleaned or fallback


def _row(b: dict) -> list:
    """Convierte un beneficiario RSH a fila de reporte."""
    return [
        b.get("hogar_id", ""),
        b.get("cui_jefe_hogar", ""),
        b.get("nombre_completo", ""),
        "Femenino" if b.get("sexo_jefe_hogar") == "F" else "Masculino",
        b.get("departamento", ""),
        b.get("municipio", ""),
        b.get("lugar_poblado", ""),
        b.get("area", ""),
        b.get("numero_personas", 0),
        round(b.get("ipm_gt", 0), 4),
        b.get("ipm_gt_clasificacion", ""),
        round(b.get("pmt", 0), 4),
        b.get("pmt_clasificacion", ""),
    ]


# ── CSV ──────────────────────────────────────────────────────────────

def generate_csv(rows: list[dict]) -> BytesIO:
    """Genera un archivo .csv UTF-8 en memoria con los beneficiarios dados."""
    text_buffer = StringIO()
    writer = csv.writer(text_buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for beneficiario in rows:
        writer.writerow(_row(beneficiario))

    output = BytesIO(text_buffer.getvalue().encode("utf-8-sig"))
    output.seek(0)
    return output


# ── Excel ────────────────────────────────────────────────────────────

def generate_excel(rows: list[dict]) -> BytesIO:
    """Genera un archivo .xlsx en memoria con los beneficiarios dados."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Beneficiarios"

    # Estilos de header
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Escribir headers
    for col_idx, title in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Escribir datos
    for row_idx, beneficiario in enumerate(rows, 2):
        values = _row(beneficiario)
        for col_idx, value in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    # Auto-width
    for col_idx in range(1, len(COLUMNS) + 1):
        max_len = len(str(COLUMNS[col_idx - 1]))
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        adjusted = min(max_len + 4, 60)
        ws.column_dimensions[get_column_letter(col_idx)].width = adjusted

    # Congelar primera fila
    ws.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _populate_worksheet(ws, rows: list[dict]) -> None:
    """Escribe headers, filas y formato base a una hoja dada."""
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col_idx, title in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    for row_idx, beneficiario in enumerate(rows, 2):
        values = _row(beneficiario)
        for col_idx, value in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    for col_idx in range(1, len(COLUMNS) + 1):
        max_len = len(str(COLUMNS[col_idx - 1]))
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 60)

    ws.freeze_panes = "A2"


def _group_rows(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    grouped: dict[str, dict[str, list[dict]]] = {}
    for row in rows:
        depto = row.get("departamento", "Sin departamento") or "Sin departamento"
        muni = row.get("municipio", "Sin municipio") or "Sin municipio"
        grouped.setdefault(depto, {}).setdefault(muni, []).append(row)
    return grouped


def _group_rows_for_print(rows: list[dict]) -> dict[str, dict[str, dict[str, list[dict]]]]:
    grouped: dict[str, dict[str, dict[str, list[dict]]]] = {}
    for row in rows:
        depto = (row.get("departamento") or "Sin departamento").strip() or "Sin departamento"
        muni = (row.get("municipio") or "Sin municipio").strip() or "Sin municipio"
        comunidad = (row.get("comunidad") or row.get("lugar_poblado") or "Sin comunidad").strip() or "Sin comunidad"
        grouped.setdefault(depto, {}).setdefault(muni, {}).setdefault(comunidad, []).append(row)
    return grouped


def generate_excel_grouped_zip(rows: list[dict]) -> BytesIO:
    """
    Genera un ZIP con un workbook por departamento y una hoja por municipio.
    """
    grouped = _group_rows(rows)
    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for depto, municipios in sorted(grouped.items()):
            workbook = Workbook()
            default_sheet = workbook.active
            first_sheet = True

            for municipio, municipio_rows in sorted(municipios.items()):
                ws = default_sheet if first_sheet else workbook.create_sheet()
                ws.title = _sanitize_excel_name(municipio, "Municipio")
                _populate_worksheet(ws, municipio_rows)
                first_sheet = False

            workbook_buffer = BytesIO()
            workbook.save(workbook_buffer)
            workbook_buffer.seek(0)

            depto_code = rows and next(
                (
                    str(row.get("departamento_codigo", "")).strip()
                    for row in rows
                    if (row.get("departamento") or "Sin departamento") == depto
                ),
                "",
            )
            prefix = f"{depto_code}_" if depto_code else ""
            filename = f"{prefix}{_sanitize_filename(depto, 'departamento')}.xlsx"
            zip_file.writestr(filename, workbook_buffer.getvalue())

    zip_buffer.seek(0)
    return zip_buffer


# ── PDF ──────────────────────────────────────────────────────────────

class _BeneficiarioPDF(FPDF):
    """PDF landscape con header/footer personalizados."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Listado de Beneficiarios por Municipio y Comunidad", new_x="LMARGIN", new_y="NEXT", align="C")
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


def generate_pdf(rows: list[dict]) -> BytesIO:
    """Genera un archivo PDF portrait agrupado por municipio y comunidad."""
    pdf = _BeneficiarioPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    grouped = _group_rows_for_print(rows)

    for depto_index, (departamento, municipios) in enumerate(sorted(grouped.items())):
        if depto_index > 0:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(31, 78, 121)
        pdf.cell(0, 8, f"Departamento: {departamento}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        for municipio, comunidades in sorted(municipios.items()):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(55, 55, 55)
            pdf.cell(0, 7, f"Municipio: {municipio}", new_x="LMARGIN", new_y="NEXT")

            for comunidad, beneficiarios in sorted(comunidades.items()):
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(
                    0,
                    6,
                    f"Comunidad: {comunidad} ({len(beneficiarios)} beneficiarios)",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

                pdf.set_font("Helvetica", "", 8)
                for idx, beneficiario in enumerate(beneficiarios, start=1):
                    nombre = (beneficiario.get("nombre_completo") or "").strip() or "Sin nombre"
                    hogar_id = beneficiario.get("hogar_id", "")
                    cui = beneficiario.get("cui_jefe_hogar", "")
                    personas = beneficiario.get("numero_personas", 0)
                    area = (beneficiario.get("area") or "").strip()
                    ipm = round(beneficiario.get("ipm_gt", 0) or 0, 4)

                    line = (
                        f"{idx}. Hogar {hogar_id} | CUI {cui} | {nombre} | "
                        f"Personas: {personas} | Area: {area} | IPM: {ipm}"
                    )
                    pdf.multi_cell(pdf.epw, 5, line, new_x="LMARGIN", new_y="NEXT")

                pdf.ln(2)

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
