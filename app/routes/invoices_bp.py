from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from markupsafe import Markup
from app.pdf_utils import build_pdf, _sanitize_filename
from app.models import Invoice, InvoiceLineItem, Setting, Workshop
from app import db
from datetime import datetime

PAYMENT_TERMS_OPTS = [('immediate', 'Immediate'), ('net15', 'Net 15'), ('net30', 'Net 30'), ('net60', 'Net 60')]

bp = Blueprint('invoices', __name__)

def _next_invoice_number():
    prefix = Setting.get('invoice_prefix', 'INV-')
    all_nums = [int(i.invoice_number.replace(prefix, '')) for i in Invoice.query.all() if i.invoice_number.startswith(prefix)]
    highest = max(all_nums) if all_nums else 0
    n = max(highest + 1, 1009542)
    return f"{prefix}{n}"

def _currency():
    currencies = {'USD': '$', 'EUR': '€', 'GBP': '£', 'AED': '\u20C3', 'INR': '₹', 'SAR': '﷼'}
    code = Setting.get('currency', 'USD')
    sym = currencies.get(code, '$')
    if code == 'AED':
        return Markup('<img src="/static/images/aed.svg" alt="AED" style="height:0.8em;vertical-align:middle">&nbsp;')
    return sym + ' '

@bp.route('/invoices/')
def list_invoices():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Invoice.query
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.order_by(Invoice.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('invoices/list.html', invoices=invoices, status=status, currency=_currency())

@bp.route('/invoices/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/view.html',
        invoice=invoice, currency=_currency(),
        business_name=Setting.get('business_name', 'Your Business'),
        business_address=Setting.get('business_address', ''),
        business_phone=Setting.get('business_phone', ''),
        business_email=Setting.get('business_email', ''),
        tax_number=Setting.get('tax_number', ''))

@bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if request.method == 'POST':
        issue_date_str = request.form.get('issue_date', '')
        if issue_date_str:
            invoice.issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d')
        invoice.description = request.form.get('description', '')
        invoice.odometer_reading = request.form.get('odometer_reading', '')
        invoice.workshop_id = request.form.get('workshop_id', type=int) or None
        invoice.notes = request.form.get('notes', '')
        invoice.tax_rate = float(request.form.get('tax_rate', 5)) / 100
        invoice.discount_workshop = float(request.form.get('discount_workshop', 0))
        invoice.discount_ob = float(request.form.get('discount_ob', 0))
        invoice.payment_terms = request.form.get('payment_terms', 'net30')
        if invoice.payment_terms != 'immediate':
            invoice.set_due_date(invoice.payment_terms)

        for li in invoice.line_items:
            db.session.delete(li)
        count = int(request.form.get('line_items_count', 0))
        subtotal = 0
        for i in range(count):
            desc = request.form.get(f'line_items[{i}][description]')
            if not desc:
                continue
            cost = request.form.get(f'line_items[{i}][cost]', type=float) or None
            margin = request.form.get(f'line_items[{i}][margin]', type=float) or None
            if margin is not None and cost is not None and cost > 0:
                price = cost + (cost * margin / 100)
            else:
                price = float(request.form.get(f'line_items[{i}][unit_price]', 0))
            qty = float(request.form.get(f'line_items[{i}][quantity]', 1))
            item_type = request.form.get(f'line_items[{i}][item_type]', 'service')
            parts_type = request.form.get(f'line_items[{i}][parts_type]', '') or None
            parts_source = request.form.get(f'line_items[{i}][parts_source]', '') or None
            li = InvoiceLineItem(
                invoice_id=invoice.id, description=desc, cost=cost, margin=margin,
                quantity=qty, unit_price=price, total=qty * price,
                item_type=item_type, parts_type=parts_type, parts_source=parts_source)
            db.session.add(li)
            subtotal += li.total
        invoice.subtotal = subtotal
        after_discount = subtotal - invoice.discount_workshop - invoice.discount_ob
        invoice.tax_amount = max(after_discount, 0) * invoice.tax_rate
        invoice.total = max(after_discount, 0) + invoice.tax_amount
        invoice.balance_due = invoice.total - invoice.paid_amount
        invoice.update_status()
        db.session.commit()
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
    default_tax = Setting.get('default_tax_rate', '5')
    workshops = Workshop.query.order_by(Workshop.name).all()
    return render_template('invoices/form.html', invoice=invoice, currency=_currency(), default_tax=default_tax, workshops=workshops, payment_terms_options=PAYMENT_TERMS_OPTS)

@bp.route('/invoices/<int:invoice_id>/mark-sent', methods=['POST'])
def mark_sent(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'sent'
    if not invoice.due_date and invoice.payment_terms != 'immediate':
        invoice.set_due_date(invoice.payment_terms or 'net30')
    db.session.commit()
    flash('Invoice marked as sent', 'success')
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))

@bp.route('/invoices/<int:invoice_id>/mark-paid', methods=['POST'])
def mark_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'paid'
    invoice.paid_amount = invoice.total
    invoice.balance_due = 0
    db.session.commit()
    flash('Invoice marked as paid', 'success')
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))

@bp.route('/invoices/<int:invoice_id>/pdf')
def pdf_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    c = invoice.customer
    vehicle_parts = []
    v = invoice.vehicle or (invoice.estimate.vehicle if invoice.estimate else None)
    if v:
        if v.year or v.make or v.model:
            vehicle_parts.append(f"{v.year or ''} {v.make or ''} {v.model or ''}".strip())
        if v.vin:
            vehicle_parts.append(f"VIN: {v.vin}")
        if v.plate:
            vehicle_parts.append(f"Plate: {v.plate}")
    odometer = invoice.odometer_reading or (invoice.estimate.odometer_reading if invoice.estimate else None)
    if odometer:
        vehicle_parts.append(f"Odometer: {odometer}")
    vehicle_info = "<br/>".join(vehicle_parts)
    workshop_info = ""
    if invoice.workshop:
        w = invoice.workshop
        workshop_info = w.name or ""
        if w.area or w.city:
            workshop_info += f"<br/>{w.area or ''}{', ' if w.area and w.city else ''}{w.city or ''}"
        if w.emirate_state:
            workshop_info += f"<br/>{w.emirate_state}, UAE"
        if w.vat_number:
            workshop_info += f"<br/>VAT: {w.vat_number}"
    entity = c.name
    if c.phone:
        entity += f"<br/>{c.phone}"
    if c.address:
        entity += f"<br/>{c.address}"
    if c.city:
        entity += f"<br/>{c.city}"
    items = [{'description': li.description, 'item_type': li.item_type, 'parts_type': li.parts_type, 'parts_source': li.parts_source, 'quantity': li.quantity, 'unit_price': li.unit_price, 'total': li.total} for li in invoice.line_items]
    date_value = invoice.issue_date.strftime('%B %d, %Y')
    buf = build_pdf(
        title='INVOICE',
        doc_type_label='Invoice',
        doc_number=invoice.invoice_number,
        entity=entity,
        items=items,
        subtotal=invoice.subtotal,
        tax_rate=invoice.tax_rate,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        notes=invoice.notes,
        date_label='Invoice Date',
        date_value=date_value,
        vehicle_info=vehicle_info,
        workshop_info=workshop_info,
        customer_name=c.name,
        discount_workshop=invoice.discount_workshop or 0,
        discount_ob=invoice.discount_ob or 0,
    )
    safe_name = _sanitize_filename(c.name).replace(' ', '_')
    safe_num = _sanitize_filename(invoice.invoice_number)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'{safe_num}_{safe_name}.pdf')
