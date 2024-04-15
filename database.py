from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    search_filter = db.Column(db.String)
    name = db.Column(db.String)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    link = db.Column(db.String)
    image = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    previously_searched = db.Column(db.Boolean, default=False)


def get_or_create_user(idinfo):
    email = idinfo["email"]
    # Check if user already exists in database
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create user if it doesn't exist
        user = User(name=idinfo["name"], email=email, password="defaultpassword")
        db.session.add(user)
        db.session.commit()
    return user


def create_latest_searches(items, user_id, search_filter):
    for i in items:
        search_item = Search(
            user_id=user_id,
            search_filter=search_filter,
            name=i["name"],
            price=i["price"],
            link=i["link"],
            image=i["image"],
        )
        db.session.add(search_item)
    # Commit to database
    db.session.commit()
