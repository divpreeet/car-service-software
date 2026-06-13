from app import db
from datetime import datetime, timedelta

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    estimate_id = db.Column(db.Integer, db.ForeignKey('estimates.id'), nullable=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue, partially_paid
    subtotal = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0.1)
    tax_amount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    balance_due = db.Column(db.Float, default=0)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    payment_terms = db.Column(db.String(50))  # net15, net30, net60
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'
    
    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.line_items)
        self.tax_amount = self.subtotal * self.tax_rate
        self.total = self.subtotal + self.tax_amount
        self.balance_due = self.total - self.paid_amount
        self.update_status()
    
    def update_status(self):
        if self.balance_due == 0 and self.paid_amount > 0:
            self.status = 'paid'
        elif self.balance_due < self.total and self.balance_due > 0 and self.paid_amount > 0:
            self.status = 'partially_paid'
        elif self.balance_due > 0 and self.due_date and datetime.utcnow() > self.due_date:
            self.status = 'overdue'
    
    def set_due_date(self, payment_terms):
        term_days = {'net15': 15, 'net30': 30, 'net60': 60}.get(payment_terms, 30)
        self.due_date = self.issue_date + timedelta(days=term_days)
        self.payment_terms = payment_terms
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name,
            'estimate_id': self.estimate_id,
            'description': self.description,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total': float(self.total),
            'paid_amount': float(self.paid_amount),
            'balance_due': float(self.balance_due),
            'issue_date': self.issue_date.isoformat(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'payment_terms': self.payment_terms,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'line_items': [item.to_dict() for item in self.line_items],
            'payments': [payment.to_dict() for payment in self.payments]
        }

class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    item_type = db.Column(db.String(50))  # labor, parts, service
    quantity = db.Column(db.Float, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<InvoiceLineItem {self.description}>'
    
    def calculate_total(self):
        self.total = self.quantity * self.unit_price
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'item_type': self.item_type,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total': float(self.total),
            'notes': self.notes
        }
