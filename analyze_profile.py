import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. Add it to your .env file."
    )


# Create Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_person(person_profile):

    prompt = f"""
You are an AI profile analyst.

Analyze the person using ONLY the LinkedIn and Instagram
information provided below.

Do NOT use outside knowledge.
Do NOT invent information.

Return JSON in exactly this structure:

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
            print(f"Trying model: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            if not response.text:
                print(f"{model_name} returned empty response.")
                continue

            return json.loads(response.text)

        except Exception as error:
            print(f"\n{model_name} failed:")
            print(error)
            print()

    raise RuntimeError("All Gemini models failed.")


# ---------------------------------
# TEST PROFILE
# ---------------------------------

person_profile = {
    "linkedin": {
        "name": "Bill Gates",
        "headline": (
            "Chair, Gates Foundation and "
            "Founder, Breakthrough Energy"
        ),
        "about": (
            "Chair of the Gates Foundation. "
            "Founder of Breakthrough Energy. "
            "Co-founder of Microsoft. "
            "Voracious reader. "
            "Avid traveler. "
            "Active blogger."
        ),

        "experience": [
            {
                "position": "Co-chair",
                "company": "Gates Foundation"
            },
            {
                "position": "Founder",
                "company": "Breakthrough Energy"
            },
            {
                "position": "Co-founder",
                "company": "Microsoft"
            }
        ],

        "education": [
            {
                "school": "Harvard University"
            },
            {
                "school": "Lakeside School"
            }
        ]
    },

    "instagram": {
        "username": "thisisbillgates",
        "full_name": "Bill Gates",

        "biography": (
            "Sharing things I'm learning through "
            "my foundation work and other interests."
        ),

        "recent_posts": [
            {
                "caption": (
                    "The week I spend in New York for "
                    "#Goalkeepers2030 and the UN General "
                    "Assembly is always a highlight of my year."
                )
            },
            {
                "caption": (
                    "People and relationships must remain "
                    "at the center of how we use AI."
                )
            },
            {
                "caption": (
                    "We have an opportunity—and an obligation—"
                    "to ensure that AI tools are designed to "
                    "improve lives and reach farmers, teachers, "
                    "and health workers."
                )
            },
            {
                "caption": (
                    "There are around 7,000 languages spoken "
                    "worldwide, yet most AI tools are still "
                    "built primarily in English."
                )
            },
            {
                "caption": (
                    "I'm excited to keep the conversation around "
                    "AI moving forward and build on the progress "
                    "we're making."
                )
            }
        ]
    }
}


print("Analyzing profile with Gemini...\n")

try:

    analysis = analyze_person(person_profile)

    print("\n==============================")
    print("AI PROFILE ANALYSIS")
    print("==============================\n")

    print(
        json.dumps(
            analysis,
            indent=2,
            ensure_ascii=False
        )
    )

except Exception as error:

    print("\nFinal error:")
    print(error)