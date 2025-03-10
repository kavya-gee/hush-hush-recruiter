import asyncio
import aiohttp
import pandas as pd
import time
import nest_asyncio
import requests
import threading
from datetime import datetime
from queue import Queue
import sqlite3


nest_asyncio.apply()

BASE_URL = "https://api.stackexchange.com/2.3"
ENDPOINTS = {
    "User Profile": "/users/{ids}",
    "Reputation History": "/users/{ids}/reputation-history",
    "Questions Asked": "/users/{ids}/questions",
    "Answers Provided": "/users/{ids}/answers",
    "Tags and Expertise": "/users/{ids}/tags",
    "Badges": "/users/{ids}/badges",
    "Comments": "/users/{ids}/comments",
    "Top Answer Tags": "/users/{ids}/top-answer-tags",
    "Top Question Tags": "/users/{ids}/top-question-tags"
}
# API Key
STACKOVERFLOW_API_KEY = "rl_Xj57uz1Ei34HFUdds3PRKCji4"

# Base URLs for Stack Overflow API
USERS_URL = "https://api.stackexchange.com/2.3/users"


PAGESIZE = 100
TOTAL_USERS = 10000
TOTAL_PAGES = TOTAL_USERS // PAGESIZE

# Thread-safe queue instead of Lock()
user_data_queue = Queue()

# Fetch users from Stack Overflow
def fetch_users(page):
    params = {
        "order": "desc",
        "sort": "reputation",
        "site": "stackoverflow",
        "pagesize": PAGESIZE,
        "page": page,
        "key": STACKOVERFLOW_API_KEY
    }
    response = requests.get(USERS_URL, params=params)
    if response.status_code == 200:
        for item in response.json().get("items", []):
            user_data_queue.put(item)  # Add each user data to the queue

# Start fetching users using threads
threads = []
for page in range(1, TOTAL_PAGES + 1):
    thread = threading.Thread(target=fetch_users, args=(page,))
    threads.append(thread)
    thread.start()

# Wait for all threads to finish
for thread in threads:
    thread.join()

# Convert queue to list
user_data_list = list(user_data_queue.queue)


csv_filename = "stackoverflow_users.csv"
csv_columns = [
    "user_id", "display_name"]

# Create a DataFrame with the required columns
user_data_df = pd.DataFrame(user_data_list)


USER_IDS = user_data_df["user_id"].to_list()
SITE = "stackoverflow"
PARAMS = {
    "site": SITE,
    "pagesize": 100,
    "key": "rl_X6zzrZxXNCYEFymBuas9FNeR9"  # Add API key here (optional)
}
BATCH_SIZE = 30


async def fetch(session, url, params):
    """Asynchronous API call with error handling and retries."""
    for attempt in range(3):
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    await asyncio.sleep(10)
                else:
                    print(f"Error {response.status}: {url}")
        except Exception as e:
            print(f"Request failed: {e}")
        await asyncio.sleep(3)
    return {"items": []}


async def fetch_user_data(user_id, session):
    """Generator to yield user data asynchronously."""
    user_data = {}
    for key, endpoint in ENDPOINTS.items():
        url = f"{BASE_URL}{endpoint}".replace("{ids}", str(user_id))
        data = await fetch(session, url, PARAMS)
        if data:
            user_data[key] = data.get("items", [])
        else:
            print(f"Skipping user {user_id} due to failed request.")
            return
    yield user_id, user_data


async def process_batch(user_batch, session):
    """Generator to process batches of users asynchronously."""
    for user_id in user_batch:
        async for user_data in fetch_user_data(user_id, session):
            yield user_data


async def main():
    """Main function to fetch data in batches and yield results."""
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(USER_IDS), BATCH_SIZE):
            user_batch = USER_IDS[i:i + BATCH_SIZE]
            async for user_data in process_batch(user_batch, session):
                yield user_data
            print(f"Processed batch {i // BATCH_SIZE + 1}")
            time.sleep(1)


async def collect_data():
    """Collects data into DataFrames lazily using generators."""
    data_frames = {key: [] for key in ENDPOINTS.keys()}
    async for user_id, user_data in main():
        for key, records in user_data.items():
            for record in records:
                record["user_id"] = user_id
                data_frames[key].append(record)
    return {key: pd.DataFrame(records) for key, records in data_frames.items()}


# Run the async function
loop = asyncio.get_event_loop()
df_results = loop.run_until_complete(collect_data())

df_user_profile = pd.DataFrame(df_results['User Profile'])
df_questions_asked = pd.DataFrame(df_results['Questions Asked'])
df_Answers_Provided = pd.DataFrame(df_results['Answers Provided'])
df_Comments = pd.DataFrame(df_results['Comments'])

conn = sqlite3.connect('your_database.db')
cursor = conn.cursor()

df_user_profile.to_sql('user_profile', conn, if_exists='replace', index=False)
df_questions_asked.to_sql('questions_asked', conn, if_exists='replace', index=False)
df_Answers_Provided.to_sql('answers_provided', conn, if_exists='replace', index=False)
df_Comments.to_sql('comments', conn, if_exists='replace', index=False)

conn.commit()
conn.close()