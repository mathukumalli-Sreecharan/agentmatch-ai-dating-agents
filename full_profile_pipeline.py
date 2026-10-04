import os
import json

from dotenv import load_dotenv
from apify_client import ApifyClient
from google import genai
from google.genai import types


load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing.")


apify_client = ApifyClient(APIFY_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def get_linkedin_data(linkedin_url):
    print("Getting LinkedIn data...")

    run = apify_client.actor(
        "harvestapi/linkedin-profile-scraper"
    ).call(
        run_input={
            "urls": [linkedin_url]
        }
    )

    if run is None:
        return {}

    items = apify_client.dataset(
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


def get_instagram_data(username):
    print("Getting Instagram data...")

    run = apify_client.actor(
        "apify/instagram-profile-scraper"
    ).call(
        run_input={
            "usernames": [username]
        }
    )

    if run is None:
        return {}

    items = apify_client.dataset(
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


def analyze_person(person_profile):
    prompt = f"""
You are an AI profile analyst.

Analyze this person using ONLY the LinkedIn and Instagram data below.

Do NOT use outside knowledge.
Do NOT invent missing information.

Extract:

- interests
- hobbies
- needs
- values
- personality_traits
- lifestyle
- short_summary

Return ONLY valid JSON in exactly this format:

{{
    "interests": [],
    "hobbies": [],
    "needs": [],
    "values": [],
    "personality_traits": [],
    "lifestyle": [],
    "short_summary": ""
}}

PERSON DATA:

{json.dumps(person_profile, indent=2)}
"""

    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
    ]

    for model_name in models_to_try:
        try:
            print(f"Analyzing with {model_name}...")

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            if response.text:
                return json.loads(response.text)

        except Exception as error:
            print(f"{model_name} failed:")
            print(error)

    raise RuntimeError("All Gemini models failed.")


linkedin_url = "https://www.linkedin.com/in/williamhgates"
instagram_username = "thisisbillgates"


linkedin_data = get_linkedin_data(linkedin_url)

instagram_data = get_instagram_data(instagram_username)


person_profile = {
    "linkedin": linkedin_data,
    "instagram": instagram_data
}


analysis = analyze_person(person_profile)


final_profile = {
    "person": person_profile,
    "analysis": analysis
}


print("\n==============================")
print("FINAL AI PROFILE")
print("==============================\n")

print(
    json.dumps(
        final_profile,
        indent=2,
        ensure_ascii=False
    )
)