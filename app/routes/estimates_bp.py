from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Customer, Estimate, EstimateLineItem
from app import db
from datetime import datetime

bp = Blueprint('estimates', __name__)

def _next_estimate_number():
    last = Estimate.query.order_by(Estimate.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"EST-{n:06d}"

@bp.route('/estimates/')
def list_estimates():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Estimate.query
    if status:
        query = query.filter(Estimate.status == status)
    estimates = query.order_by(Estimate.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('estimates/list.html', estimates=estimates, status=status)

@bp.route('/estimates/create', methods=['GET', 'POST'])
def create_estimate():
    if request.method == 'POST':
        est = Estimate(
            estimate_number=_next_estimate_number(),
            customer_id=request.form.get('customer_id', type=int),
            description=request.form.get('description', ''),
            notes=request.form.get('notes', ''),
            tax_rate=float(request.form.get('tax_rate', 10)) / 100,
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
    return render_template('estimates/form.html', estimate=None, customers=customers)

@bp.route('/estimates/<int:estimate_id>')
def view_estimate(estimate_id):
    estimate = Estimate.query.get_or_404(estimate_id)
    return render_template('estimates/view.html', estimate=estimate)

@bp.route('/estimates/<int:estimate_id>/edit', methods=['GET', 'POST'])
def edit_estimate(estimate_id):
    estimate = Estimate.query.get_or_404(estimate_id)
    if request.method == 'POST':
        estimate.customer_id = request.form.get('customer_id', type=int)
        estimate.description = request.form.get('description', '')
        estimate.notes = request.form.get('notes', '')
        estimate.tax_rate = float(request.form.get('tax_rate', 10)) / 100
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
    return render_template('estimates/form.html', estimate=estimate, customers=customers)

@bp.route('/estimates/<int:estimate_id>/convert', methods=['POST'])
def convert_to_invoice(estimate_id):
    from app.models import Invoice, InvoiceLineItem
    estimate = Estimate.query.get_or_404(estimate_id)
    if estimate.status == 'converted':
        flash('Estimate already converted', 'error')
        return redirect(url_for('estimates.view_estimate', estimate_id=estimate.id))

    last_inv = Invoice.query.order_by(Invoice.id.desc()).first()
    inv_num = f"INV-{(last_inv.id + 1) if last_inv else 1:06d}"
    inv = Invoice(
        invoice_number=inv_num,
        customer_id=estimate.customer_id,
        estimate_id=estimate.id,
        description=estimate.description,
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
