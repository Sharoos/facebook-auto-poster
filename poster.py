import json
import os
import random
import re
import time
import requests

# ==========================================
# CONFIGURATION
# ==========================================
MY_WEBSITE = "https://www.bestpricezone.in"
TRACKING_FILE = "posted_products.json"

# Meta API Credentials
FB_PAGE_ID = "104412797589430"
IG_USER_ID = "17841458404272372"  # Your verified Instagram Business ID
# Ensure your new permanent token is set in your environment variables/GitHub Secrets
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
FB_GRAPH_VERSION = "v20.0"

# Posting Settings for GitHub Actions (1 post per hourly run)
POSTS_PER_RUN = 1
MAX_PHOTOS_PER_POST = 6

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


def generate_dynamic_hashtags(product):
    """Dynamically extracts keywords from the product title and pairs them with rotated deal tags."""
    title = product.get("title", "")

    stop_words = {
        "for",
        "and",
        "the",
        "with",
        "pcs",
        "pack",
        "inch",
        "mm",
        "cm",
        "to",
        "of",
        "in",
        "on",
        "by",
        "an",
        "a",
    }
    words = re.findall(r"\b[A-Za-z0-9]+\b", title)

    keywords = []
    for word in words:
        if word.lower() not in stop_words and len(word) > 2:
            keywords.append(f"#{word.capitalize()}")

    # Keep unique keywords from the title (up to 4)
    keywords = list(dict.fromkeys(keywords))[:4]

    # Dynamic pool of high-performing e-commerce and deal hashtags
    niche_tags = [
        "#BestPriceZone",
        "#DealOfTheDay",
        "#BudgetDeals",
        "#TrendingFinds",
        "#ShopSmart",
        "#OnlineShoppingIndia",
        "#MegaDiscounts",
        "#MustHaveGadgets",
    ]

    # Combine title-specific tags with a random sample of rotational deal tags
    all_tags = keywords + random.sample(niche_tags, min(3, len(niche_tags)))

    return "\n\n" + " ".join(all_tags)


def create_single_product_caption(product):
    """Creates varied discount-hook captions with price and discount first, item name next, then the rest."""
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

    savings = max(compare_at - price, 0)
    hashtags = generate_dynamic_hashtags(product)

    templates = [
        (
            f"Rs. {price}/- ONLY ({discount}% OFF!)\n"
            f"{title}\n\n"
            f"Usually ₹{compare_at} — save ₹{savings} today.\n"
            f"👉 Grab it before the offer resets: {MY_WEBSITE}\n"
            f"⚡ Limited stock available"
            f"{hashtags}"
        ),
        (
            f"Just Rs. {price}/- after {discount}% discount 🔥\n"
            f"{title}\n\n"
            f"MRP ₹{compare_at} • You save ₹{savings}\n"
            f"🛒 Order here (link in bio): {MY_WEBSITE}\n"
            f"📦 Pan-India delivery"
            f"{hashtags}"
        ),
        (
            f"Rs. {price}/- steal • {discount}% off MRP!\n"
            f"{title}\n\n"
            f"Down from ₹{compare_at} while stock lasts.\n"
            f"🔗 Tap link in bio or visit: {MY_WEBSITE}\n"
            f"⏰ Don't sleep on this price"
            f"{hashtags}"
        ),
        (
            f"FLAT {discount}% OFF → Rs. {price}/- only\n"
            f"{title}\n\n"
            f"Compare at ₹{compare_at} — quick deal on Best Price Zone.\n"
            f"👉 Shop now: {MY_WEBSITE}\n"
            f"🔥 Limited pieces"
            f"{hashtags}"
        ),
    ]

    return random.choice(templates)


def post_photo_to_facebook(image_url, caption):
    """Posts a single image + caption directly to Facebook Page."""
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


def post_photos_to_facebook(image_urls, caption):
    """Posts up to 6 images + caption to Facebook Page."""
    if not FB_ACCESS_TOKEN:
        print("❌ Error: FB_ACCESS_TOKEN environment variable is missing.")
        return False

    urls = image_urls[:MAX_PHOTOS_PER_POST]
    if not urls:
        return False

    if len(urls) == 1:
        return post_photo_to_facebook(urls[0], caption)

    media_ids = []
    upload_url = (
        f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{FB_PAGE_ID}/photos"
    )

    try:
        for img_url in urls:
            res = requests.post(
                upload_url,
                data={
                    "url": img_url,
                    "published": "false",
                    "access_token": FB_ACCESS_TOKEN,
                },
            )
            data = res.json()

            if res.status_code == 200 and "id" in data:
                media_ids.append(data["id"])
            else:
                print(f"❌ Facebook Photo Upload Error ({img_url}): {data}")

        if not media_ids:
            return False

        feed_url = (
            f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{FB_PAGE_ID}/feed"
        )
        attached_media = json.dumps([{"media_fbid": mid} for mid in media_ids])

        pub_res = requests.post(
            feed_url,
            data={
                "message": caption,
                "attached_media": attached_media,
                "access_token": FB_ACCESS_TOKEN,
            },
        )
        pub_data = pub_res.json()

        if pub_res.status_code == 200 and "id" in pub_data:
            print(
                f"✅ Posted {len(media_ids)} photos to Facebook successfully! Post ID: {pub_data['id']}"
            )
            return True
        else:
            print(f"❌ Facebook Multi-Photo Publish Error: {pub_data}")
            return False
    except Exception as e:
        print(f"❌ Failed to post multiple photos to Facebook: {e}")
        return False


def post_photo_to_instagram(image_url, caption):
    """Posts a single image + caption to Instagram Business Account via 2-step process with a delay."""
    if not FB_ACCESS_TOKEN:
        print("❌ Error: FB_ACCESS_TOKEN environment variable is missing.")
        return False

    # STEP 1: Create a Container
    container_url = (
        f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{IG_USER_ID}/media"
    )
    container_payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FB_ACCESS_TOKEN,
    }

    try:
        res = requests.post(container_url, data=container_payload)
        res_data = res.json()

        if res.status_code != 200 or "id" not in res_data:
            print(f"❌ Instagram Container Creation Error: {res_data}")
            return False

        creation_id = res_data["id"]

        # ⏳ Wait for Instagram to process the media container
        print("⏳ Waiting for Instagram to process the media container...")
        time.sleep(6)

        # STEP 2: Publish the Container
        publish_url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{IG_USER_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": FB_ACCESS_TOKEN,
        }

        pub_res = requests.post(publish_url, data=publish_payload)
        pub_data = pub_res.json()

        if pub_res.status_code == 200 and "id" in pub_data:
            print(
                f"✅ Posted to Instagram successfully! Post ID: {pub_data['id']}"
            )
            return True
        else:
            print(f"❌ Instagram Publish Error: {pub_data}")
            return False

    except Exception as e:
        print(f"❌ Failed to connect to Instagram API: {e}")
        return False


def post_photos_to_instagram(image_urls, caption):
    """Posts 1 image or up to 6 photos as an Instagram carousel."""
    if not FB_ACCESS_TOKEN:
        print("❌ Error: FB_ACCESS_TOKEN environment variable is missing.")
        return False

    urls = image_urls[:MAX_PHOTOS_PER_POST]
    if not urls:
        return False

    if len(urls) == 1:
        return post_photo_to_instagram(urls[0], caption)

    container_url = (
        f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{IG_USER_ID}/media"
    )
    child_ids = []

    try:
        for img_url in urls:
            created = False
            for attempt in range(2):
                res = requests.post(
                    container_url,
                    data={
                        "image_url": img_url,
                        "is_carousel_item": "true",
                        "access_token": FB_ACCESS_TOKEN,
                    },
                )
                data = res.json()

                if res.status_code == 200 and "id" in data:
                    child_ids.append(data["id"])
                    created = True
                    break

                if attempt == 0:
                    time.sleep(2)
                else:
                    print(
                        f"❌ Instagram Carousel Item Error ({img_url}): {data}"
                    )

        if len(child_ids) < 2:
            print(
                "⚠️ Fewer than 2 carousel items succeeded; falling back to single photo."
            )
            return post_photo_to_instagram(urls[0], caption)

        print(
            f"⏳ Waiting for {len(child_ids)} Instagram carousel items to process..."
        )
        time.sleep(6)

        carousel_res = requests.post(
            container_url,
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": FB_ACCESS_TOKEN,
            },
        )
        carousel_data = carousel_res.json()

        if carousel_res.status_code != 200 or "id" not in carousel_data:
            print(f"❌ Instagram Carousel Container Error: {carousel_data}")
            return False

        carousel_id = carousel_data["id"]

        print("⏳ Waiting for Instagram carousel container to finalize...")
        time.sleep(6)

        publish_url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{IG_USER_ID}/media_publish"
        pub_res = requests.post(
            publish_url,
            data={
                "creation_id": carousel_id,
                "access_token": FB_ACCESS_TOKEN,
            },
        )
        pub_data = pub_res.json()

        if pub_res.status_code == 200 and "id" in pub_data:
            print(
                f"✅ Posted {len(child_ids)}-photo carousel to Instagram successfully! Post ID: {pub_data['id']}"
            )
            return True
        else:
            print(f"❌ Instagram Carousel Publish Error: {pub_data}")
            return False

    except Exception as e:
        print(f"❌ Failed to post carousel to Instagram: {e}")
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
    image_urls = [
        img["src"]
        for img in product["images"][:MAX_PHOTOS_PER_POST]
        if img.get("src")
    ]
    caption = create_single_product_caption(product)

    print(f"--- [Scheduled Post Execution] ---")
    print(f"Product: {product['title']}")
    print(f"Images ({len(image_urls)}): {image_urls}")

    # Attempt publishing to both platforms
    fb_success = post_photos_to_facebook(image_urls, caption)
    ig_success = post_photos_to_instagram(image_urls, caption)

    # Log history if at least one platform succeeds
    if fb_success or ig_success:
        posted_ids.add(p_id)
        save_posted_history(posted_ids)
        print("🎉 Log updated successfully.")


if __name__ == "__main__":
    run_single_post()
