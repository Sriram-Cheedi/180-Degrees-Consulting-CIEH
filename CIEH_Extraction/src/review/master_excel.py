"""Formatted Excel export of the final master columns."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def build_master_excel(master):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Master data"
    columns = master["columns"]

    def safe_value(value):
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    sheet.append(columns)
    for record in master["records"]:
        sheet.append([safe_value(record.get(column)) for column in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="244062")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 28
    for index, column in enumerate(columns, start=1):
        longest = max([len(column)] + [max((len(line) for line in str(record.get(column) or "").splitlines()), default=0) for record in master["records"]])
        width = min(65, max(16, longest + 3))
        sheet.column_dimensions[get_column_letter(index)].width = width
        for cells in sheet.iter_rows(min_row=2, min_col=index, max_col=index):
            cells[0].alignment = Alignment(vertical="top", wrap_text=True)
    for row in sheet.iter_rows(min_row=2):
        # Explicit height makes long wrapped values visible on first open.
        line_counts = []
        for cell in row:
            characters = max(1, int(sheet.column_dimensions[cell.column_letter].width) - 3)
            line_counts.append(sum(max(1, (len(line) + characters - 1) // characters)
                                   for line in str(cell.value or "").split("\n")))
        lines = max(line_counts, default=1)
        sheet.row_dimensions[row[0].row].height = min(409, max(20, lines * 16))
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()
