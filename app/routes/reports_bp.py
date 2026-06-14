from flask import Blueprint, render_template
from app.models import Customer, Invoice, Estimate, Setting
from app import db
from datetime import datetime, timedelta

bp = Blueprint('reports', __name__)

@bp.route('/reports/')
def dashboard():
    total_customers = Customer.query.count()
    total_estimates = Estimate.query.count()
    total_invoices = Invoice.query.count()
    paid_invoices = Invoice.query.filter(Invoice.status == 'paid').count()
    overdue_invoices = Invoice.query.filter(Invoice.status == 'overdue').count()

    revenue = db.session.query(db.func.coalesce(db.func.sum(Invoice.total), 0)).scalar()
    collected = db.session.query(db.func.coalesce(db.func.sum(Invoice.paid_amount), 0)).scalar()
    outstanding = float(revenue) - float(collected)

    this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.session.query(db.func.coalesce(db.func.sum(Invoice.total), 0)).filter(
        Invoice.issue_date >= this_month).scalar()

    currencies = {'USD': '$', 'EUR': '€', 'GBP': '£', 'AED': '\u20C3', 'INR': '₹', 'SAR': '﷼'}
    code = Setting.get('currency', 'USD')
    currency = currencies.get(code, '$')

    return render_template('reports/dashboard.html',
        total_customers=total_customers,
        total_estimates=total_estimates,
        total_invoices=total_invoices,
        paid_invoices=paid_invoices,
        overdue_invoices=overdue_invoices,
        revenue=float(revenue),
        collected=float(collected),
        outstanding=outstanding,
        monthly_revenue=float(monthly_revenue),
        currency=currency)
