from app import db

class Workshop(db.Model):
    __tablename__ = 'workshops'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    area = db.Column(db.String(200))
    city = db.Column(db.String(100))
    emirate_state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    vat_number = db.Column(db.String(50))
    email = db.Column(db.String(120))
    mobile_number = db.Column(db.String(50))
    phone_number = db.Column(db.String(50))
    whatsapp_number = db.Column(db.String(50))

    def __repr__(self):
        return self.name or f'Workshop #{self.id}'
