from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Workshop
from app import db

bp = Blueprint('workshops', __name__)

@bp.route('/workshops/')
def list_workshops():
    workshops = Workshop.query.order_by(Workshop.name).all()
    return render_template('workshops/list.html', workshops=workshops)

@bp.route('/workshops/create', methods=['GET', 'POST'])
def create_workshop():
    if request.method == 'POST':
        w = Workshop()
        for field in ['name', 'area', 'city', 'emirate_state', 'country', 'zip_code', 'vat_number', 'email', 'mobile_number', 'phone_number', 'whatsapp_number']:
            setattr(w, field, request.form.get(field, ''))
        db.session.add(w)
        db.session.commit()
        flash('Workshop created successfully', 'success')
        return redirect(url_for('workshops.list_workshops'))
    return render_template('workshops/form.html', workshop=None)

@bp.route('/workshops/<int:workshop_id>/edit', methods=['GET', 'POST'])
def edit_workshop(workshop_id):
    w = Workshop.query.get_or_404(workshop_id)
    if request.method == 'POST':
        for field in ['name', 'area', 'city', 'emirate_state', 'country', 'zip_code', 'vat_number', 'email', 'mobile_number', 'phone_number', 'whatsapp_number']:
            setattr(w, field, request.form.get(field, ''))
        db.session.commit()
        flash('Workshop updated successfully', 'success')
        return redirect(url_for('workshops.list_workshops'))
    return render_template('workshops/form.html', workshop=w)

@bp.route('/workshops/<int:workshop_id>/delete', methods=['POST'])
def delete_workshop(workshop_id):
    w = Workshop.query.get_or_404(workshop_id)
    db.session.delete(w)
    db.session.commit()
    flash('Workshop deleted successfully', 'success')
    return redirect(url_for('workshops.list_workshops'))
