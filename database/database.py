from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import boto3


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String)
    search_filter = db.Column(db.String)
    name = db.Column(db.String)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    link = db.Column(db.String)
    image = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    previously_searched = db.Column(db.Boolean, default=False)


client = boto3.client("cognito-idp", region_name="eu-north-1")


def create_user(name, email, password):
    try:
        resp = client.sign_up(
            ClientId="2faojcgeao3gqovcsk6itafqlp",
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "name", "Value": name},
                {"Name": "email", "Value": email},
            ],
        )
    except Exception as e:
        if "Password" in str(e):
            return "Password must contain at least 8 characters"          
        return "User already exists"
    return ""


def confirm_user(email, code):
    try:
        client.confirm_sign_up(
            ClientId="2faojcgeao3gqovcsk6itafqlp",
            Username=email,
            ConfirmationCode=code,
        )
    except:
        return "Invalid code"
    return ""


def login_user(email, password):
    try:
        resp = client.initiate_auth(
            ClientId="2faojcgeao3gqovcsk6itafqlp",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except:
        return "Invalid email or password"
    return resp["AuthenticationResult"]["AccessToken"]


def get_user(token):
    try:
        resp = client.get_user(AccessToken=token)
        name = resp["UserAttributes"][2]["Value"]
        email = resp["UserAttributes"][0]["Value"]
        return name, email
    except:
        return "Expired token", None


def create_latest_searches(items, email, search_filter):
    for i in items:
        search_item = Search(
            user_email=email,
            search_filter=search_filter,
            name=i["name"],
            price=i["price"],
            link=i["link"],
            image=i["image"],
        )
        db.session.add(search_item)
    # Commit to database
    db.session.commit()
