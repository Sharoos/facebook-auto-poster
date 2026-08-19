import json
import os
import random
import requests

# ==========================================
# CONFIGURATION
# ==========================================
MY_WEBSITE = "https://www.bestpricezone.in"
TRACKING_FILE = "posted_products.json"

# Facebook API Credentials
FB_PAGE_ID = "104412797589430"
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
FB_GRAPH_VERSION = "v20.0"

# Posting Settings for GitHub Actions (1 post per hourly run)
POSTS_PER_RUN = 1

COLLECTIONS = [
    {
        "url": "https://deodap.in/collections/all/products.json",
        "name": "Main Catalog",
    },
    {
        "url": "https://deodap.in/collections/just-arrived/products.json",
        "name": "New Arrivals",
    },
    {
        "url": "https://deodap.in/collections/customer-favorites/products.json",
        "name": "Bestsellers",
    },
    {
        "url": "https://deodap.in/collections/kitchen-dining-items/products.json",
        "name": "Kitchenware",
    },
    {
        "url": "https://deodap.in/collections/home_decor/products.json",
        "name": "Home & Living",
    },
    {
        "url": "https://deodap.in/collections/home-improvement/products.json",
        "name": "Hardware & Tools",
    },
    {
        "url": "https://deodap.in/collections/beauty-health-grocery/products.json",
        "name": "Beauty & Personal Care",
    },
    {
        "url": "https://deodap.in/collections/jewellery-accessories/products.json",
        "name": "Jewellery & Accessories",
    },
    {
        "url": "https://deodap.in/collections/stationery/products.json",
        "name": "Stationery & Office",
    },
    {
        "url": "https://deodap.in/collections/chargers-power/products.json",
        "name": "Mobile & Gadgets",
    },
    {
        "url": "https://deodap.in/collections/mega-savings/products.json",
        "name": "Under ₹99 Store",
    },
]


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def load_posted_history():
    try:
        with open(TRACKING_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_posted_history(posted_ids):
    with open(TRACKING_FILE, "w") as f:
        json.dump(list(posted_ids), f, indent=4)


def fetch_products_from_collection(collection_url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    url_with_limit = f"{collection_url}?limit=250"
    try:
        response = requests.get(url_with_limit, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("products", [])
    except Exception as e:
        print(f"Error fetching collection {collection_url}: {e}")
    return []


def create_single_product_caption(product):
    """Creates a varied, high-converting caption for 1 product."""
    title = product["title"]
    variant = product["variants"][0]
    price = int(float(variant["price"]))

    compare_at = (
        int(float(variant["compare_at_price"]))
        if variant.get("compare_at_price")
        else int(price * 2.2)
    )

    discount = (
        int(((compare_at - price) / compare_at) * 100)
        if compare_at > price
        else 0
    )

    templates = [
        (
            f"🔥 MEGA PRICE DROP | {discount}% OFF! 🔥\n\n"
            f"🛍️ Product: {title}\n"
            f"💰 Offer Price: ₹{price} (WAS ₹{compare_at})\n\n"
            f"👉 Buy Now on Best Price Zone: {MY_WEBSITE}\n\n"
            f"⚡ Hurry, limited stock available! Grab yours before price changes."
        ),
        (
            f"⚡ SPECIAL DEAL OF THE DAY ⚡\n\n"
            f"✨ Item: {title}\n"
            f"🏷️ Discount: Save {discount}% TODAY!\n"
            f"💸 Deal Price: ₹{price} (MSRP: ₹{compare_at})\n\n"
            f"🛒 Order online here: {MY_WEBSITE}\n\n"
            f"📦 Fast shipping available across India!"
        ),
        (
            f"📢 HUGE SAVINGS ALERT! 📢\n\n"
            f"Get {title} for just ₹{price}! (Original Price: ₹{compare_at})\n\n"
            f"💥 You save {discount}% on this order.\n\n"
            f"🔗 Shop Now: {MY_WEBSITE}\n\n"
            f"⏰ Offer valid while stocks last!"
        ),
        (
            f"🛒 TRENDING NOW ON BEST PRICE ZONE 🛒\n\n"
            f"🔹 {title}\n"
            f"🔹 Special Price: ₹{price} ({discount}% OFF)\n\n"
            f"Click to order yours today: {MY_WEBSITE} 👇"
        ),
    ]

    return random.choice(templates)


def post_photo_to_facebook(image_url, caption):
    """Posts image + caption directly to Facebook Page."""
    if not FB_ACCESS_TOKEN:
        print("❌ Error: FB_ACCESS_TOKEN environment variable is missing.")
        return False

    fb_url = (
        f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{FB_PAGE_ID}/photos"
    )

    payload = {
        "url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN,
    }

    try:
        res = requests.post(fb_url, data=payload)
        res_data = res.json()

        if res.status_code == 200 and "id" in res_data:
            print(
                f"✅ Posted to Facebook successfully! Post ID: {res_data['id']}"
            )
            return True
        else:
            print(f"❌ Facebook API Error: {res_data}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Facebook API: {e}")
        return False


# ==========================================
# MAIN ROUTINE (POST 1 PRODUCT PER RUN)
# ==========================================
def run_single_post():
    posted_ids = load_posted_history()

    candidates = []
    attempts = 0

    while len(candidates) < POSTS_PER_RUN and attempts < 15:
        attempts += 1
        col = random.choice(COLLECTIONS)
        products = fetch_products_from_collection(col["url"])

        random.shuffle(products)

        for p in products:
            p_id = str(p["id"])
            if (
                p_id not in posted_ids
                and p.get("images")
                and len(p["images"]) > 0
            ):
                candidates.append(p)
                break

    if not candidates:
        print(
            "⚠️ Not enough new products found. Resetting history log to reuse products..."
        )
        posted_ids.clear()
        save_posted_history(posted_ids)
        return

    product = candidates[0]
    p_id = str(product["id"])
    image_url = product["images"][0]["src"]
    caption = create_single_product_caption(product)

    print(f"--- [Scheduled Post Execution] ---")
    print(f"Product: {product['title']}")
    print(f"Image: {image_url}")

    success = post_photo_to_facebook(image_url, caption)

    if success:
        posted_ids.add(p_id)
        save_posted_history(posted_ids)
        print("🎉 Post published and history log updated.")


if __name__ == "__main__":
    run_single_post()