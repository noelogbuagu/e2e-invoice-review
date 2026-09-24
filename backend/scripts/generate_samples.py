import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import reportlab
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

CUSTOMER_NAME = "Plurobi B.V."
CUSTOMER_VAT_ID = "NL00449544B01"
CUSTOMER_ADDRESS = "Wibautstraat 131-D, 1091 GL Amsterdam, Netherlands"

LABELS = {
    "en": {
        "title": "INVOICE",
        "vendor": "Supplier",
        "customer": "Customer",
        "vat": "VAT number",
        "number": "Invoice number",
        "date": "Invoice date",
        "due": "Due date",
        "po": "Purchase order",
        "description": "Description",
        "quantity": "Quantity",
        "unit_price": "Unit price",
        "amount": "Amount",
        "subtotal": "Subtotal",
        "tax": "VAT 21%",
        "total": "Total",
    },
    "nl": {
        "title": "FACTUUR",
        "vendor": "Leverancier",
        "customer": "Klant",
        "vat": "BTW-nummer",
        "number": "Factuurnummer",
        "date": "Factuurdatum",
        "due": "Vervaldatum",
        "po": "Inkooporder",
        "description": "Omschrijving",
        "quantity": "Aantal",
        "unit_price": "Eenheidsprijs",
        "amount": "Bedrag",
        "subtotal": "Subtotaal",
        "tax": "BTW 21%",
        "total": "Totaal",
    },
    "de": {
        "title": "RECHNUNG",
        "vendor": "Lieferant",
        "customer": "Kunde",
        "vat": "USt-IdNr.",
        "number": "Rechnungsnummer",
        "date": "Rechnungsdatum",
        "due": "Fälligkeitsdatum",
        "po": "Bestellnummer",
        "description": "Beschreibung",
        "quantity": "Menge",
        "unit_price": "Einzelpreis",
        "amount": "Betrag",
        "subtotal": "Zwischensumme",
        "tax": "MwSt. 21%",
        "total": "Gesamtbetrag",
    },
    "fr": {
        "title": "FACTURE",
        "vendor": "Fournisseur",
        "customer": "Client",
        "vat": "N° TVA",
        "number": "N° de facture",
        "date": "Date de facture",
        "due": "Échéance",
        "po": "Bon de commande",
        "description": "Description",
        "quantity": "Quantité",
        "unit_price": "Prix unitaire",
        "amount": "Montant",
        "subtotal": "Sous-total",
        "tax": "TVA 21%",
        "total": "Total",
    },
}


@dataclass(frozen=True)
class InvoiceCase:
    filename: str
    language: Literal["en", "nl", "de", "fr"]
    layout: Literal["classic", "compact", "modern"]
    scenario: str
    vendor_name: str
    vendor_vat_id: str | None
    customer_vat_id: str | None
    invoice_number: str
    purchase_order: str | None
    subtotal: str
    total_tax: str
    invoice_total: str
    expected_issue_codes: tuple[str, ...] = ()
    pages: int = 1
    file_type: Literal["pdf", "png"] = "pdf"


@dataclass(frozen=True)
class SampleManifestEntry:
    filename: str
    language: str
    layout: str
    scenario: str
    pages: int
    document_type: str
    expected: dict[str, str | None]
    expected_issue_codes: list[str]


CASES = (
    InvoiceCase(
        "01-en-happy-classic.pdf", "en", "classic", "happy_path",
        "Bright Spark Europe S.A.S.", "FR61954506077", CUSTOMER_VAT_ID,
        "EN-2026-1001", "PO-4001", "100.00", "21.00", "121.00",
    ),
    InvoiceCase(
        "02-nl-happy-compact.pdf", "nl", "compact", "happy_path",
        "Helder Schoonmaak B.V.", "NL123456782B90", CUSTOMER_VAT_ID,
        "NL-2026-2042", "PO-4002", "240.00", "50.40", "290.40",
    ),
    InvoiceCase(
        "03-de-happy-modern.pdf", "de", "modern", "happy_path",
        "Rhein Wartung GmbH", "DE136695976", CUSTOMER_VAT_ID,
        "DE-2026-3098", "PO-4003", "450.00", "94.50", "544.50",
    ),
    InvoiceCase(
        "04-fr-happy-classic.pdf", "fr", "classic", "happy_path",
        "Lumière Technique S.A.S.", "FR40303265045", CUSTOMER_VAT_ID,
        "FR-2026-4017", "PO-4004", "180.00", "37.80", "217.80",
    ),
    InvoiceCase(
        "05-nl-missing-vendor-vat.pdf", "nl", "compact", "missing_vendor_vat",
        "Groen Onderhoud B.V.", None, CUSTOMER_VAT_ID,
        "NL-2026-5005", "PO-4005", "320.00", "67.20", "387.20",
        ("vendor_vat_id_required",),
    ),
    InvoiceCase(
        "06-de-invalid-vendor-vat.pdf", "de", "modern", "invalid_vendor_vat",
        "Alpen Elektro GmbH", "DE-NOT-A-VAT", CUSTOMER_VAT_ID,
        "DE-2026-6006", "PO-4006", "90.00", "18.90", "108.90",
        ("vendor_vat_id_invalid",),
    ),
    InvoiceCase(
        "07-fr-wrong-customer-vat.pdf", "fr", "classic", "wrong_customer_vat",
        "Propre Services S.A.S.", "FR61954506077", "FR40303265045",
        "FR-2026-7007", "PO-4007", "210.00", "44.10", "254.10",
        ("customer_vat_id_mismatch",),
    ),
    InvoiceCase(
        "08-en-total-mismatch.pdf", "en", "compact", "total_mismatch",
        "Lift Safety Europe S.A.S.", "FR40303265045", CUSTOMER_VAT_ID,
        "EN-2026-8008", "PO-4008", "100.00", "21.00", "125.00",
        ("invoice_total_mismatch",),
    ),
    InvoiceCase(
        "09-nl-missing-po.pdf", "nl", "modern", "missing_purchase_order",
        "Waterwerk B.V.", "NL123456782B90", CUSTOMER_VAT_ID,
        "NL-2026-9009", None, "140.00", "29.40", "169.40",
        ("purchase_order_missing",),
    ),
    InvoiceCase(
        "10-de-duplicate.pdf", "de", "classic", "duplicate",
        "Rhein Wartung GmbH", "DE136695976", CUSTOMER_VAT_ID,
        "DE-2026-3098", "PO-4010", "450.00", "94.50", "544.50",
        ("duplicate_invoice",),
    ),
    InvoiceCase(
        "11-fr-scan-quality.png", "fr", "compact", "scan_quality",
        "Clair Nettoyage S.A.S.", "FR61954506077", CUSTOMER_VAT_ID,
        "FR-2026-1111", "PO-4011", "75.00", "15.75", "90.75",
        file_type="png",
    ),
    InvoiceCase(
        "12-en-two-page.pdf", "en", "modern", "happy_path",
        "European Equipment S.A.S.", "FR40303265045", CUSTOMER_VAT_ID,
        "EN-2026-1212", "PO-4012", "600.00", "126.00", "726.00",
        pages=2,
    ),
)


def _expected(case: InvoiceCase) -> dict[str, str | None]:
    return {
        "document_type": "invoice",
        "vendor_name": case.vendor_name,
        "vendor_vat_id": case.vendor_vat_id,
        "customer_name": CUSTOMER_NAME,
        "customer_vat_id": case.customer_vat_id,
        "invoice_number": case.invoice_number,
        "purchase_order": case.purchase_order,
        "invoice_date": "2026-07-01",
        "due_date": "2026-07-31",
        "currency": "EUR",
        "subtotal": case.subtotal,
        "total_tax": case.total_tax,
        "invoice_total": case.invoice_total,
    }


def _meta_lines(case: InvoiceCase) -> list[tuple[str, str]]:
    labels = LABELS[case.language]
    return [
        (labels["number"], case.invoice_number),
        (labels["date"], "2026-07-01"),
        (labels["due"], "2026-07-31"),
        (labels["po"], case.purchase_order or "—"),
    ]


def _draw_pdf_page(canvas: Canvas, case: InvoiceCase, page: int) -> None:
    labels = LABELS[case.language]
    accent = {"classic": "#183153", "compact": "#226B5C", "modern": "#5B4B8A"}[case.layout]
    width, height = A4

    canvas.setFillColor(HexColor(accent))
    canvas.rect(0, height - 88, width, 88, fill=1, stroke=0)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawString(42, height - 55, labels["title"])
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(width - 42, height - 54, f"Page {page} / {case.pages}")

    canvas.setFillColorRGB(0.12, 0.15, 0.18)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(42, height - 118, labels["vendor"])
    canvas.drawString(320, height - 118, labels["customer"])
    canvas.setFont("Helvetica", 10)
    canvas.drawString(42, height - 136, case.vendor_name)
    canvas.drawString(42, height - 152, f"{labels['vat']}: {case.vendor_vat_id or '—'}")
    canvas.drawString(320, height - 136, CUSTOMER_NAME)
    canvas.drawString(320, height - 152, f"{labels['vat']}: {case.customer_vat_id or '—'}")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(320, height - 168, CUSTOMER_ADDRESS)

    y = height - 202
    canvas.setFont("Helvetica", 9)
    for label, value in _meta_lines(case):
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(42, y, label)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(150, y, value)
        y -= 17

    y -= 10
    canvas.setFillColor(HexColor("#EEF1F4"))
    canvas.rect(42, y - 8, width - 84, 25, fill=1, stroke=0)
    canvas.setFillColorRGB(0.12, 0.15, 0.18)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(50, y, labels["description"])
    canvas.drawRightString(355, y, labels["quantity"])
    canvas.drawRightString(450, y, labels["unit_price"])
    canvas.drawRightString(width - 50, y, labels["amount"])

    items = 4 if case.pages == 1 else 10
    start = 0 if page == 1 else items // 2
    stop = items if case.pages == 1 else start + items // 2
    y -= 29
    canvas.setFont("Helvetica", 8)
    for index in range(start, stop):
        amount = float(case.subtotal) / items
        canvas.drawString(50, y, f"Facility service item {index + 1}")
        canvas.drawRightString(355, y, "1")
        canvas.drawRightString(450, y, f"EUR {amount:.2f}")
        canvas.drawRightString(width - 50, y, f"EUR {amount:.2f}")
        canvas.line(50, y - 7, width - 50, y - 7)
        y -= 24

    if page == case.pages:
        y = max(y - 12, 145)
        canvas.setFont("Helvetica", 9)
        for label, value in (
            (labels["subtotal"], case.subtotal),
            (labels["tax"], case.total_tax),
            (labels["total"], case.invoice_total),
        ):
            canvas.drawRightString(465, y, label)
            canvas.setFont("Helvetica-Bold" if label == labels["total"] else "Helvetica", 9)
            canvas.drawRightString(width - 50, y, f"EUR {value}")
            canvas.setFont("Helvetica", 9)
            y -= 19

    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(HexColor("#6C757D"))
    canvas.drawString(42, 35, "Fictional tutorial invoice — not a real commercial document")


def _render_pdf(path: Path, case: InvoiceCase) -> None:
    canvas = Canvas(str(path), pagesize=A4, invariant=1)
    for page in range(1, case.pages + 1):
        _draw_pdf_page(canvas, case, page)
        canvas.showPage()
    canvas.save()


def load_scan_font(size: int) -> ImageFont.FreeTypeFont:
    font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    return ImageFont.truetype(str(font_path), size)


def _render_scan(path: Path, case: InvoiceCase) -> None:
    labels = LABELS[case.language]
    image = Image.new("RGB", (1240, 1754), "#F4F1E8")
    draw = ImageDraw.Draw(image)
    title_font = load_scan_font(38)
    body_font = load_scan_font(22)
    small_font = load_scan_font(18)

    draw.text((75, 70), labels["title"], fill="#454545", font=title_font)
    lines = [
        f"{labels['vendor']}: {case.vendor_name}",
        f"{labels['vat']}: {case.vendor_vat_id}",
        f"{labels['customer']}: {CUSTOMER_NAME}",
        f"{labels['vat']}: {case.customer_vat_id}",
        f"{labels['number']}: {case.invoice_number}",
        f"{labels['date']}: 2026-07-01",
        f"{labels['due']}: 2026-07-31",
        f"{labels['po']}: {case.purchase_order}",
        "",
        f"{labels['description']}: Entretien des installations",
        f"{labels['quantity']}: 1",
        f"{labels['subtotal']}: EUR {case.subtotal}",
        f"{labels['tax']}: EUR {case.total_tax}",
        f"{labels['total']}: EUR {case.invoice_total}",
    ]
    y = 160
    for line in lines:
        draw.text((75, y), line, fill="#666666", font=body_font)
        y += 54
    draw.text(
        (75, 1650),
        "Document fictif pour tutoriel — aucune transaction réelle",
        fill="#777777",
        font=small_font,
    )
    image = ImageEnhance.Contrast(image).enhance(0.72)
    image.save(path, format="PNG", optimize=True)


def _render_fuel_receipt(path: Path) -> None:
    canvas = Image.new("RGB", (1000, 1400), "#BDBAB4")
    draw_canvas = ImageDraw.Draw(canvas)
    draw_canvas.rounded_rectangle((132, 112, 902, 1312), radius=16, fill="#77736E")

    receipt = Image.new("RGB", (720, 1160), "#F5F1E8")
    draw = ImageDraw.Draw(receipt)
    title_font = load_scan_font(31)
    body_font = load_scan_font(23)
    small_font = load_scan_font(18)
    bold_font_path = Path(reportlab.__file__).parent / "fonts" / "VeraBd.ttf"
    bold_font = ImageFont.truetype(str(bold_font_path), 24)

    lines: list[tuple[str, ImageFont.FreeTypeFont, int]] = [
        ("NORTH SEA FUEL B.V.", title_font, 18),
        ("Wibautstraat 150", small_font, 8),
        ("1091 GR Amsterdam", small_font, 8),
        ("KASSABON", bold_font, 24),
        ("Datum: 19-07-2026   Tijd: 14:32", body_font, 18),
        ("Pomp: 04            Terminal: 02", small_font, 28),
        ("EURO 95", bold_font, 12),
        ("25.00 L x EUR 2.420", body_font, 8),
        ("Brandstof                         EUR 60.50", body_font, 28),
        ("Subtotaal excl. BTW               EUR 50.00", body_font, 10),
        ("BTW 21%                           EUR 10.50", body_font, 20),
        ("TOTAAL                            EUR 60.50", bold_font, 28),
        ("Betaald met PIN                    EUR 60.50", body_font, 12),
        ("Bedankt en een veilige reis!", small_font, 42),
        ("Fictieve kassabon voor tutorial", small_font, 8),
    ]
    y = 62
    for text, font, spacing in lines:
        draw.text((52, y), text, fill="#4B4945", font=font)
        y += font.size + spacing
        separators = {
            "KASSABON",
            "Pomp: 04            Terminal: 02",
            "TOTAAL                            EUR 60.50",
        }
        if text in separators:
            draw.line((48, y - 8, 672, y - 8), fill="#A7A198", width=2)

    rotated = receipt.rotate(
        1.4,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor="#BDBAB4",
    )
    canvas.paste(rotated, ((canvas.width - rotated.width) // 2, 102))
    canvas = ImageEnhance.Contrast(canvas).enhance(0.86)
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.35))
    canvas.save(path, format="PNG", optimize=True)


def generate_corpus(output_dir: Path) -> list[SampleManifestEntry]:
    generated_dir = output_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    entries: list[SampleManifestEntry] = []

    for case in CASES:
        target = generated_dir / case.filename
        if case.file_type == "png":
            _render_scan(target, case)
        else:
            _render_pdf(target, case)
        entries.append(
            SampleManifestEntry(
                filename=case.filename,
                language=case.language,
                layout=case.layout,
                scenario=case.scenario,
                pages=case.pages,
                document_type="invoice",
                expected=_expected(case),
                expected_issue_codes=list(case.expected_issue_codes),
            )
        )

    receipt_filename = "13-nl-fuel-receipt.png"
    _render_fuel_receipt(generated_dir / receipt_filename)
    entries.append(
        SampleManifestEntry(
            filename=receipt_filename,
            language="nl",
            layout="compact",
            scenario="fuel_receipt",
            pages=1,
            document_type="receipt",
            expected={
                "document_type": "receipt",
                "vendor_name": "North Sea Fuel B.V.",
                "vendor_vat_id": None,
                "customer_name": None,
                "customer_vat_id": None,
                "invoice_number": None,
                "purchase_order": None,
                "invoice_date": "2026-07-19",
                "due_date": None,
                "currency": "EUR",
                "subtotal": "50.00",
                "total_tax": "10.50",
                "invoice_total": "60.50",
            },
            expected_issue_codes=[],
        )
    )

    manifest = [asdict(entry) for entry in entries]
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    return entries


def main() -> None:
    output_dir = Path(__file__).parents[2] / "samples"
    entries = generate_corpus(output_dir)
    print(
        f"Generated {len(entries)} fictional financial-document samples "
        f"in {output_dir / 'generated'}"
    )


if __name__ == "__main__":
    main()
