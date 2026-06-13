from flask import Blueprint, render_template
from app.models import Customer, Invoice
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    total_customers = Customer.query.count()
    total_invoices = Invoice.query.count()
    pending_invoices = Invoice.query.filter(Invoice.status.in_(['draft', 'sent', 'partially_paid', 'overdue'])).count()
    outstanding = db.session.query(db.func.coalesce(db.func.sum(Invoice.balance_due), 0)).scalar()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    return render_template('index.html',
        total_customers=total_customers,
        total_invoices=total_invoices,
        pending_invoices=pending_invoices,
        outstanding_amount=float(outstanding),
        recent_invoices=recent_invoices)
