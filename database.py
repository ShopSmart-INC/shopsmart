import requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import boto3, base64
from botocore.exceptions import BotoCoreError, ClientError


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String)
    search_keyword = db.Column(db.String)
    name = db.Column(db.String)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    link = db.Column(db.String)
    image = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    previously_searched = db.Column(db.Boolean, default=False)


def generate_access_token(code):
    token_url = "https://shopsmart.auth.eu-north-1.amazoncognito.com/oauth2/token"
    message = bytes(
        f"7v0mgimfcvhgvh3ib16j5toad9:d49rk8pv0s5d77omoor10ftohtitlfl43rs4didf4d1niakeisf",
        "utf-8",
    )
    secret_hash = base64.b64encode(message).decode()
    payload = {
        "grant_type": "authorization_code",
        "client_id": "7v0mgimfcvhgvh3ib16j5toad9",
        "code": code,
        "redirect_uri": "http://localhost:5000",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {secret_hash}",
    }
    resp = requests.post(token_url, params=payload, headers=headers)
    data = resp.json()
    return data.get("access_token")


def get_user_via_access_token(token):
   client = boto3.client("cognito-idp", region_name="eu-north-1")


   try:
       response = client.get_user(AccessToken=token)
       data = response["UserAttributes"]
       email = data[0]["Value"]
       name = data[2]["Value"]
       return name, email
   except client.exceptions.ExpiredCodeException:
       # Handle the expired token case
       print("The provided token has expired.")
       return None, None
   except ClientError as e:
       # Handle other possible exceptions such as NotAuthorizedException, etc.
       print(f"An error occurred: {e}")
       return None, None


def create_latest_searches(items, user_email, search_filter):
    for i in items:
        search_item = Search(
            user_email=user_email,
            search_keyword=search_filter,
            name=i["name"],
            price=i["price"],
            link=i["link"],
            image=i["image"],
        )
        db.session.add(search_item)
    # Commit to database
    db.session.commit()
