from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Customer, Vehicle
from app import db

bp = Blueprint('customers', __name__)

@bp.route('/customers/')
def list_customers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Customer.query
    if search:
        query = query.filter(
            Customer.name.ilike(f'%{search}%') |
            Customer.phone.ilike(f'%{search}%') |
            Customer.email.ilike(f'%{search}%')
        )
    customers = query.order_by(Customer.name).paginate(page=page, per_page=20)
    return render_template('customers/list.html', customers=customers, search=search)

@bp.route('/customers/create', methods=['GET', 'POST'])
def create_customer():
    if request.method == 'POST':
        customer = Customer()
        for field in ['name', 'email', 'phone', 'address', 'city', 'state', 'zip_code', 'notes']:
            setattr(customer, field, request.form.get(field, ''))
        db.session.add(customer)
        db.session.flush()

        count = int(request.form.get('vehicles_count', 0))
        for i in range(count):
            make = request.form.get(f'vehicles[{i}][make]', '').strip()
            model = request.form.get(f'vehicles[{i}][model]', '').strip()
            if not make and not model:
                continue
            v = Vehicle(
                customer_id=customer.id,
                make=make,
                model=model,
                year=request.form.get(f'vehicles[{i}][year]', type=int),
                vin=request.form.get(f'vehicles[{i}][vin]', '').strip(),
                plate=request.form.get(f'vehicles[{i}][plate]', '').strip(),
            )
            db.session.add(v)
        db.session.commit()
        flash('Customer created successfully', 'success')
        return redirect(url_for('customers.list_customers'))
    return render_template('customers/form.html', customer=None)

@bp.route('/customers/<int:customer_id>')
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customers/view.html', customer=customer)

@bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        for field in ['name', 'email', 'phone', 'address', 'city', 'state', 'zip_code', 'notes']:
            setattr(customer, field, request.form.get(field, ''))

        existing_ids = {v.id for v in customer.vehicles}
        submitted_ids = set()
        count = int(request.form.get('vehicles_count', 0))
        for i in range(count):
            vid = request.form.get(f'vehicles[{i}][id]', type=int)
            make = request.form.get(f'vehicles[{i}][make]', '').strip()
            model = request.form.get(f'vehicles[{i}][model]', '').strip()
            if not make and not model and not vid:
                continue
            if vid and vid in existing_ids:
                v = Vehicle.query.get(vid)
                if v:
                    v.make = make
                    v.model = model
                    v.year = request.form.get(f'vehicles[{i}][year]', type=int)
                    v.vin = request.form.get(f'vehicles[{i}][vin]', '').strip()
                    v.plate = request.form.get(f'vehicles[{i}][plate]', '').strip()
                    submitted_ids.add(vid)
            else:
                v = Vehicle(
                    customer_id=customer.id,
                    make=make,
                    model=model,
                    year=request.form.get(f'vehicles[{i}][year]', type=int),
                    vin=request.form.get(f'vehicles[{i}][vin]', '').strip(),
                    plate=request.form.get(f'vehicles[{i}][plate]', '').strip(),
                )
                db.session.add(v)

        for v in customer.vehicles:
            if v.id not in submitted_ids:
                db.session.delete(v)
        db.session.commit()
        flash('Customer updated successfully', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer.id))
    return render_template('customers/form.html', customer=customer)

@bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully', 'success')
    return redirect(url_for('customers.list_customers'))
