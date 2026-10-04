import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing. Add it to your .env file.")

client = ApifyClient(APIFY_TOKEN)


def get_instagram_data(username):
    print("Getting Instagram data...")

    run_input = {
        "usernames": [username]
    }

    run = client.actor(
        "apify/instagram-profile-scraper"
    ).call(
        run_input=run_input
    )

    if run is None:
        return {}

    items = client.dataset(
        run.default_dataset_id
    ).list_items().items

    if not items:
        return {}

    profile = items[0]

    recent_posts = []

    for post in profile.get("latestPosts", [])[:5]:
        recent_posts.append({
            "caption": post.get("caption"),
            "url": post.get("url")
        })

    return {
        "username": profile.get("username"),
        "full_name": profile.get("fullName"),
        "biography": profile.get("biography"),
        "followers": profile.get("followersCount"),
        "private": profile.get("private"),
        "verified": profile.get("verified"),
        "recent_posts": recent_posts
    }


def get_linkedin_data(linkedin_url):
    print("Getting LinkedIn data...")

    run_input = {
        "urls": [linkedin_url]
    }

    run = client.actor(
        "harvestapi/linkedin-profile-scraper"
    ).call(
        run_input=run_input
    )

    if run is None:
        return {}

    items = client.dataset(
        run.default_dataset_id
    ).list_items().items

    if not items:
        return {}

    profile = items[0]

    experience = []

    for exp in profile.get("experience", [])[:5]:
        experience.append({
            "position": exp.get("position"),
            "company": exp.get("companyName")
        })

    education = []

    for edu in profile.get("education", [])[:5]:
        education.append({
            "school": edu.get("schoolName")
        })

    return {
        "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
        "headline": profile.get("headline"),
        "about": profile.get("about"),
        "experience": experience,
        "education": education
    }


# SAME PERSON
linkedin_url = "https://www.linkedin.com/in/williamhgates"
instagram_username = "thisisbillgates"


linkedin_data = get_linkedin_data(linkedin_url)
instagram_data = get_instagram_data(instagram_username)


person_profile = {
    "linkedin": linkedin_data,
    "instagram": instagram_data
}


print("\n==============================")
print("COMBINED PERSON PROFILE")
print("==============================")


print("\n--- LINKEDIN ---")
print("Name:", linkedin_data.get("name"))
print("Headline:", linkedin_data.get("headline"))
print("About:", linkedin_data.get("about"))

print("\nExperience:")
for exp in linkedin_data.get("experience", []):
    print(
        "-",
        exp.get("position"),
        "at",
        exp.get("company")
    )

print("\nEducation:")
for edu in linkedin_data.get("education", []):
    print("-", edu.get("school"))


print("\n--- INSTAGRAM ---")
print("Username:", instagram_data.get("username"))
print("Full Name:", instagram_data.get("full_name"))
print("Biography:", instagram_data.get("biography"))
print("Followers:", instagram_data.get("followers"))
print("Private:", instagram_data.get("private"))
print("Verified:", instagram_data.get("verified"))

print("\nRecent Posts:")

for index, post in enumerate(
    instagram_data.get("recent_posts", []),
    start=1
):
    print(f"\nPost {index}")
    print("Caption:", post.get("caption"))
    print("URL:", post.get("url"))