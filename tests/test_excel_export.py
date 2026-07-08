import os
import sys
from io import BytesIO

from openpyxl import Workbook, load_workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from excel_export import build_rating_export_workbook, update_workbook_with_rating_summary


def test_build_rating_export_workbook():
    clips = [{
        "content_id": "1260029222",
        "content_name": "Example Movie",
        "clip_type": "momenttype_pro",
        "clip_id": "clip1",
        "clip_drive_link": "https://drive.google.com/file/d/abc/view",
        "genre_cms": "Drama",
        "description": "A key moment.",
    }]
    summary = {"1260029222::momenttype::pro::clip1": {"avg": 8.5, "count": 2}}

    data = build_rating_export_workbook(clips, summary)
    wb = load_workbook(BytesIO(data))
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    values = [cell.value for cell in ws[2]]
    assert "Avg User Rating" in headers
    assert values[headers.index("unique_clip_key")] == "1260029222::momenttype::pro::clip1"
    assert values[headers.index("Avg User Rating")] == 8.5
    assert values[headers.index("Rating Count")] == 2


def test_update_workbook_with_rating_summary(tmp_path):
    source = tmp_path / "source.xlsx"
    output = tmp_path / "output.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Example Gamma"
    ws.append(["content_id", "content_name", "output_set", "clip_id"])
    ws.append(["1260029222", "Example Movie", "Gamma", "clip1"])
    wb.save(source)

    summary = {"1260029222::momenttype::pro::clip1": {"avg": 9.0, "count": 3}}
    updated = update_workbook_with_rating_summary(source, output, summary)

    assert updated == 1
    out_wb = load_workbook(output)
    out_ws = out_wb.active
    headers = [cell.value for cell in out_ws[1]]
    values = [cell.value for cell in out_ws[2]]
    assert values[headers.index("Unique Clip Key")] == "1260029222::momenttype::pro::clip1"
    assert values[headers.index("Avg User Rating")] == 9.0
    assert values[headers.index("Rating Count")] == 3
