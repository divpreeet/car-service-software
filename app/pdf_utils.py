import os, json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from app.models import Setting

CURRENCY_SYMS = {'USD': '$', 'EUR': '\u20ac', 'GBP': '\u00a3', 'AED': 'AED ', 'INR': '\u20b9', 'SAR': '\ufdfc'}

_UNITS = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
_TEENS = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
_SCALES = ['', 'Thousand', 'Million', 'Billion']


def _under_1000(n):
    words = ''
    h = n // 100
    if h:
        words += _UNITS[h] + ' Hundred '
        n %= 100
    if n >= 20:
        words += _TENS[n // 10] + ' '
        n %= 10
    elif n >= 10:
        words += _TEENS[n - 10] + ' '
        n = 0
    if n:
        words += _UNITS[n] + ' '
    return words.strip()


def _number_to_words(amount):
    if amount == 0:
        return 'Zero'
    whole = int(amount)
    cents = round((amount - whole) * 100)
    words = ''
    if whole:
        parts = []
        i = 0
        while whole:
            part = whole % 1000
            if part:
                w = _under_1000(part)
                if _SCALES[i]:
                    w += ' ' + _SCALES[i]
                parts.append(w)
            whole //= 1000
            i += 1
        words = ' '.join(reversed(parts))
    else:
        words = 'Zero'
    if cents:
        words += f' and {cents:02d}/100'
    else:
        words += ' Only'
    return words


PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
_THICK = colors.Color(0.15, 0.15, 0.15)
_GRAY = colors.Color(0.4, 0.4, 0.4)
_LIGHT_GRAY = colors.Color(0.95, 0.95, 0.95)
_ROW_ALT = colors.Color(0.97, 0.97, 0.98)
_BORDER = colors.Color(0.85, 0.85, 0.85)
_ORANGE = colors.HexColor('#f97316')
_ORANGE_HEX = '#f97316'


def _get_settings():
    return {
        'business_name': Setting.get('business_name', 'Your Business'),
        'business_address': Setting.get('business_address', ''),
        'business_phone': Setting.get('business_phone', ''),
        'business_email': Setting.get('business_email', ''),
        'tax_number': Setting.get('tax_number', ''),
        'logo': Setting.get('logo', ''),
    }


def _currency():
    code = Setting.get('currency', 'USD')
    return CURRENCY_SYMS.get(code, '$')


def _get_layout():
    raw = Setting.get('invoice_layout')
    default = {
        'logo': 'header_left', 'company_name': 'header_left',
        'doc_info': 'header_right', 'date': 'body', 'due_date': 'body',
        'tax_number': 'body', 'bill_to': 'body', 'vehicle_info': 'body',
        'line_items': 'body', 'totals': 'body', 'notes': 'body',
        'company_info': 'footer_center', 'page_number': 'footer_right',
    }
    if not raw:
        return default
    try:
        return {**default, **json.loads(raw)}
    except (json.JSONDecodeError, TypeError):
        return default


def _visible(layout, key):
    v = layout.get(key)
    return v and v != ''


def _is_position(layout, key, pos):
    return layout.get(key) == pos


def _in_body(layout, key):
    return layout.get(key) == 'body'


def _in_header(layout, key):
    v = layout.get(key)
    return v and v.startswith('header_')


def _header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    biz = _get_settings()
    layout = _get_layout()

    right_x = PAGE_W - MARGIN

    # --- Header ---
    has_header = _visible(layout, 'company_address') or _visible(layout, 'company_phone')

    y = PAGE_H - MARGIN

    if has_header:
        # Draw the thick separator line
        canvas_obj.setStrokeColor(_THICK)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(MARGIN, y, right_x, y)

        # -- Left column: company info --
        left_x = MARGIN

        # Header info text
        addr = biz['business_address'] if _visible(layout, 'company_address') else ''
        phone = biz['business_phone'] if _visible(layout, 'company_phone') else ''

        canvas_obj.setFillColor(_GRAY)
        canvas_obj.setFont('Helvetica', 7)
        if addr:
            canvas_obj.drawString(left_x, y - 10, addr.replace('\n', ', ').replace('\r', ''))
        if phone:
            canvas_obj.drawString(left_x, y - 22, phone)

        canvas_obj.setFillColor(colors.black)

    # --- Footer ---
    has_footer = any(_visible(layout, k) for k in ['company_info', 'company_name', 'company_address', 'company_phone', 'page_number'])
    if has_footer:
        yf = MARGIN
        canvas_obj.setStrokeColor(_GRAY)
        canvas_obj.setLineWidth(0.3)
        canvas_obj.line(MARGIN, yf, right_x, yf)

        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(_GRAY)
        company = f"{biz['business_name']} | {biz['business_address']} | {biz['business_phone']}"

        def _draw(region, text):
            if not text:
                return
            if region == 'footer_left':
                canvas_obj.drawString(MARGIN, yf - 12, text)
            elif region == 'footer_center':
                canvas_obj.drawCentredString(PAGE_W / 2, yf - 12, text)
            elif region == 'footer_right':
                canvas_obj.drawRightString(right_x, yf - 12, text)

        _draw('footer_left', company if _is_position(layout, 'company_info', 'footer_left') else '')
        _draw('footer_center', company if _is_position(layout, 'company_info', 'footer_center') else '')
        _draw('footer_right', company if _is_position(layout, 'company_info', 'footer_right') else '')
        pg = f"Page {canvas_obj.getPageNumber()}"
        _draw('footer_left', pg if _is_position(layout, 'page_number', 'footer_left') else '')
        _draw('footer_center', pg if _is_position(layout, 'page_number', 'footer_center') else '')
        _draw('footer_right', pg if _is_position(layout, 'page_number', 'footer_right') else '')

    canvas_obj.restoreState()


class _PDFDocTemplate(BaseDocTemplate):
    def __init__(self, buf, **kw):
        BaseDocTemplate.__init__(self, buf, **kw)
        frame = Frame(MARGIN, MARGIN + 8*mm, PAGE_W - 2*MARGIN, PAGE_H - 2*MARGIN - 8*mm, id='normal')
        self.addPageTemplates([PageTemplate(id='main', frames=frame, onPage=_header_footer)])


def build_pdf(title, doc_type_label, doc_number, entity, items, subtotal, tax_rate, tax_amount, total, notes="", date_label="Date", date_value=None, due_label=None, due_value=None, vehicle_info=""):
    buf = BytesIO()
    doc = _PDFDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN + 8*mm)

    # Store for _header_footer
    doc._doc_label = title.upper()
    doc._doc_number = doc_number

    styles = getSampleStyleSheet()
    cur = _currency()
    biz = _get_settings()
    layout = _get_layout()
    aw = PAGE_W - 2 * MARGIN  # available width

    elements = []

    # Custom styles
    styles.add(ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=11))
    styles.add(ParagraphStyle('Bold8', parent=styles['Normal'], fontSize=8, leading=11, fontName='Helvetica-Bold', textColor=colors.white))
    styles.add(ParagraphStyle('GrayLabel', parent=styles['Normal'], fontSize=7, leading=9,
                                textColor=_GRAY, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle('TotalValue', parent=styles['Normal'], fontSize=8, leading=11, alignment=TA_RIGHT))
    styles.add(ParagraphStyle('TotalLarge', parent=styles['Normal'], fontSize=14, leading=17,
                                fontName='Helvetica-Bold', alignment=TA_RIGHT))

    # Spacer below header thick line
    elements.append(Spacer(1, -1))

    # --- Logo (left) + INVOICE heading (right) ---
    show_logo = _visible(layout, 'logo')
    show_heading = _visible(layout, 'doc_info')
    if show_logo or show_heading:
        left_cells = []
        right_cells = []
        if show_logo:
            logo_name = biz.get('logo')
            if logo_name:
                logo_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', logo_name)
                if os.path.exists(logo_path):
                    try:
                        img = Image(logo_path, width=40*mm, height=18*mm)
                        left_cells.append(img)
                    except Exception:
                        left_cells.append(Paragraph('', styles['Small']))
                else:
                    left_cells.append(Paragraph('', styles['Small']))
            else:
                left_cells.append(Paragraph('', styles['Small']))
        else:
            left_cells.append(Paragraph('', styles['Small']))

        if show_heading:
            doc_label = getattr(doc, '_doc_label', 'INVOICE')
            doc_number = getattr(doc, '_doc_number', '')
            heading_text = f"{doc_label}<br/><font size='8' color='#666666'>{doc_number}</font>"
            if date_value:
                heading_text += f"<br/><font size='8' color='#666666'>{date_value}</font>"
            styles.add(ParagraphStyle('DocTitleRight', parent=styles['Normal'], fontSize=20,
                                        fontName='Helvetica-Bold', alignment=TA_RIGHT,
                                        textColor=_ORANGE))
            right_cells.append(Paragraph(heading_text, styles['DocTitleRight']))
        else:
            right_cells.append(Paragraph('', styles['Small']))

        title_table = Table([[left_cells[0], right_cells[0]]], colWidths=[aw / 2, aw / 2])
        title_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 2*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#2563eb'), spaceAfter=2*mm))

    # --- Info strip: tax-number ---
    info_cells = []
    if biz['tax_number'] and _in_body(layout, 'tax_number'):
        info_cells.append(Paragraph(
            f"<font color='{_ORANGE_HEX}' size='7'><b>TAX NO.</b></font><br/>{biz['tax_number']}",
            styles['Small']))

    if info_cells:
        n = len(info_cells)
        it = Table([info_cells], colWidths=[aw / n] * n)
        it.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (-1,-1), _LIGHT_GRAY),
        ]))
        elements.append(it)
        elements.append(Spacer(1, 6*mm))

    # --- Bill To + Vehicle Info (2-column) ---
    show_bill = _in_body(layout, 'bill_to')
    show_veh = _in_body(layout, 'vehicle_info') and vehicle_info

    if show_bill or show_veh:
        left_cell = Paragraph(
            f"<font color='{_ORANGE_HEX}' size='7'><b>BILL TO</b></font><br/>"
            f"<b>{entity.replace('<br/>', '<br/>')}</b>",
            styles['Small']) if show_bill else Paragraph('', styles['Small'])

        right_cell = Paragraph(
            f"<font color='{_ORANGE_HEX}' size='7'><b>VEHICLE</b></font><br/>"
            f"{vehicle_info.replace('<br/>', '<br/>')}",
            styles['Small']) if show_veh else Paragraph('', styles['Small'])

        cols = 2 if (show_bill and show_veh) else 1
        cells = [left_cell, right_cell] if (show_bill and show_veh) else ([left_cell] if show_bill else [right_cell])
        cw = [aw / cols] * cols

        bt = Table([cells], colWidths=cw)
        bt.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(bt)
        elements.append(Spacer(1, 6*mm))

    # --- Line Items Table ---
    if _in_body(layout, 'line_items'):
        hdr = [
            Paragraph('<b>#</b>', styles['Bold8']),
            Paragraph('<b>DESCRIPTION</b>', styles['Bold8']),
            Paragraph('<b>TYPE</b>', styles['Bold8']),
            Paragraph('<b>QTY</b>', styles['Bold8']),
            Paragraph('<b>RATE</b>', styles['Bold8']),
            Paragraph('<b>AMOUNT</b>', styles['Bold8']),
        ]
        rows = []
        for i, item in enumerate(items, 1):
            rows.append([
                str(i),
                Paragraph(f"<b>{item['description']}</b>", styles['Small']),
                item.get('item_type', '').title(),
                str(item['quantity']),
                f"{cur}{item['unit_price']:.2f}",
                f"{cur}{item['total']:.2f}",
            ])

        c1, c3, c4 = 8*mm, 18*mm, 12*mm
        c5 = c6 = 28*mm
        c2 = aw - c1 - c3 - c4 - c5 - c6

        td = [hdr] + rows
        tbl = Table(td, colWidths=[c1,c2,c3,c4,c5,c6], repeatRows=1)
        ts = [
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), _THICK),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (2,0), (2,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.4, _BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]
        tbl.setStyle(TableStyle(ts))
        for i in range(1, len(td)):
            if i % 2 == 0:
                tbl.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), _ROW_ALT)]))
        elements.append(tbl)
        elements.append(Spacer(1, 6*mm))

    # --- Totals ---
    if _in_body(layout, 'totals'):
        trows = [
            [Paragraph('Subtotal', styles['Small']), Paragraph(f"{cur}{subtotal:.2f}", styles['TotalValue'])],
        ]
        if tax_rate > 0:
            trows.append([
                Paragraph(f'Tax ({tax_rate*100:.0f}%)', styles['Small']),
                Paragraph(f"{cur}{tax_amount:.2f}", styles['TotalValue']),
            ])
        trows.append([Paragraph('', styles['Small']), Paragraph('', styles['Small'])])
        trows.append([
            Paragraph(f"<font color='{_ORANGE_HEX}'><b>TOTAL DUE</b></font>", styles['Small']),
            Paragraph(f"<b>{cur}{total:.2f}</b>", styles['TotalLarge']),
        ])
        words = _number_to_words(total)
        trows.append([
            Paragraph(f"<font size='7' color='#666666'><i>{words}</i></font>", styles['Normal']),
            Paragraph('', styles['Normal']),
        ])

        tw = [aw - 55*mm, 55*mm]
        tt = Table(trows, colWidths=tw)
        tt.setStyle(TableStyle([
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEABOVE', (2,0), (2,-1), 0.5, _GRAY),
            ('LINEABOVE', (3,0), (3,-1), 1.5, _THICK),
        ]))
        elements.append(tt)

    # --- Notes ---
    if notes and _in_body(layout, 'notes'):
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(
            f"<font color='{_ORANGE_HEX}' size='7'><b>NOTES</b></font><br/>"
            f"<font size='8'><i>{notes}</i></font>",
            styles['Normal']))

    doc.build(elements)
    buf.seek(0)
    return buf
