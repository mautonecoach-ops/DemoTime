from datetime import datetime

from app import db


class DemoEntry(db.Model):
    """Model for storing demo form submissions"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default="general")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }


class Counter(db.Model):
    """Model for tracking various counters in demos"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Integer, default=0)

    def increment(self):
        self.value += 1
        db.session.commit()
        return self.value
