import re  # Import regular expression module for string matching
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
)  # Import necessary modules from Flask
from flask_session import Session  # Import Session module from Flask Session extension
from google.auth.transport import (
    requests as google_requests,
)  # Import necessary modules from Google Auth
from google.oauth2 import id_token  # Import id_token module from Google OAuth2
import requests  # Import requests module for making HTTP requests
from bs4 import BeautifulSoup  # Import BeautifulSoup module for web scraping
from .database import db, create_latest_searches, Search, get_or_create_user
import sqlalchemy

app = Flask(__name__)  # Create Flask application instance
app.config["SESSION_PERMANENT"] = False  # Configure session to be non-permanent
app.config["SESSION_TYPE"] = "filesystem"  # Set session type as filesystem
Session(app)  # Initialize Flask Session extension with the app instance

# Configure the Postgresql database
app.config["SQLALCHEMY_DATABASE_URI"] = sqlalchemy.engine.url.URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="shopsmart_db_password",
    host="shopsmart-db.cp0sou4uaccg.eu-north-1.rds.amazonaws.com",
    port=5432,
    database="postgres",
)
# initialize the app with the extension
db.init_app(app)

# Create all tables
with app.app_context():
    db.create_all()


def fetch_site_1_items(keyword):
    """
    Function to fetch items from site 1 based on a keyword.

    Args:
        keyword (str): Keyword to search for items.

    Returns:
        list: List of dictionaries containing item details.
    """
    url = (
        "https://swiftronics.ca/search?type=product&q=" + keyword
    )  # Construct URL for site 1

    items = []  # Initialize empty list to store items

    response = requests.get(url).text  # Get HTML response from the URL
    soup = BeautifulSoup(response, "html.parser")  # Parse HTML using BeautifulSoup

    # Find all product containers
    product_containers = soup.find_all("div", class_="inner product-item")
    for container in product_containers:
        try:
            # Extract item name and price
            image_container = container.find("div", class_="product-top")
            image_sub_container = image_container.find("a")
            link = image_sub_container["href"]
            image = image_sub_container.find("img")["src"]

            product_info_container = container.find("div", class_="product-bottom")
            name = product_info_container.find("a").find("span").text.strip()
            price = (
                product_info_container.find("div", class_="price-regular")
                .find("span")
                .text.strip()
            )
            price = re.findall(r"(?:[$]{1}[,\d]+.?\d*)", price)[0][1:]
            # Append item details to the list
            items.append(
                {
                    "name": name,
                    "price": price.replace("$", "").replace(",", ""),
                    "link": f"https://swiftronics.ca{link}",
                    "image": image,
                }
            )
        except Exception as e:
            print(e)
            # Skip if any attribute error occurs
            pass
    return items


def fetch_site_2_items(keyword):
    """
    Function to fetch items from site 2 based on a keyword.

    Args:
        keyword (str): Keyword to search for items.

    Returns:
        list: List of dictionaries containing item details.
    """
    url = "https://www.newegg.ca/p/pl?d=" + keyword  # Construct URL for site 2

    items = []  # Initialize empty list to store items

    response = requests.get(url).text  # Get HTML response from the URL
    soup = BeautifulSoup(response, "html.parser")  # Parse HTML using BeautifulSoup

    # Find all product containers
    product_containers = soup.find_all("div", class_="item-container")
    for container in product_containers:
        try:
            # Extract item name and price
            link = container.find("a")["href"]
            image = container.find("img")["src"]

            name = container.find("a", class_="item-title").text.strip()
            price = (
                container.find("li", class_="price-current").find("strong").text.strip()
            )
            price = price.replace(",", "")
            # Append item details to the list
            items.append({"name": name, "price": price, "link": link, "image": image})
        except Exception as e:
            # Skip if any attribute error occurs
            pass
    return items


def fetch_items(keyword):
    """
    Function to fetch items from both sites based on a keyword.

    Args:
        keyword (str): Keyword to search for items.

    Returns:
        list: List of dictionaries containing item details.
    """
    items_from_site_1 = fetch_site_1_items(keyword)  # Fetch items from site 1
    items_from_site_2 = fetch_site_2_items(keyword)  # Fetch items from site 2
    items = items_from_site_1 + items_from_site_2  # Combine items from both sites

    # Sort items by price (ascending)
    sorted_items = sorted(items, key=lambda x: float(x["price"]))
    return sorted_items


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Route for the home page.

    Returns:
        render_template: Rendered template for the home page.
        redirect: Redirects to other routes based on conditions.
    """
    token = request.args.get("auth_token")  # Get authentication token from request
    if token:
        # User is logging in
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
        # Get or create user and add the details to session
        user = get_or_create_user(idinfo)
        session["name"] = user.name
        session["user_id"] = user.id
        return redirect("/")  # Redirect to home page after login
    elif request.method == "POST":
        user_id = session.get("user_id")
        keyword = request.form.get("keyword")  # Get keyword from search form
        # User is searching for products
        items = fetch_items(keyword)  # Fetch items based on the keyword
        # Update all current user search to previously_searched before creating new searches
        Search.query.filter_by(user_id=session.get("user_id")).update(
            {"previously_searched": True}
        )

        # Create new searches
        create_latest_searches(items, user_id, keyword)
        return redirect("/results")  # Redirect to results page
    return render_template("search_form.html")  # Render search form template


@app.route("/results", methods=["GET"])
def results():
    """
    Route for displaying search results.

    Returns:
        render_template: Rendered template for displaying search results.
        redirect: Redirects to home page if user is not logged in.
    """
    user_id = session.get("user_id")
    if user_id == None:
        # Only logged in users can see search results. So if you're not logged in, you're redirected home
        return redirect("/")
    currently_searched_items = Search.query.filter_by(
        user_id=user_id, previously_searched=False
    ).all()
    previously_searched_items = Search.query.filter_by(
        user_id=user_id, previously_searched=True
    ).order_by(Search.created_at)[:3]
    return render_template(
        "search_results.html",
        currently_searched_items=currently_searched_items,
        previously_searched_items=previously_searched_items,
    )  # Render search results template


@app.route("/logout", methods=["GET"])
def logout():
    """
    Route for logging out the user.

    Returns:
        redirect: Redirects to home page after logout.
    """
    # Clear user's session data
    session["name"] = None
    session["user_id"] = None
    return redirect("/")  # Redirect to home page after logout


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)  # Run the Flask application in debug mode
