from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Setting
from app import db

bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_FIELDS = [
    ('business_name', 'Business Name', 'text'),
    ('business_address', 'Address', 'text'),
    ('business_phone', 'Phone', 'text'),
    ('business_email', 'Email', 'email'),
    ('default_tax_rate', 'Default Tax Rate (%)', 'number'),
    ('default_payment_terms', 'Default Payment Terms', 'select'),
    ('currency_symbol', 'Currency Symbol', 'text'),
    ('estimate_prefix', 'Estimate Number Prefix', 'text'),
    ('invoice_prefix', 'Invoice Number Prefix', 'text'),
]

@bp.route('/', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        for key, _, _ in SETTINGS_FIELDS:
            val = request.form.get(key, '').strip()
            Setting.set(key, val)
        flash('Settings saved successfully', 'success')
        return redirect(url_for('settings.edit'))

    settings = {}
    for key, label, ftype in SETTINGS_FIELDS:
        settings[key] = {'label': label, 'type': ftype, 'value': Setting.get(key)}
    return render_template('settings/form.html', settings=settings)
