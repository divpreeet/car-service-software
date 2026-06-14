import os, json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from markupsafe import Markup
from app.models import Setting
from app import db
from werkzeug.utils import secure_filename

bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_FIELDS = [
    ('business_name', 'Business Name', 'text'),
    ('business_address', 'Address', 'text'),
    ('business_phone', 'Phone', 'text'),
    ('business_email', 'Email', 'email'),
    ('tax_number', 'Tax Number', 'text'),
    ('default_tax_rate', 'Default Tax Rate (%)', 'number'),
    ('default_payment_terms', 'Default Payment Terms', 'select'),
    ('currency', 'Currency', 'select'),
    ('estimate_prefix', 'Estimate Number Prefix', 'text'),
    ('invoice_prefix', 'Invoice Number Prefix', 'text'),
]

CURRENCIES = [('USD', '$'), ('EUR', '€'), ('GBP', '£'), ('AED', Markup('<img src="/static/images/aed.svg" alt="AED" style="height:1em;vertical-align:middle"> AED')), ('INR', '₹'), ('SAR', '﷼')]
PAYMENT_TERMS = [('immediate', 'Immediate'), ('net15', 'Net 15'), ('net30', 'Net 30'), ('net60', 'Net 60')]

LAYOUT_POSITIONS = [
    ('header_left', 'Header Left'),
    ('header_center', 'Header Center'),
    ('header_right', 'Header Right'),
    ('body', 'Body'),
    ('footer_left', 'Footer Left'),
    ('footer_center', 'Footer Center'),
    ('footer_right', 'Footer Right'),
]

LAYOUT_ELEMENTS = [
    ('logo', 'Logo', ['header_left', 'header_center', 'header_right']),
    ('company_name', 'Company Name', ['header_left', 'header_center', 'header_right', 'footer_left', 'footer_center', 'footer_right']),
    ('company_address', 'Company Address', ['header_left', 'header_center', 'header_right', 'footer_left', 'footer_center', 'footer_right']),
    ('company_phone', 'Company Phone', ['header_left', 'header_center', 'header_right', 'footer_left', 'footer_center', 'footer_right']),
    ('doc_info', 'Doc Title & Number', ['header_left', 'header_center', 'header_right']),
    ('date', 'Date', ['header_left', 'header_center', 'header_right', 'body']),
    ('due_date', 'Due Date', ['header_left', 'header_center', 'header_right', 'body']),
    ('tax_number', 'Tax Number', ['body']),
    ('bill_to', 'Bill To', ['body']),
    ('vehicle_info', 'Vehicle Info', ['body']),
    ('line_items', 'Line Items Table', ['body']),
    ('totals', 'Totals', ['body']),
    ('notes', 'Notes', ['body']),
    ('company_info', 'Footer Company Info', ['footer_left', 'footer_center', 'footer_right']),
    ('page_number', 'Page Number', ['footer_left', 'footer_center', 'footer_right']),
]

def _default_layout():
    return json.dumps({
        'logo': 'header_left',
        'company_name': 'header_left',
        'doc_info': 'header_right',
        'date': 'body',
        'due_date': 'body',
        'tax_number': 'body',
        'bill_to': 'body',
        'vehicle_info': 'body',
        'line_items': 'body',
        'totals': 'body',
        'notes': 'body',
        'company_info': 'footer_center',
        'page_number': 'footer_right',
    })

@bp.route('/design', methods=['GET', 'POST'])
def design():
    if request.method == 'POST':
        layout = {}
        for key, _, _ in LAYOUT_ELEMENTS:
            val = request.form.get(f'pos_{key}', '').strip()
            if val:
                layout[key] = val
        Setting.set('invoice_layout', json.dumps(layout))
        flash('Invoice design saved successfully', 'success')
        return redirect(url_for('settings.design'))

    raw = Setting.get('invoice_layout')
    try:
        current_layout = json.loads(raw) if raw else json.loads(_default_layout())
    except (json.JSONDecodeError, TypeError):
        current_layout = json.loads(_default_layout())
    return render_template('settings/design.html',
        elements=LAYOUT_ELEMENTS, positions=LAYOUT_POSITIONS, layout=current_layout)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        for key, _, _ in SETTINGS_FIELDS:
            val = request.form.get(key, '').strip()
            Setting.set(key, val)

        logo = request.files.get('logo')
        if logo and logo.filename and allowed_file(logo.filename):
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            ext = logo.filename.rsplit('.', 1)[1].lower()
            filename = f'logo.{ext}'
            logo.save(os.path.join(upload_dir, filename))
            Setting.set('logo', filename)

        if request.form.get('remove_logo'):
            Setting.set('logo', '')
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            for f in os.listdir(upload_dir):
                if f.startswith('logo.'):
                    os.remove(os.path.join(upload_dir, f))

        flash('Settings saved successfully', 'success')
        return redirect(url_for('settings.edit'))

    settings = {}
    for key, label, ftype in SETTINGS_FIELDS:
        settings[key] = {'label': label, 'type': ftype, 'value': Setting.get(key)}
    settings['currencies'] = CURRENCIES
    settings['payment_terms'] = PAYMENT_TERMS
    settings['logo'] = Setting.get('logo')
    return render_template('settings/form.html', settings=settings)
