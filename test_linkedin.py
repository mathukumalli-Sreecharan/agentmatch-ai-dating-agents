import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing.")

client = ApifyClient(APIFY_TOKEN)

linkedin_url = "https://www.linkedin.com/in/williamhgates"

run_input = {
    "urls": [linkedin_url]
}

print("Starting LinkedIn scraper...")

run = client.actor("harvestapi/linkedin-profile-scraper").call(
    run_input=run_input
)

if run is None:
    raise RuntimeError("LinkedIn scraper did not return a run object.")

dataset = client.dataset(run.default_dataset_id)
items = dataset.list_items().items

if items:
    profile = items[0]

    print("\n--- LINKEDIN PROFILE ---")
    print("Name:", profile.get("firstName"), profile.get("lastName"))
    print("Headline:", profile.get("headline"))
    print("About:", profile.get("about"))

    print("\n--- EXPERIENCE ---")
    for exp in profile.get("experience", [])[:3]:
        print(
            "-",
            exp.get("position"),
            "at",
            exp.get("companyName")
        )

    print("\n--- EDUCATION ---")
    for edu in profile.get("education", [])[:3]:
        print("-", edu.get("schoolName"))

else:
    print("No LinkedIn data found.")