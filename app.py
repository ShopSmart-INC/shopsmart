import re
from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def fetch_items(keyword):
    url = "https://swiftronics.ca/search?type=product&q=" + keyword

    items = []

    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    
    # Find all product containers
    product_containers = soup.find_all('div', class_="inner product-item")
    for container in product_containers:
        try:
            # Extract item name and price
            image_container = container.find("div", class_="product-top")
            image_sub_container = image_container.find("a")
            link = image_sub_container["href"]
            image = image_sub_container.find("img")["src"]

            product_info_container = container.find("div", class_="product-bottom")
            name = product_info_container.find("a").find("span").text.strip()
            price = product_info_container.find("div", class_="price-regular").find("span").text.strip()
            price = re.findall(r'(?:[$]{1}[,\d]+.?\d*)', price)[0][1:]
            # Append item details to the list
            items.append({'name': name, 'price': price, "link": f"https://swiftronics.ca{link}", "image": image})
        except Exception as e:
            print(e)
            # Skip if any attribute error occurs
            pass

    # Sort items by price (ascending)
    sorted_items = sorted(items, key=lambda x: float(x['price'].replace('$', '').replace(',', '')))
    return sorted_items

@app.route('/', methods=['GET', 'POST'])
def index():
    token = request.args.get('auth_token')
    if token:
        # User is logging in
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
        session["name"] = idinfo["name"]
        return redirect("/")
    elif request.method == 'POST':
        keyword = request.form.get('keyword')        
        # User is searching for products
        items = fetch_items(keyword)
        # print(items)
        session["previous_search_results"] = session.get("current_search_results", [])[:3] # To show at most 3 of former search results
        session["current_search_results"] = items
        return redirect('/results')
    return render_template('search_form.html')

@app.route('/results', methods=['GET'])
def results():
    # For displaying results
    if session.get("name") == None:
        # Only logged in users can see search results. So if you're not logged in, you're redirected home
        return redirect("/")
    return render_template('search_results.html')

@app.route('/logout', methods=['GET'])
def logout():
    session["name"] = None
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
