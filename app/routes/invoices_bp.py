from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Invoice, InvoiceLineItem
from app import db
from datetime import datetime

bp = Blueprint('invoices', __name__)

def _next_invoice_number():
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"INV-{n:06d}"

@bp.route('/invoices/')
def list_invoices():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Invoice.query
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.order_by(Invoice.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('invoices/list.html', invoices=invoices, status=status)

@bp.route('/invoices/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/view.html', invoice=invoice)

@bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if request.method == 'POST':
        invoice.description = request.form.get('description', '')
        invoice.notes = request.form.get('notes', '')
        invoice.tax_rate = float(request.form.get('tax_rate', 10)) / 100
        invoice.payment_terms = request.form.get('payment_terms', 'net30')
        invoice.set_due_date(invoice.payment_terms)

        for li in invoice.line_items:
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
            li = InvoiceLineItem(
                invoice_id=invoice.id, description=desc, quantity=qty,
                unit_price=price, total=qty * price, item_type=item_type)
            db.session.add(li)
            subtotal += li.total
        invoice.subtotal = subtotal
        invoice.tax_amount = subtotal * invoice.tax_rate
        invoice.total = subtotal + invoice.tax_amount
        invoice.balance_due = invoice.total - invoice.paid_amount
        invoice.update_status()
        db.session.commit()
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
    return render_template('invoices/form.html', invoice=invoice)

@bp.route('/invoices/<int:invoice_id>/mark-sent', methods=['POST'])
def mark_sent(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'sent'
    if not invoice.due_date:
        invoice.set_due_date(invoice.payment_terms or 'net30')
    db.session.commit()
    flash('Invoice marked as sent', 'success')
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
