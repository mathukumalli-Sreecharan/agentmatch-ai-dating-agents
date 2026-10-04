import os
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load .env file
load_dotenv()

# Get Apify token
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing. Add it to your .env file.")

# Create Apify client
client = ApifyClient(APIFY_TOKEN)

# Instagram username
instagram_username = "humansofny"

# Input for Instagram Profile Scraper
run_input = {
    "usernames": [instagram_username]
}

print("Starting Instagram scraper...")

# Run Actor
run = client.actor("apify/instagram-profile-scraper").call(
    run_input=run_input
)

if run is None:
    raise RuntimeError("Instagram scraper did not return a run object.")

print("Scraping completed.")

# Get Actor dataset
dataset = client.dataset(run.default_dataset_id)

# Get scraped results
items = dataset.list_items().items

# Print only useful fields
if items:
    profile = items[0]

    print("\n--- INSTAGRAM PROFILE ---")

    print("Username:", profile.get("username"))
    print("Full Name:", profile.get("fullName"))
    print("Biography:", profile.get("biography"))
    print("Followers:", profile.get("followersCount"))
    print("Following:", profile.get("followsCount"))
    print("Private:", profile.get("private"))
    print("Verified:", profile.get("verified"))

    print("\n--- RECENT POSTS ---")

    latest_posts = profile.get("latestPosts", [])

    for index, post in enumerate(latest_posts[:5], start=1):
        print(f"\nPost {index}")
        print("Caption:", post.get("caption"))
        print("Likes:", post.get("likesCount"))
        print("URL:", post.get("url"))

else:
    print("No Instagram profile data found.")