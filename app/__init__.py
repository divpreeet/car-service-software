from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
import os

db = SQLAlchemy()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    from app.models import Customer, Estimate, EstimateLineItem, Invoice, InvoiceLineItem, Payment, Setting
    
    with app.app_context():
        db.create_all()
    
    # Import and register blueprints
    from app.routes.main_bp import bp as main_bp
    from app.routes.customers_bp import bp as customers_bp
    from app.routes.estimates_bp import bp as estimates_bp
    from app.routes.invoices_bp import bp as invoices_bp
    from app.routes.payments_bp import bp as payments_bp
    from app.routes.reports_bp import bp as reports_bp
    from app.routes.settings_bp import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(estimates_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    
    return app
