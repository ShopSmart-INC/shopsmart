from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def fetch_items(keyword):
    sites = [
        'https://www.walmart.ca/search/?query=', 
        'https://www.ebay.ca/sch/i.html?_nkw='
    ]
    items = []

    for site in sites:
        try:
            url = site + keyword
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all product containers
            product_containers = soup.find_all('div', class_='s-result-item')

            for container in product_containers:
                try:
                    # Extract item name and price
                    name = container.find('span', class_='a-size-medium').text.strip()
                    price = container.find('span', class_='a-offscreen').text.strip()
                    
                    # Append item details to the list
                    items.append({'name': name, 'price': price})
                except AttributeError:
                    # Skip if any attribute error occurs
                    continue
        except Exception as e:
            print(f"An error occurred while fetching data from {url}: {e}")
            continue

    # Sort items by price (ascending)
    sorted_items = sorted(items, key=lambda x: float(x['price'].replace('$', '').replace(',', '')))

    return sorted_items

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        keyword = request.form['keyword']
        items = fetch_items(keyword)
        return render_template('search_results.html', items=items)
    return render_template('search_form.html')

if __name__ == '__main__':
    app.run(debug=True)