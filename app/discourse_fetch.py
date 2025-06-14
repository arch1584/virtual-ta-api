import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

# === CONFIG ===
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
LOGIN_URL = f"{BASE_URL}/login"
SEARCH_API = f"{BASE_URL}/search.json"
TOPIC_API = f"{BASE_URL}/t/{{topic_id}}.json"
DATE_FROM = "2025-01-01"
DATE_TO = "2025-04-14"
CATEGORY_TAG = "courses:tds-kb"

DISCOURSE_USERNAME = os.environ.get("DISCOURSE_USERNAME")
DISCOURSE_PASSWORD = os.environ.get("DISCOURSE_PASSWORD")

def get_cookies_and_csrf():
    # Start undetected Chrome
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    driver = uc.Chrome(options=options)
    driver.get(LOGIN_URL)
    time.sleep(2)  # Wait for page to load

    # Fill in login form (update selectors if needed)
    driver.find_element(By.ID, "login-account-name").send_keys(DISCOURSE_USERNAME)
    driver.find_element(By.ID, "login-account-password").send_keys(DISCOURSE_PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary')]").click()
    time.sleep(5)  # Wait for login

    # Get cookies
    cookies = driver.get_cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    # Get CSRF token from cookies or meta tag
    csrf_token = None
    for c in cookies:
        if c['name'] == "_forum_session" or "csrf" in c['name']:
            csrf_token = c['value']
    if not csrf_token:
        # Try to get from meta tag
        try:
            csrf_token = driver.execute_script(
                "return document.querySelector('meta[name=csrf-token]').getAttribute('content');"
            )
        except Exception:
            pass
    driver.quit()
    return cookie_str, csrf_token

def get_authenticated_session():
    cookie_str, csrf_token = get_cookies_and_csrf()
    session = requests.Session()
    session.headers.update({
        "x-csrf-token": csrf_token,
        "cookie": cookie_str,
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })
    return session

def get_search_results(query, session):
    full_query = f"{query}%20after%3A2025-01-01%20before%3A2025-04-14%20%23courses%3Atds-kb"
    params = {"q": full_query}
    print(f"Searching: {full_query}")
    r = session.get(SEARCH_API, params=params)
    r.raise_for_status()
    return r.json()

def get_full_topic(topic_id, session):
    url = TOPIC_API.format(topic_id=topic_id)
    r = session.get(url)
    r.raise_for_status()
    return r.json()

def extract_post_data(topic_json):
    posts = topic_json.get("post_stream", {}).get("posts", [])
    topic_title = topic_json.get("title")
    topic_id = topic_json.get("id")
    topic_slug = topic_json.get("slug")

    extracted = []
    for post in posts:
        content = BeautifulSoup(post["cooked"], "html.parser").get_text()
        extracted.append({
            "topic_id": topic_id,
            "topic_title": topic_title,
            "post_id": post["id"],
            "post_number": post["post_number"],
            "author": post["username"],
            "created_at": post["created_at"],
            "content": content,
            "url": f"{BASE_URL}/t/{topic_slug}/{topic_id}/{post['post_number']}"
        })
    return extracted

def fetch_relevant_posts(query, out_file="data/fetched_discourse/fetched_discourse.json"):
    session = get_authenticated_session()
    search_data = get_search_results(query, session)
    topic_ids = {topic["id"] for topic in search_data.get("topics", [])}
    print(f"Found {len(topic_ids)} matching topics for query '{query}'")

    all_posts = []
    for tid in topic_ids:
        topic_data = get_full_topic(tid, session)
        all_posts.extend(extract_post_data(topic_data))

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2)
    print(f"Saved {len(all_posts)} posts to {out_file}")

if __name__ == "__main__":
    user_query = input("Enter your query: ").strip()
    fetch_relevant_posts(user_query)
