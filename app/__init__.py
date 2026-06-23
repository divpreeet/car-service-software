import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
import os

db = SQLAlchemy()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
        app = Flask(__name__, instance_path=os.path.join(base, 'instance'), instance_relative_config=True)
    else:
        app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    from app.models import Customer, Vehicle, Estimate, EstimateLineItem, Invoice, InvoiceLineItem, Payment, Setting, Workshop
    
    with app.app_context():
        db.create_all()
        # Migrate existing DBs
        for stmt in [
            'ALTER TABLE invoices ADD COLUMN odometer_reading VARCHAR(50)',
            'CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, make VARCHAR(100), model VARCHAR(100), year INTEGER, vin VARCHAR(50), plate VARCHAR(50), notes TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id))',
            'ALTER TABLE estimates ADD COLUMN vehicle_id INTEGER REFERENCES vehicles(id)',
            'ALTER TABLE invoices ADD COLUMN vehicle_id INTEGER REFERENCES vehicles(id)',
            'ALTER TABLE invoices ADD COLUMN workshop_id INTEGER REFERENCES workshops(id)',
            'ALTER TABLE workshops ADD COLUMN area VARCHAR(200)',
            'ALTER TABLE workshops ADD COLUMN city VARCHAR(100)',
            'ALTER TABLE workshops ADD COLUMN emirate_state VARCHAR(100)',
            'ALTER TABLE workshops ADD COLUMN country VARCHAR(100)',
            'ALTER TABLE workshops ADD COLUMN zip_code VARCHAR(20)',
            'ALTER TABLE estimate_line_items ADD COLUMN parts_type VARCHAR(20)',
            'ALTER TABLE invoice_line_items ADD COLUMN parts_type VARCHAR(20)',
            'ALTER TABLE estimate_line_items ADD COLUMN parts_source VARCHAR(20)',
            'ALTER TABLE invoice_line_items ADD COLUMN parts_source VARCHAR(20)',
            'ALTER TABLE estimates ADD COLUMN discount_workshop FLOAT DEFAULT 0',
            'ALTER TABLE estimates ADD COLUMN discount_ob FLOAT DEFAULT 0',
            'ALTER TABLE invoices ADD COLUMN discount_workshop FLOAT DEFAULT 0',
            'ALTER TABLE invoices ADD COLUMN discount_ob FLOAT DEFAULT 0',
        ]:
            try:
                db.session.execute(db.text(stmt))
                db.session.commit()
            except Exception:
                db.session.rollback()
    
    # Import and register blueprints
    from app.routes.main_bp import bp as main_bp
    from app.routes.customers_bp import bp as customers_bp
    from app.routes.estimates_bp import bp as estimates_bp
    from app.routes.invoices_bp import bp as invoices_bp
    from app.routes.payments_bp import bp as payments_bp
    from app.routes.reports_bp import bp as reports_bp
    from app.routes.settings_bp import bp as settings_bp
    from app.routes.workshops_bp import bp as workshops_bp
    from app.routes.settlement_bp import bp as settlement_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(estimates_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(workshops_bp)
    app.register_blueprint(settlement_bp)
    
    return app
