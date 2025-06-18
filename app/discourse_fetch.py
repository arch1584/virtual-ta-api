import os
import json
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# === CONFIG ===
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
LOGIN_URL = f"{BASE_URL}/login"
SEARCH_API = f"{BASE_URL}/search.json"
TOPIC_API = f"{BASE_URL}/t/{{topic_id}}.json"


DISCOURSE_USERNAME = os.environ.get("DISCOURSE_USERNAME")
DISCOURSE_PASSWORD = os.environ.get("DISCOURSE_PASSWORD")

def get_cookies_and_csrf_and_session():
    options = uc.ChromeOptions()
    options.binary_location = "/snap/bin/chromium"
    driver = uc.Chrome(
        options=options,
        driver_executable_path="/usr/bin/chromedriver",
        version_main=137,
        headless=True,
    )

    driver.get(LOGIN_URL)
    time.sleep(2)

    # Fill login
    driver.find_element(By.ID, "login-account-name").send_keys(DISCOURSE_USERNAME)
    driver.find_element(By.ID, "login-account-password").send_keys(DISCOURSE_PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary')]").click()

    # Wait for login success — avatar presence
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img.avatar"))
    )

    cookies = driver.get_cookies()
    driver.quit()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": BASE_URL,
    })

    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))

    return session


def get_search_results(query, session, page=1):

    #build the full query as a raw string
    full_query = f"{query} after:2025-01-01 before:2025-04-14 #courses:tds-kb"

    # Let requests handle encoding safely
    params = {"q": full_query, "page": page}

    try:
        r = session.get(SEARCH_API, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"HTTP error on search page {page}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"JSON decode error on search page {page}")
        return None


def get_full_topic(topic_id, session):
    url = TOPIC_API.format(topic_id=topic_id)
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"HTTP error fetching topic {topic_id}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"JSON decode error for topic {topic_id}")
        return None

def extract_post_data(topic_json):
    if not topic_json:
        print("Warning: Received empty topic JSON!")
        return []

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
            "post_id": post.get("id"),
            "post_number": post.get("post_number"),
            "author": post.get("username"),
            "created_at": post.get("created_at"),
            "content": content,
            "url": f"{BASE_URL}/t/{topic_slug}/{topic_id}/{post.get('post_number')}"
        })
    return extracted



def fetch_relevant_posts(query, out_file):
    session = get_cookies_and_csrf_and_session()
    all_topic_ids = set()
    page = 1
    while True:
        search_data = get_search_results(query, session, page=page)
        if not search_data:
            print("Search data is None. Ending search.")
            break
        topics = search_data.get("topics", [])
        if not topics:
            print("No topics found. Ending search.")
            break

        new_ids = {topic["id"] for topic in search_data["topics"]}
        if not new_ids - all_topic_ids:
            break  # No new topics, end pagination
        all_topic_ids.update(new_ids)
        print(f"Page {page}: found {len(new_ids)} topics, total unique topics so far: {len(all_topic_ids)}")
        if len(search_data["topics"]) < 50:
            break  # Last page
        page += 1

    
    print(f"Total unique topics found: {len(all_topic_ids)}")

    all_posts = []
    for tid in all_topic_ids:
        try:
            topic_data = get_full_topic(tid, session)
            if topic_data:
                all_posts.extend(extract_post_data(topic_data))
        except Exception as e:
            print(f"Failed to fetch/extract topic {tid}: {e}")

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2)
    print(f"Saved {len(all_posts)} posts to {out_file}")
    return out_file
    
