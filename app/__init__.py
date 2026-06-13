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
    
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from app.routes import customers_bp, estimates_bp, invoices_bp, payments_bp, reports_bp, main_bp
    
    app.register_blueprint(main_bp.bp)
    app.register_blueprint(customers_bp.bp)
    app.register_blueprint(estimates_bp.bp)
    app.register_blueprint(invoices_bp.bp)
    app.register_blueprint(payments_bp.bp)
    app.register_blueprint(reports_bp.bp)
    
    return app
