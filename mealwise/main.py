from fastapi import FastAPI, HTTPException
from quart import request
import requests
import quart
import quart_cors
import base64
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI()

app = FastAPI()

# Configure the CORS middleware
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8080",
    "https://chat.openai.com/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Replace these placeholders with your actual client ID and secret from the Kroger Developer Portal
YOUR_CLIENT_ID = "mealprice-98f71351b6455ef372f14d38514dd5ec6812214460393455349"
YOUR_CLIENT_SECRET = "9caCs00jJ5ztTPoTasuWO0NRkjHWTbVYaT6rZf4_"

# ZIP code to search for
ZIP_CODE = "60610"

# Kroger API URLs
TOKEN_URL = "https://api-ce.kroger.com/v1/connect/oauth2/token"
PRODUCT_URL = "https://api-ce.kroger.com/v1/products"
LOCATIONS_URL = 'https://api-ce.kroger.com/v1/locations'
PRODUCT_DETAILS_URL = "https://api-ce.kroger.com/v1/products/"

@app.get("/mealwise/{prompt}")
async def prompt_endpoint(prompt: str):
    return {"message": prompt}

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")
        
@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

def get_kroger_access_token(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact"
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def find_closest_kroger_store(zip_code: str):
    access_token = get_kroger_access_token(YOUR_CLIENT_ID, YOUR_CLIENT_SECRET)
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "filter.zipCode.near": zip_code,
        "filter.limit": 1,  # Limit results to the closest store
        "filter.radiusInMiles": 10  # Search radius in miles
    }

    response = requests.get(LOCATIONS_URL, headers=headers, params=params)
    response.raise_for_status()
    store_data = response.json()["data"]
    if store_data:
        closest_store = store_data[0]
        return {
            "store_id": closest_store["locationId"],
            "store_name": closest_store["name"],
            "store_address": closest_store["address"]["addressLine1"],
            "store_city": closest_store["address"]["city"],
            "store_state": closest_store["address"]["state"],
            "store_zip": closest_store["address"]["zipCode"]
        }
    else:
        return None

def get_product_id(product: str, store_id: str, headers: dict) -> str:
    params = {
        "filter.term": product,
        "filter.store": store_id
    }
    response = requests.get(PRODUCT_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()["data"]
    if not data:
        return None
    return data[0]["productId"]

def get_product_details(product_id: str, store_id: str, headers: dict) -> dict:
    params = {
        "filter.locationId": store_id
    }
    response = requests.get(PRODUCT_DETAILS_URL + product_id, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["data"]


@app.get("/get_product_info/{product}")
async def get_product_info(product: str):
    try:
        access_token = get_kroger_access_token(YOUR_CLIENT_ID, YOUR_CLIENT_SECRET)
        headers = {"Authorization": f"Bearer {access_token}"}
        results = []
        store_id = find_closest_kroger_store(zip_code=ZIP_CODE)["store_id"]

        # for product in products:
        product_id = get_product_id(product, store_id, headers)
        product_data = get_product_details(product_id, store_id, headers)
        description = product_data["description"]
        price = product_data["items"][0]["price"]["regular"]
        promo = product_data["items"][0]["price"]["promo"]
        results.append({
            "description": description,
            "price": str(price),
            "hasPromo": promo != 0,
            "promoPrice": promo,
            "location": product_data["aisleLocations"][0]["description"] if product_data["aisleLocations"] else "Not available"
        })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

