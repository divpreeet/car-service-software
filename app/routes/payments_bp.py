from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Invoice, Payment
from app import db
from datetime import datetime

bp = Blueprint('payments', __name__)

@bp.route('/payments/record/<int:invoice_id>', methods=['GET', 'POST'])
def record_payment(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            flash('Amount must be greater than 0', 'error')
            return render_template('payments/record.html', invoice=invoice)
        if amount > invoice.balance_due:
            flash('Amount exceeds balance due', 'error')
            return render_template('payments/record.html', invoice=invoice)
        payment = Payment(
            invoice_id=invoice.id,
            amount=amount,
            payment_method=request.form.get('payment_method', 'cash'),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
        )
        invoice.paid_amount += amount
        invoice.balance_due = invoice.total - invoice.paid_amount
        invoice.update_status()
        db.session.add(payment)
        db.session.commit()
        flash('Payment recorded successfully', 'success')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
    return render_template('payments/record.html', invoice=invoice)

@bp.route('/payments/<int:payment_id>/delete', methods=['POST'])
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    invoice = payment.invoice
    invoice.paid_amount -= payment.amount
    invoice.balance_due = invoice.total - invoice.paid_amount
    invoice.update_status()
    db.session.delete(payment)
    db.session.commit()
    flash('Payment deleted successfully', 'success')
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
