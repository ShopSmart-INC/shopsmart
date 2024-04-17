import re  # Import regular expression module for string matching
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
)  # Import necessary modules from Flask --
from flask_session import Session  # Import Session module from Flask Session extension
import requests  # Import requests module for making HTTP requests
from bs4 import BeautifulSoup  # Import BeautifulSoup module for web scraping
from database.database import (
    db,
    create_latest_searches,
    Search,
    get_user,
    create_user,
    confirm_user,
    login_user,
)
import sqlalchemy
from datetime import timedelta

app = Flask(__name__)  # Create Flask application instance
app.config["SECRET_KEY"] = "shopsmart-secret-key"

DATABASE_URL = sqlalchemy.engine.url.URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="shopsmart",
    host="shopsmart.cp0sou4uaccg.eu-north-1.rds.amazonaws.com",
    port=5432,
    database="postgres",
)

# Configure the Postgresql database
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
# initialize the app with the extension
db.init_app(app)

app.config["SESSION_PERMANENT"] = True  # Configure session to be non-permanent
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_TYPE"] = "sqlalchemy"  # Set session type as filesystem
app.config["SESSION_SQLALCHEMY"] = DATABASE_URL  # Set session type as filesystem
app.config["SESSION_SQLALCHEMY_TABLE"] = "sessions"  # Set session type as filesystem

# Session(app)  # Initialize Flask Session extension with the app instance

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
    if request.method == "POST":
        keyword = request.form.get("keyword")  # Get keyword from search form
        if keyword:
            name, email = get_user(session.get("access_token"))
            if name == "Expired token":
                # Login again
                session["access_token"] = None
                return redirect("/")
            # User is searching for products
            items = fetch_items(keyword)  # Fetch items based on the keyword
            # Update all current user search to previously_searched before creating new searches
            Search.query.filter_by(user_email=email).update(
                {"previously_searched": True}
            )

            # Create new searches
            create_latest_searches(items, email, keyword)
            return redirect("/results")  # Redirect to results page
        else:
            email = request.form.get("email")
            password = request.form.get("password")
            resp = login_user(email, password)
            if resp == "Invalid email or password":
                return render_template("search_form.html", error=resp)
            session["access_token"] = resp
            session.permanent = True
            return redirect("/")  # Redirect to home page after login
    access_token = session.get("access_token")
    name = None
    email = None
    if access_token:
        name, email = get_user(access_token)
        if name == "Expired token":
            # Login again
            session["access_token"] = None
            return redirect("/")
    return render_template(
        "search_form.html", name=name, email=email
    )  # Render search form template


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Route for the register page.

    Returns:
        render_template: Rendered template for the home page.
        redirect: Redirects to other routes based on conditions.
    """
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        resp = create_user(name, email, password)
        if resp != "":
            return render_template(
                "register.html", error=resp
            )  # Render register template
        session["email"] = email
        return redirect("/verify")  # Redirect to verification page
    return render_template("register.html")  # Render search form template


@app.route("/verify", methods=["GET", "POST"])
def verify():
    """
    Route for the verification page.

    Returns:
        render_template: Rendered template for the home page.
        redirect: Redirects to other routes based on conditions.
    """
    if request.method == "POST":
        code = request.form.get("code")
        resp = confirm_user(session.get("email"), code)
        if resp == "Invalid code":
            return render_template(
                "verify.html", error=resp
            )  # Render register template

        return redirect("/")  # Redirect to home page
    return render_template("verify.html")  # Render search form template


@app.route("/results", methods=["GET"])
def results():
    """
    Route for displaying search results.

    Returns:
        render_template: Rendered template for displaying search results.
        redirect: Redirects to home page if user is not logged in.
    """

    # Authorize user
    access_token = session.get("access_token")
    if access_token == None:
        # Only logged in users can see search results. So if you're not logged in, you're redirected home
        return redirect("/")
    name, email = get_user(access_token)
    if name == "Expired token":
        # Login again
        session["access_token"] = None
        return redirect("/")

    currently_searched_items = Search.query.filter_by(
        user_email=email, previously_searched=False
    ).all()
    previously_searched_items = Search.query.filter_by(
        user_email=email, previously_searched=True
    ).order_by(Search.created_at.desc())[:3]
    return render_template(
        "search_results.html",
        name=name,
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
    session["access_token"] = None
    return redirect("/")  # Redirect to home page after logout


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)  # Run the Flask application in debug mode
