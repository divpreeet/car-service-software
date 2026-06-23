from flask import Blueprint, render_template, request, send_file, url_for
from app.pdf_utils import build_settlement_pdf, _sanitize_filename
from app.models import Invoice, InvoiceLineItem, Setting
from app import db

bp = Blueprint('settlement', __name__)

def _currency():
    currencies = {'USD': '$', 'EUR': '\u20ac', 'GBP': '\u00a3', 'AED': 'AED ', 'INR': '\u20b9', 'SAR': '\ufdfc'}
    code = Setting.get('currency', 'USD')
    return currencies.get(code, '$')

def _calc(invoice, comm_pct=None, gateway_pct=None, gateway_fixed=None):
    labor_amount = db.session.query(
        db.func.coalesce(db.func.sum(
            db.func.coalesce(InvoiceLineItem.cost, InvoiceLineItem.unit_price) * InvoiceLineItem.quantity
        ), 0)
    ).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'labor',
        db.or_(InvoiceLineItem.parts_source == 'workshop', InvoiceLineItem.parts_source.is_(None))
    ).scalar() or 0

    labor_total = db.session.query(db.func.coalesce(db.func.sum(InvoiceLineItem.total), 0)).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'labor',
        db.or_(InvoiceLineItem.parts_source == 'workshop', InvoiceLineItem.parts_source.is_(None))
    ).scalar() or 0

    parts_amount = db.session.query(
        db.func.coalesce(db.func.sum(
            db.func.coalesce(InvoiceLineItem.cost, InvoiceLineItem.unit_price) * InvoiceLineItem.quantity
        ), 0)
    ).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'parts',
        InvoiceLineItem.parts_source == 'workshop'
    ).scalar() or 0

    parts_total = db.session.query(db.func.coalesce(db.func.sum(InvoiceLineItem.total), 0)).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'parts',
        InvoiceLineItem.parts_source == 'workshop'
    ).scalar() or 0

    service_amount = db.session.query(
        db.func.coalesce(db.func.sum(
            db.func.coalesce(InvoiceLineItem.cost, InvoiceLineItem.unit_price) * InvoiceLineItem.quantity
        ), 0)
    ).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'service',
        db.or_(InvoiceLineItem.parts_source == 'workshop', InvoiceLineItem.parts_source.is_(None))
    ).scalar() or 0

    service_total = db.session.query(db.func.coalesce(db.func.sum(InvoiceLineItem.total), 0)).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'service',
        db.or_(InvoiceLineItem.parts_source == 'workshop', InvoiceLineItem.parts_source.is_(None))
    ).scalar() or 0

    pickup_drop_workshop = db.session.query(db.func.coalesce(db.func.sum(InvoiceLineItem.total), 0)).filter(
        InvoiceLineItem.invoice_id == invoice.id,
        InvoiceLineItem.item_type == 'pickup_drop',
        db.or_(InvoiceLineItem.parts_source == 'workshop', InvoiceLineItem.parts_source.is_(None))
    ).scalar() or 0

    def _ob_cost_total(item_type):
        cost = db.session.query(
            db.func.coalesce(db.func.sum(
                db.func.coalesce(InvoiceLineItem.cost, 0) * InvoiceLineItem.quantity
            ), 0)
        ).filter(
            InvoiceLineItem.invoice_id == invoice.id,
            InvoiceLineItem.item_type == item_type,
            InvoiceLineItem.parts_source == 'ob'
        ).scalar() or 0
        total = db.session.query(db.func.coalesce(db.func.sum(InvoiceLineItem.total), 0)).filter(
            InvoiceLineItem.invoice_id == invoice.id,
            InvoiceLineItem.item_type == item_type,
            InvoiceLineItem.parts_source == 'ob'
        ).scalar() or 0
        return cost, total

    pickup_drop_ob_cost, pickup_drop_ob_total = _ob_cost_total('pickup_drop')
    ob_labor_cost, ob_labor_total = _ob_cost_total('labor')
    ob_parts_cost, ob_parts_total = _ob_cost_total('parts')
    ob_service_cost, ob_service_total = _ob_cost_total('service')

    ob_labor_amount = ob_labor_total - ob_labor_cost
    ob_parts_amount = ob_parts_total - ob_parts_cost
    ob_service_amount = ob_service_total - ob_service_cost

    workshop_discount = invoice.discount_workshop or 0
    ob_discount = invoice.discount_ob or 0

    job_amount = labor_amount + parts_amount + service_amount
    net_job = job_amount - workshop_discount - ob_discount
    tax_rate = 0.05
    vat = net_job * tax_rate
    customer_payment = net_job + vat

    gw_pct = (gateway_pct if gateway_pct is not None else 0.025)
    gw_fixed = (gateway_fixed if gateway_fixed is not None else 1)
    gateway = (customer_payment * gw_pct) + gw_fixed
    vat_on_gateway = gateway * 0.05
    total_gateway = gateway + vat_on_gateway

    payment_received_by_ob = customer_payment - total_gateway

    if comm_pct is None:
        comm_pct = {'labour': 0.2, 'spares': 0.1, 'service': 0.1}

    labour_commission = labor_amount * comm_pct['labour']
    spares_commission = parts_amount * comm_pct['spares']
    service_commission = service_amount * comm_pct['service']
    total_ob_comm = labour_commission + spares_commission + service_commission - ob_discount
    vat_on_ob_comm = total_ob_comm * 0.05
    ob_comm_with_vat = total_ob_comm + vat_on_ob_comm

    job_to_workshop = net_job - (gateway + total_ob_comm)
    vat_to_workshop = job_to_workshop * 0.05
    total_to_workshop = job_to_workshop + vat_to_workshop + pickup_drop_workshop

    return {
        'gateway_pct': gw_pct,
        'gateway_fixed': gw_fixed,
        'labor_amount': labor_amount,
        'labor_total': labor_total,
        'parts_amount': parts_amount,
        'parts_total': parts_total,
        'service_amount': service_amount,
        'service_total': service_total,
        'job_amount': job_amount,
        'workshop_discount': workshop_discount,
        'ob_discount': ob_discount,
        'net_job': net_job,
        'vat': vat,
        'customer_payment': customer_payment,
        'gateway': gateway,
        'vat_on_gateway': vat_on_gateway,
        'total_gateway': total_gateway,
        'payment_received_by_ob': payment_received_by_ob,
        'labour_commission': labour_commission,
        'spares_commission': spares_commission,
        'service_commission': service_commission,
        'comm_pct': comm_pct,
        'total_ob_comm': total_ob_comm,
        'vat_on_ob_comm': vat_on_ob_comm,
        'ob_comm_with_vat': ob_comm_with_vat,
        'job_to_workshop': job_to_workshop,
        'vat_to_workshop': vat_to_workshop,
        'pickup_drop_workshop': pickup_drop_workshop,
        'pickup_drop_ob': pickup_drop_ob_total,
        'pickup_drop_ob_cost': pickup_drop_ob_cost,
        'pickup_drop_ob_total': pickup_drop_ob_total,
        'ob_labor_cost': ob_labor_cost,
        'ob_labor_total': ob_labor_total,
        'ob_labor_amount': ob_labor_amount,
        'ob_parts_cost': ob_parts_cost,
        'ob_parts_total': ob_parts_total,
        'ob_parts_amount': ob_parts_amount,
        'ob_service_cost': ob_service_cost,
        'ob_service_total': ob_service_total,
        'ob_service_amount': ob_service_amount,
        'total_to_workshop': total_to_workshop,
    }

@bp.route('/settlement', methods=['GET'])
def settlement_page():
    invoices = Invoice.query.order_by(Invoice.invoice_number.desc()).all()
    cur = _currency()
    pre_selected = request.args.get('invoice_id', type=int)
    if pre_selected:
        invoice = Invoice.query.get(pre_selected)
        if invoice:
            result = _calc(invoice)
            return render_template('settlement/view.html', invoices=invoices, currency=cur, result=result, selected_id=invoice.id, invoice=invoice)
    return render_template('settlement/view.html', invoices=invoices, currency=cur, result=None)

@bp.route('/settlement/calculate', methods=['POST'])
def calculate():
    invoice_id = request.form.get('invoice_id', type=int)
    invoice = Invoice.query.get_or_404(invoice_id)
    comm_pct = {
        'labour': float(request.form.get('comm_labour', 20)) / 100,
        'spares': float(request.form.get('comm_spares', 10)) / 100,
        'service': float(request.form.get('comm_service', 10)) / 100,
    }
    gw_pct = float(request.form.get('gateway_pct', 2.5)) / 100
    gw_fixed = float(request.form.get('gateway_fixed', 1))
    result = _calc(invoice, comm_pct, gw_pct, gw_fixed)
    invoices = Invoice.query.order_by(Invoice.invoice_number.desc()).all()
    cur = _currency()
    return render_template('settlement/view.html', invoices=invoices, currency=cur, result=result, selected_id=invoice_id, invoice=invoice)

@bp.route('/settlement/pdf/<int:invoice_id>', methods=['GET'])
def settlement_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    comm_pct = {
        'labour': float(request.args.get('comm_labour', 20)) / 100,
        'spares': float(request.args.get('comm_spares', 10)) / 100,
        'service': float(request.args.get('comm_service', 10)) / 100,
    }
    result = _calc(invoice, comm_pct)
    cur = _currency()
    buf = build_settlement_pdf(invoice, result, cur)
    safe_num = _sanitize_filename(invoice.invoice_number)
    safe_name = _sanitize_filename(invoice.customer.name).replace(' ', '_')
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'{safe_num}_Settlement.pdf')
