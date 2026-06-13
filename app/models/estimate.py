from app import db
from datetime import datetime
from decimal import Decimal

class Estimate(db.Model):
    __tablename__ = 'estimates'
    
    id = db.Column(db.Integer, primary_key=True)
    estimate_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, approved, rejected, converted
    subtotal = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0.1)  # 10% default
    tax_amount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    valid_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = db.relationship('EstimateLineItem', backref='estimate', lazy=True, cascade='all, delete-orphan')
    invoice = db.relationship('Invoice', uselist=False, backref='estimate', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Estimate {self.estimate_number}>'
    
    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.line_items)
        self.tax_amount = self.subtotal * self.tax_rate
        self.total = self.subtotal + self.tax_amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'estimate_number': self.estimate_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name,
            'description': self.description,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total': float(self.total),
            'notes': self.notes,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'line_items': [item.to_dict() for item in self.line_items]
        }

class EstimateLineItem(db.Model):
    __tablename__ = 'estimate_line_items'
    
    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey('estimates.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    item_type = db.Column(db.String(50))  # labor, parts, service
    quantity = db.Column(db.Float, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<EstimateLineItem {self.description}>'
    
    def calculate_total(self):
        self.total = self.quantity * self.unit_price
    
    def to_dict(self):
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'description': self.description,
            'item_type': self.item_type,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total': float(self.total),
            'notes': self.notes
        }
