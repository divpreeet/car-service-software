from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from markupsafe import Markup
from app.pdf_utils import build_pdf
from app.models import Customer, Estimate, EstimateLineItem, Setting
from app import db
from datetime import datetime

bp = Blueprint('estimates', __name__)

def _next_estimate_number():
    prefix = Setting.get('estimate_prefix', 'EST-')
    all_nums = [int(e.estimate_number.replace(prefix, '')) for e in Estimate.query.all() if e.estimate_number.startswith(prefix)]
    highest = max(all_nums) if all_nums else 0
    n = max(highest + 1, 1009542)
    return f"{prefix}{n}"

def _currency():
    currencies = {'USD': '$', 'EUR': '€', 'GBP': '£', 'AED': '\u20C3', 'INR': '₹', 'SAR': '﷼'}
    code = Setting.get('currency', 'USD')
    sym = currencies.get(code, '$')
    if code == 'AED':
        return Markup('<img src="/static/images/aed.svg" alt="AED" style="height:1.1em;vertical-align:middle">')
    return sym

@bp.route('/estimates/')
def list_estimates():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Estimate.query
    if status:
        query = query.filter(Estimate.status == status)
    estimates = query.order_by(Estimate.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('estimates/list.html', estimates=estimates, status=status, currency=_currency())

@bp.route('/estimates/create', methods=['GET', 'POST'])
def create_estimate():
    if request.method == 'POST':
        est = Estimate(
            estimate_number=_next_estimate_number(),
            customer_id=request.form.get('customer_id', type=int),
            vehicle_id=request.form.get('vehicle_id', type=int) or None,
            description=request.form.get('description', ''),
            odometer_reading=request.form.get('odometer_reading', ''),
            notes=request.form.get('notes', ''),
            tax_rate=float(request.form.get('tax_rate', 5)) / 100,
        )
        valid_until_str = request.form.get('valid_until')
        if valid_until_str:
            est.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
        est.status = 'draft'

        count = int(request.form.get('line_items_count', 0))
        subtotal = 0
        for i in range(count):
            desc = request.form.get(f'line_items[{i}][description]')
            if not desc:
                continue
            qty = float(request.form.get(f'line_items[{i}][quantity]', 1))
            price = float(request.form.get(f'line_items[{i}][unit_price]', 0))
            item_type = request.form.get(f'line_items[{i}][item_type]', 'service')
            li = EstimateLineItem(
                description=desc, quantity=qty, unit_price=price,
                total=qty * price, item_type=item_type)
            est.line_items.append(li)
            subtotal += li.total
        est.subtotal = subtotal
        est.tax_amount = subtotal * est.tax_rate
        est.total = subtotal + est.tax_amount
        db.session.add(est)
        db.session.commit()
        flash('Estimate created successfully', 'success')
        return redirect(url_for('estimates.list_estimates'))
    customers = Customer.query.order_by(Customer.name).all()
    default_tax = Setting.get('default_tax_rate', '5')
    return render_template('estimates/form.html', estimate=None, customers=customers, default_tax=default_tax)

@bp.route('/estimates/<int:estimate_id>')
def view_estimate(estimate_id):
    estimate = Estimate.query.get_or_404(estimate_id)
    return render_template('estimates/view.html', estimate=estimate, currency=_currency())

@bp.route('/estimates/<int:estimate_id>/edit', methods=['GET', 'POST'])
def edit_estimate(estimate_id):
    estimate = Estimate.query.get_or_404(estimate_id)
    if request.method == 'POST':
        estimate.customer_id = request.form.get('customer_id', type=int)
        estimate.vehicle_id = request.form.get('vehicle_id', type=int) or None
        estimate.description = request.form.get('description', '')
        estimate.odometer_reading = request.form.get('odometer_reading', '')
        estimate.notes = request.form.get('notes', '')
        estimate.tax_rate = float(request.form.get('tax_rate', 5)) / 100
        valid_until_str = request.form.get('valid_until')
        if valid_until_str:
            estimate.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')

        for li in estimate.line_items:
            db.session.delete(li)
        count = int(request.form.get('line_items_count', 0))
        subtotal = 0
        for i in range(count):
            desc = request.form.get(f'line_items[{i}][description]')
            if not desc:
                continue
            qty = float(request.form.get(f'line_items[{i}][quantity]', 1))
            price = float(request.form.get(f'line_items[{i}][unit_price]', 0))
            item_type = request.form.get(f'line_items[{i}][item_type]', 'service')
            li = EstimateLineItem(
                estimate_id=estimate.id, description=desc, quantity=qty,
                unit_price=price, total=qty * price, item_type=item_type)
            db.session.add(li)
            subtotal += li.total
        estimate.subtotal = subtotal
        estimate.tax_amount = subtotal * estimate.tax_rate
        estimate.total = subtotal + estimate.tax_amount
        db.session.commit()
        flash('Estimate updated successfully', 'success')
        return redirect(url_for('estimates.view_estimate', estimate_id=estimate.id))
    customers = Customer.query.order_by(Customer.name).all()
    default_tax = Setting.get('default_tax_rate', '5')
    return render_template('estimates/form.html', estimate=estimate, customers=customers, default_tax=default_tax)

def _next_invoice_number():
    prefix = Setting.get('invoice_prefix', 'INV-')
    from app.models import Invoice
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"{prefix}{n:06d}"

@bp.route('/estimates/<int:estimate_id>/convert', methods=['POST'])
def convert_to_invoice(estimate_id):
    from app.models import Invoice, InvoiceLineItem
    estimate = Estimate.query.get_or_404(estimate_id)
    if estimate.status == 'converted':
        flash('Estimate already converted', 'error')
        return redirect(url_for('estimates.view_estimate', estimate_id=estimate.id))

    inv = Invoice(
        invoice_number=_next_invoice_number(),
        customer_id=estimate.customer_id,
        estimate_id=estimate.id,
        description=estimate.description,
        odometer_reading=estimate.odometer_reading,
        vehicle_id=estimate.vehicle_id,
        notes=estimate.notes,
        subtotal=estimate.subtotal,
        tax_rate=estimate.tax_rate,
        tax_amount=estimate.tax_amount,
        total=estimate.total,
        paid_amount=0,
        balance_due=estimate.total,
        status='draft',
        issue_date=datetime.utcnow(),
    )
    for li in estimate.line_items:
        inv.line_items.append(InvoiceLineItem(
            description=li.description, item_type=li.item_type,
            quantity=li.quantity, unit_price=li.unit_price, total=li.total))
    estimate.status = 'converted'
    db.session.add(inv)
    db.session.commit()
    flash('Estimate converted to invoice', 'success')
    return redirect(url_for('invoices.view_invoice', invoice_id=inv.id))

@bp.route('/estimates/<int:estimate_id>/pdf')
def pdf_estimate(estimate_id):
    estimate = Estimate.query.get_or_404(estimate_id)
    c = estimate.customer
    vehicle_parts = []
    v = estimate.vehicle
    if v:
        if v.year or v.make or v.model:
            vehicle_parts.append(f"{v.year or ''} {v.make or ''} {v.model or ''}".strip())
        if v.vin:
            vehicle_parts.append(f"VIN: {v.vin}")
        if v.plate:
            vehicle_parts.append(f"Plate: {v.plate}")
    if estimate.odometer_reading:
        vehicle_parts.append(f"Odometer: {estimate.odometer_reading}")
    vehicle_info = "<br/>".join(vehicle_parts)
    entity = c.name
    if c.phone:
        entity += f"<br/>{c.phone}"
    if c.address:
        entity += f"<br/>{c.address}"
    if c.city:
        entity += f"<br/>{c.city}"
    items = [{'description': li.description, 'item_type': li.item_type, 'quantity': li.quantity, 'unit_price': li.unit_price, 'total': li.total} for li in estimate.line_items]
    date_value = estimate.created_at.strftime('%B %d, %Y')
    due_value = estimate.valid_until.strftime('%B %d, %Y') if estimate.valid_until else None
    buf = build_pdf(
        title='ESTIMATE',
        doc_type_label='Estimate',
        doc_number=estimate.estimate_number,
        entity=entity,
        items=items,
        subtotal=estimate.subtotal,
        tax_rate=estimate.tax_rate,
        tax_amount=estimate.tax_amount,
        total=estimate.total,
        notes=estimate.notes,
        date_label='Date',
        date_value=date_value,
        due_label='Valid Until',
        due_value=due_value,
        vehicle_info=vehicle_info,
    )
    return send_file(buf, mimetype='application/pdf', as_attachment=False, download_name=f'estimate_{estimate.estimate_number}.pdf')
