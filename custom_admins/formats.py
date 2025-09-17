from import_export.formats.base_formats import Format
from tablib import Dataset
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

class PDF(Format):
    def get_title(self):
        return "pdf"

    def create_dataset(self, in_stream, **kwargs):
        return Dataset().load(in_stream, format='csv')

    def export_data(self, dataset, **kwargs):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        textobject = p.beginText(40, 800)
        textobject.setFont("Helvetica", 10)

        # headers
        headers = dataset.headers
        if headers:
            textobject.textLine(" | ".join(headers))
            textobject.textLine("-" * 80)

        # rows
        for row in dataset.dict:
            textobject.textLine(" | ".join([str(v) for v in row.values()]))

        p.drawText(textobject)
        p.showPage()
        p.save()

        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    def get_content_type(self):
        return "application/pdf"

    def get_extension(self):
        return "pdf"
