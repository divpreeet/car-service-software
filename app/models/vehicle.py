from app import db

class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    vin = db.Column(db.String(50))
    plate = db.Column(db.String(50))
    notes = db.Column(db.Text)

    def __repr__(self):
        parts = []
        if self.year:
            parts.append(str(self.year))
        if self.make:
            parts.append(self.make)
        if self.model:
            parts.append(self.model)
        if self.plate:
            parts.append(f'({self.plate})')
        return ' '.join(parts) if parts else f'Vehicle #{self.id}'

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'vin': self.vin,
            'plate': self.plate,
            'notes': self.notes,
        }
