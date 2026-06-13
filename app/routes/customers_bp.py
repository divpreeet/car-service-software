from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Customer
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
            Customer.email.ilike(f'%{search}%') |
            Customer.vehicle_plate.ilike(f'%{search}%')
        )
    customers = query.order_by(Customer.name).paginate(page=page, per_page=20)
    return render_template('customers/list.html', customers=customers, search=search)

@bp.route('/customers/create', methods=['GET', 'POST'])
def create_customer():
    if request.method == 'POST':
        customer = Customer()
        for field in ['name', 'email', 'phone', 'address', 'city', 'state', 'zip_code',
                       'vehicle_make', 'vehicle_model', 'vehicle_plate', 'vehicle_vin', 'notes']:
            setattr(customer, field, request.form.get(field, ''))
        customer.vehicle_year = request.form.get('vehicle_year', type=int)
        db.session.add(customer)
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
        for field in ['name', 'email', 'phone', 'address', 'city', 'state', 'zip_code',
                       'vehicle_make', 'vehicle_model', 'vehicle_plate', 'vehicle_vin', 'notes']:
            setattr(customer, field, request.form.get(field, ''))
        customer.vehicle_year = request.form.get('vehicle_year', type=int)
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
