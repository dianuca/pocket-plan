"""Raport PDF din date curente, fără închiderea lunii."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


FONT_DIR = Path(__file__).parent / "assets" / "fonts"
pdfmetrics.registerFont(TTFont("PocketPlan", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("PocketPlan-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))


def build_monthly_report_pdf(context):
    output = BytesIO()
    month = context["selected_month"]
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=42, leftMargin=42,
                                 topMargin=42, bottomMargin=48, title=f"PocketPlan — Raport lunar {month}")
    body = ParagraphStyle("body", fontName="PocketPlan", fontSize=9, leading=13)
    heading = ParagraphStyle("heading", parent=body, fontName="PocketPlan-Bold",
                             fontSize=11, leading=15, spaceBefore=18, spaceAfter=8,
                             textColor=colors.black, keepWithNext=True)
    title = ParagraphStyle("title", parent=heading, fontSize=18, leading=24,
                           alignment=TA_CENTER, spaceBefore=0, spaceAfter=6)
    subtitle = ParagraphStyle("subtitle", parent=body, alignment=TA_CENTER, spaceAfter=14)
    column_header = ParagraphStyle("column-header", parent=body, fontName="PocketPlan-Bold")
    amount_style = ParagraphStyle("amount", parent=body, alignment=TA_RIGHT)
    total_style = ParagraphStyle("total", parent=body, fontName="PocketPlan-Bold")
    total_amount = ParagraphStyle("total-amount", parent=total_style, alignment=TA_RIGHT)

    def paragraph(value, style=body):
        return Paragraph(escape(str(value)), style)

    def money(value):
        return f"{value:.2f}".replace(".", ",") + " lei"

    story = [paragraph("RAPORT LUNAR", title),
             paragraph(f"PocketPlan | Luna: {month} | Moneda: lei", subtitle),
             paragraph(f"Perioada: {context['period_start']:%d.%m.%Y} – {context['period_end']:%d.%m.%Y}", subtitle),
             paragraph("Situație calculată din datele curente ale lunii. Raportul nu închide luna.")]

    def table(title, headers, rows, widths, empty, emphasize_last=False):
        story.append(paragraph(title, heading))
        rows = list(rows)
        if not rows:
            story.append(paragraph(empty))
            return
        data = [[paragraph(cell, column_header) for cell in headers]]
        for index, row in enumerate(rows):
            is_total = emphasize_last and index == len(rows) - 1
            data.append([
                paragraph(cell, (total_amount if is_total else amount_style)
                          if column == len(row) - 1 or str(cell).endswith(" lei")
                          else (total_style if is_total else body))
                for column, cell in enumerate(row)
            ])
        grid = LongTable(data, colWidths=[document.width * width for width in widths], repeatRows=1, hAlign="LEFT")
        grid.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black),
        ]))
        if emphasize_last:
            grid.setStyle(TableStyle([("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.black)]))
        story.append(grid)

    table("Rezumat", ["Indicator", "Sumă"], [
        ("Venituri", money(context["income"])),
        ("Cheltuieli fără rate", money(context["direct_expenses"])),
        ("Rate active", money(context["installment_total"])),
        ("Total cheltuieli (inclusiv rate)", money(context["expenses"])),
        ("Depuneri în economii", money(context["savings_deposits"])),
        ("Retrageri din economii", money(context["savings_withdrawals"])),
        ("Sold după cheltuieli și economii", money(context["balance"])),
        ("Buget personal rezervat, necheltuit", money(context["personal_reserved"])),
        ("Bani disponibili", money(context["unallocated_balance"])),
    ], [.65, .35], "", emphasize_last=True)
    table("Venituri", ["Data", "Sursă", "Sumă"],
          ((item.received_on.strftime("%d.%m.%Y"), item.source, money(item.amount)) for item in context["report_incomes"]),
          [.2, .5, .3], "Nu există venituri în această lună.")
    table("Cheltuieli", ["Data", "Denumire", "Categorie", "Sumă"],
          ((item.paid_on.strftime("%d.%m.%Y"), item.name + (" (Pentru mine)" if item.from_personal_budget else ""), item.get_category_display(), money(item.amount)) for item in context["report_expenses"]),
          [.18, .34, .22, .26], "Nu există cheltuieli în această lună.")
    table("Rate active", ["Denumire", "Sumă în perioadă", "Rate rămase"],
          ((item["name"], money(item["amount"]), item["remaining"]) for item in context["installment_items"]),
          [.45, .3, .25], "Nu există rate active în această lună.")
    story.append(paragraph("Ratele rămase sunt calculate înaintea primei scadențe din perioadă și nu confirmă plata."))
    table("Buget pentru mine", ["Indicator", "Sumă"], [
        ("Alocat", money(context["personal_allocated"])),
        ("Cheltuit pentru mine", money(context["personal_spent"])),
        ("Rămas din alocare", money(context["personal_remaining"])),
        ("Depășire", money(context["personal_overspent"])),
    ], [.65, .35], "")
    story.append(paragraph("Alocarea rezervă bani. Cheltuielile marcate «Pentru mine» sunt incluse o singură dată în tabelul și totalul cheltuielilor."))
    table("Transferuri în economii", ["Data", "Tip", "Descriere", "Sumă"],
          ((item.occurred_on.strftime("%d.%m.%Y"), item.get_kind_display(), item.description or "—", money(item.amount)) for item in context["report_transfers"]),
          [.18, .2, .36, .26], "Nu există transferuri în această lună.")
    story.extend([Spacer(1, 12), paragraph(f"Sold economii la sfârșitul lunii: {money(context['savings_balance'])}"),
                  paragraph(f"Deficit de recuperat până la zero: {money(context['savings_deficit'])}"),
                  paragraph("Bani disponibili = venituri − cheltuieli (inclusiv rate) − depuneri + retrageri − buget personal rezervat, necheltuit."),
                  paragraph("Rezerva personală = maximul dintre alocat − cheltuit pentru mine și zero.")])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("PocketPlan", 8)
        canvas.setFillColor(colors.black)
        canvas.setStrokeColor(colors.HexColor("#999999"))
        canvas.setLineWidth(0.4)
        canvas.line(42, 36, A4[0] - 42, 36)
        canvas.drawString(42, 24, f"PocketPlan | Raport {month}")
        canvas.drawRightString(A4[0] - 42, 24, f"Pagina {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
