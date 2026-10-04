import os
import json
import re

import streamlit as st
from dotenv import load_dotenv
from apify_client import ApifyClient
from google import genai
from google.genai import types


# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(
    page_title="AgentMatch",
    page_icon="💘",
    layout="wide"
)

load_dotenv()


# =========================================================
# LOCAL + CLOUD SECRETS
# =========================================================

def get_secret(name):
    # First try local .env
    value = os.getenv(name)

    if value:
        return value

    # Then try Streamlit Cloud secrets
    try:
        return st.secrets[name]
    except Exception:
        return None


APIFY_TOKEN = get_secret("APIFY_TOKEN")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")


if not APIFY_TOKEN:
    st.error("APIFY_TOKEN is missing.")
    st.stop()

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is missing.")
    st.stop()


apify_client = ApifyClient(APIFY_TOKEN)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# FILES
# =========================================================

DATA_FILE = "data/profiles.json"
DATES_FILE = "data/dates.json"


# =========================================================
# SAVE / LOAD PROFILES
# =========================================================

def save_profiles():

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            st.session_state["profiles"],
            file,
            indent=2,
            ensure_ascii=False
        )


def load_profiles():

    if not os.path.exists(DATA_FILE):
        return []

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:
        return []


# =========================================================
# SAVE / LOAD DATES
# =========================================================

def save_dates():

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        DATES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            st.session_state["dates"],
            file,
            indent=2,
            ensure_ascii=False
        )


def load_dates():

    if not os.path.exists(DATES_FILE):
        return []

    try:

        with open(
            DATES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:
        return []


# =========================================================
# SESSION STATE
# =========================================================

if "profiles" not in st.session_state:
    st.session_state["profiles"] = load_profiles()

if "dates" not in st.session_state:
    st.session_state["dates"] = load_dates()

if "current_date" not in st.session_state:
    st.session_state["current_date"] = None


# =========================================================
# INSTAGRAM USERNAME
# =========================================================

def extract_instagram_username(value):

    value = value.strip()

    if "instagram.com" in value:

        match = re.search(
            r"instagram\.com/([^/?#]+)",
            value
        )

        if match:
            return match.group(1)

    return (
        value
        .replace("@", "")
        .strip()
    )


# =========================================================
# LINKEDIN
# =========================================================

def get_linkedin_data(linkedin_url):

    run = apify_client.actor(
        "harvestapi/linkedin-profile-scraper"
    ).call(
        run_input={
            "urls": [linkedin_url]
        }
    )

    if run is None:
        return {}

    items = (
        apify_client
        .dataset(run.default_dataset_id)
        .list_items()
        .items
    )

    if not items:
        return {}

    profile = items[0]

    experience = []

    for exp in profile.get(
        "experience",
        []
    )[:5]:

        experience.append({
            "position":
                exp.get("position"),

            "company":
                exp.get("companyName")
        })


    education = []

    for edu in profile.get(
        "education",
        []
    )[:5]:

        education.append({
            "school":
                edu.get("schoolName")
        })


    name = (
        f"{profile.get('firstName', '')} "
        f"{profile.get('lastName', '')}"
    ).strip()


    return {
        "name":
            name,

        "headline":
            profile.get("headline"),

        "about":
            profile.get("about"),

        "experience":
            experience,

        "education":
            education,

        "source_url":
            linkedin_url
    }


# =========================================================
# INSTAGRAM
# =========================================================

def get_instagram_data(username):

    run = apify_client.actor(
        "apify/instagram-profile-scraper"
    ).call(
        run_input={
            "usernames": [username]
        }
    )

    if run is None:
        return {}

    items = (
        apify_client
        .dataset(run.default_dataset_id)
        .list_items()
        .items
    )

    if not items:
        return {}

    profile = items[0]

    recent_posts = []

    for post in profile.get(
        "latestPosts",
        []
    )[:5]:

        recent_posts.append({
            "caption":
                post.get("caption"),

            "url":
                post.get("url")
        })


    return {
        "username":
            profile.get("username"),

        "full_name":
            profile.get("fullName"),

        "biography":
            profile.get("biography"),

        "followers":
            profile.get("followersCount"),

        "private":
            profile.get("private"),

        "verified":
            profile.get("verified"),

        "profile_picture":
            (
                profile.get("profilePicUrlHD")
                or
                profile.get("profilePicUrl")
            ),

        "recent_posts":
            recent_posts,

        "source_url":
            f"https://www.instagram.com/{username}/"
    }


# =========================================================
# PROFILE ANALYSIS
# =========================================================

def analyze_person(person_profile):

    prompt = f"""
You are an AI profile analyst.

Analyze this person using ONLY the LinkedIn and Instagram
information supplied below.

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

Return ONLY valid JSON:

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

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type=
                    "application/json"
                )
            )

            if response.text:
                return json.loads(
                    response.text
                )

        except Exception:
            continue

    raise RuntimeError(
        "Gemini profile analysis failed."
    )


# =========================================================
# AGENT DATE
# =========================================================

def generate_date(profile_a, profile_b):

    name_a = (
        profile_a[
            "person"
        ][
            "linkedin"
        ].get(
            "name",
            "Person A"
        )
    )

    name_b = (
        profile_b[
            "person"
        ][
            "linkedin"
        ].get(
            "name",
            "Person B"
        )
    )

    analysis_a = profile_a["analysis"]
    analysis_b = profile_b["analysis"]


    prompt = f"""
You are simulating a short conversation between
two AI dating agents.

Each agent represents one real person.

Use ONLY the supplied profile analyses.

Do NOT use outside knowledge.
Do NOT invent facts.

PERSON A:
{name_a}

PROFILE A:
{json.dumps(analysis_a, indent=2)}

PERSON B:
{name_b}

PROFILE B:
{json.dumps(analysis_b, indent=2)}

Create a natural conversation where the agents compare:

- interests
- hobbies
- values
- lifestyle
- needs
- similarities
- differences

Return ONLY valid JSON:

{{
    "conversation": [
        {{
            "speaker": "{name_a} Agent",
            "message": ""
        }},
        {{
            "speaker": "{name_b} Agent",
            "message": ""
        }},
        {{
            "speaker": "{name_a} Agent",
            "message": ""
        }},
        {{
            "speaker": "{name_b} Agent",
            "message": ""
        }}
    ],

    "compatibility_score": 0,

    "compatibility_breakdown": {{
        "interests": 0,
        "values": 0,
        "lifestyle": 0,
        "personality": 0,
        "needs": 0
    }},

    "strengths": [],
    "differences": [],
    "verdict": ""
}}

All scores must be integers between 0 and 100.

Keep everything grounded only in the supplied profile data.
"""


    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
    ]


    for model_name in models_to_try:

        try:

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type=
                    "application/json"
                )
            )

            if response.text:

                return json.loads(
                    response.text
                )

        except Exception:
            continue


    raise RuntimeError(
        "Dating simulation failed."
    )


# =========================================================
# RANKING SYSTEM
# =========================================================

STOP_WORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "through",
    "their",
    "that",
    "this",
    "using",
    "focused",
    "focus",
    "active",
    "global",
    "highly",
    "people",
    "work",
    "working",
    "based",
    "toward",
    "towards"
}


def normalize_words(items):

    words = set()

    for item in items:

        if not item:
            continue

        text = str(item).lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        for word in text.split():

            if (
                len(word) > 2
                and
                word not in STOP_WORDS
            ):
                words.add(word)

    return words


def category_similarity(
    profile_a,
    profile_b,
    category
):

    list_a = (
        profile_a[
            "analysis"
        ].get(
            category,
            []
        )
    )

    list_b = (
        profile_b[
            "analysis"
        ].get(
            category,
            []
        )
    )

    words_a = normalize_words(
        list_a
    )

    words_b = normalize_words(
        list_b
    )

    if not words_a or not words_b:
        return 50


    intersection = (
        words_a.intersection(
            words_b
        )
    )

    union = (
        words_a.union(
            words_b
        )
    )


    overlap = (
        len(intersection)
        /
        len(union)
    )


    score = (
        40
        +
        overlap * 60
    )


    return round(
        min(
            score,
            100
        )
    )


def calculate_match_score(
    profile_a,
    profile_b
):

    interests = category_similarity(
        profile_a,
        profile_b,
        "interests"
    )

    hobbies = category_similarity(
        profile_a,
        profile_b,
        "hobbies"
    )

    values = category_similarity(
        profile_a,
        profile_b,
        "values"
    )

    lifestyle = category_similarity(
        profile_a,
        profile_b,
        "lifestyle"
    )

    personality = category_similarity(
        profile_a,
        profile_b,
        "personality_traits"
    )

    needs = category_similarity(
        profile_a,
        profile_b,
        "needs"
    )


    final_score = (
        interests * 0.20
        +
        hobbies * 0.10
        +
        values * 0.25
        +
        lifestyle * 0.15
        +
        personality * 0.15
        +
        needs * 0.15
    )


    return {
        "score":
            round(final_score),

        "interests":
            interests,

        "hobbies":
            hobbies,

        "values":
            values,

        "lifestyle":
            lifestyle,

        "personality":
            personality,

        "needs":
            needs
    }


def build_rankings(profiles):

    rankings = {}

    for i, profile_a in enumerate(
        profiles
    ):

        name_a = (
            profile_a[
                "person"
            ][
                "linkedin"
            ].get(
                "name",
                f"Person {i + 1}"
            )
        )

        matches = []

        for j, profile_b in enumerate(
            profiles
        ):

            if i == j:
                continue


            name_b = (
                profile_b[
                    "person"
                ][
                    "linkedin"
                ].get(
                    "name",
                    f"Person {j + 1}"
                )
            )


            match = (
                calculate_match_score(
                    profile_a,
                    profile_b
                )
            )


            matches.append({
                "name":
                    name_b,

                "score":
                    match["score"],

                "details":
                    match
            })


        matches.sort(
            key=lambda x:
                x["score"],
            reverse=True
        )


        rankings[
            name_a
        ] = matches


    return rankings


# =========================================================
# HEADER
# =========================================================

st.title(
    "💘 AgentMatch"
)

st.caption(
    "AI dating agents built from public LinkedIn "
    "and Instagram profiles."
)

st.divider()


# =========================================================
# CREATE PERSON
# =========================================================

st.header(
    "👤 Create a Person Agent"
)

linkedin_url = st.text_input(
    "LinkedIn profile URL",
    placeholder=
    "https://www.linkedin.com/in/..."
)

instagram_input = st.text_input(
    "Instagram profile URL or username",
    placeholder=
    "https://www.instagram.com/username/"
)


if st.button(
    "Analyze & Add Person",
    type="primary"
):

    if not linkedin_url or not instagram_input:

        st.warning(
            "Please enter both LinkedIn "
            "and Instagram."
        )

    else:

        instagram_username = (
            extract_instagram_username(
                instagram_input
            )
        )


        try:

            with st.status(
                "Building AI profile...",
                expanded=True
            ) as status:


                st.write(
                    "Reading LinkedIn profile..."
                )


                linkedin_data = (
                    get_linkedin_data(
                        linkedin_url
                    )
                )


                if not linkedin_data:

                    raise RuntimeError(
                        "LinkedIn profile "
                        "could not be read."
                    )


                st.write(
                    "Reading Instagram profile..."
                )


                instagram_data = (
                    get_instagram_data(
                        instagram_username
                    )
                )


                if not instagram_data:

                    raise RuntimeError(
                        "Instagram profile "
                        "could not be read."
                    )


                if (
                    instagram_data.get(
                        "private"
                    )
                    is True
                ):

                    raise RuntimeError(
                        "Instagram profile must be public."
                    )


                person_profile = {
                    "linkedin":
                        linkedin_data,

                    "instagram":
                        instagram_data
                }


                st.write(
                    "Analyzing person with AI..."
                )


                analysis = (
                    analyze_person(
                        person_profile
                    )
                )


                new_profile = {
                    "person":
                        person_profile,

                    "analysis":
                        analysis
                }


                duplicate = False


                for existing in (
                    st.session_state[
                        "profiles"
                    ]
                ):

                    existing_ig = (
                        existing[
                            "person"
                        ][
                            "instagram"
                        ].get(
                            "username"
                        )
                    )


                    if (
                        existing_ig
                        ==
                        instagram_data.get(
                            "username"
                        )
                    ):

                        duplicate = True
                        break


                if duplicate:

                    status.update(
                        label=
                        "Profile already exists",
                        state=
                        "error",
                        expanded=
                        False
                    )

                    st.warning(
                        "This person is already added."
                    )


                else:

                    st.session_state[
                        "profiles"
                    ].append(
                        new_profile
                    )

                    save_profiles()

                    status.update(
                        label=
                        "Person added",
                        state=
                        "complete",
                        expanded=
                        False
                    )

                    st.success(
                        f"{linkedin_data.get('name')} "
                        "added successfully."
                    )


        except Exception as error:

            st.error(
                f"Error: {error}"
            )


# =========================================================
# PEOPLE
# =========================================================

st.divider()

st.header(
    f"👥 People Added: "
    f"{len(st.session_state['profiles'])}"
)


if not st.session_state[
    "profiles"
]:

    st.info(
        "Add a person to begin."
    )


else:

    profile_names = [

        profile[
            "person"
        ][
            "linkedin"
        ].get(
            "name",
            "Unknown"
        )

        for profile
        in st.session_state[
            "profiles"
        ]
    ]


    selected_index = st.selectbox(
        "View Person",
        options=
        range(
            len(profile_names)
        ),
        format_func=
        lambda i:
        profile_names[i]
    )


    selected_profile = (
        st.session_state[
            "profiles"
        ][selected_index]
    )


    person = (
        selected_profile[
            "person"
        ]
    )

    analysis = (
        selected_profile[
            "analysis"
        ]
    )

    linkedin = (
        person[
            "linkedin"
        ]
    )

    instagram = (
        person[
            "instagram"
        ]
    )


    st.subheader(
        linkedin.get(
            "name",
            "Profile"
        )
    )


    st.write(
        linkedin.get(
            "headline",
            ""
        )
    )


    st.write(
        f"Instagram: "
        f"@{instagram.get('username', '')}"
    )


    if instagram.get(
        "verified"
    ):

        st.write(
            "✅ Verified Instagram"
        )


    st.write(
        "### AI Profile Summary"
    )

    st.write(
        analysis.get(
            "short_summary",
            ""
        )
    )


    col1, col2 = (
        st.columns(2)
    )


    with col1:

        st.write(
            "### 🎯 Interests"
        )

        for item in analysis.get(
            "interests",
            []
        ):
            st.write(
                "•",
                item
            )


        st.write(
            "### 🎨 Hobbies"
        )

        for item in analysis.get(
            "hobbies",
            []
        ):
            st.write(
                "•",
                item
            )


        st.write(
            "### 💭 Needs"
        )

        for item in analysis.get(
            "needs",
            []
        ):
            st.write(
                "•",
                item
            )


    with col2:

        st.write(
            "### ❤️ Values"
        )

        for item in analysis.get(
            "values",
            []
        ):
            st.write(
                "•",
                item
            )


        st.write(
            "### 🧠 Personality"
        )

        for item in analysis.get(
            "personality_traits",
            []
        ):
            st.write(
                "•",
                item
            )


        st.write(
            "### 🌍 Lifestyle"
        )

        for item in analysis.get(
            "lifestyle",
            []
        ):
            st.write(
                "•",
                item
            )


# =========================================================
# ALL AGENTS
# =========================================================

if st.session_state[
    "profiles"
]:

    st.divider()

    st.header(
        "🤖 All Agents"
    )


    for index, profile in enumerate(
        st.session_state[
            "profiles"
        ],
        start=1
    ):

        name = (
            profile[
                "person"
            ][
                "linkedin"
            ].get(
                "name",
                "Unknown"
            )
        )


        username = (
            profile[
                "person"
            ][
                "instagram"
            ].get(
                "username",
                ""
            )
        )


        st.write(
            f"{index}. "
            f"{name} — "
            f"@{username}"
        )


# =========================================================
# AGENT DATE
# =========================================================

if len(
    st.session_state[
        "profiles"
    ]
) >= 2:

    st.divider()

    st.header(
        "💞 Agent Date"
    )

    st.caption(
        "Two AI agents meet and evaluate "
        "compatibility on behalf of their people."
    )


    names = [

        profile[
            "person"
        ][
            "linkedin"
        ].get(
            "name",
            "Unknown"
        )

        for profile
        in st.session_state[
            "profiles"
        ]
    ]


    col_a, col_b = (
        st.columns(2)
    )


    with col_a:

        person_a_index = st.selectbox(
            "Person A",
            range(
                len(names)
            ),
            format_func=
            lambda i:
            names[i],
            key=
            "agent_a"
        )


    with col_b:

        person_b_index = st.selectbox(
            "Person B",
            range(
                len(names)
            ),
            index=
            1,
            format_func=
            lambda i:
            names[i],
            key=
            "agent_b"
        )


    if st.button(
        "💘 Start Agent Date",
        type="primary"
    ):

        if (
            person_a_index
            ==
            person_b_index
        ):

            st.warning(
                "Choose two different people."
            )


        else:

            profile_a = (
                st.session_state[
                    "profiles"
                ][
                    person_a_index
                ]
            )


            profile_b = (
                st.session_state[
                    "profiles"
                ][
                    person_b_index
                ]
            )


            try:

                with st.spinner(
                    "Their agents are dating..."
                ):

                    result = (
                        generate_date(
                            profile_a,
                            profile_b
                        )
                    )


                date_record = {
                    "person_a":
                        names[
                            person_a_index
                        ],

                    "person_b":
                        names[
                            person_b_index
                        ],

                    "result":
                        result
                }


                st.session_state[
                    "dates"
                ].append(
                    date_record
                )

                save_dates()


                st.session_state[
                    "current_date"
                ] = (
                    date_record
                )


            except Exception as error:

                st.error(
                    f"Date failed: {error}"
                )


# =========================================================
# DISPLAY DATE
# =========================================================

if st.session_state[
    "current_date"
]:

    date_record = (
        st.session_state[
            "current_date"
        ]
    )


    result = (
        date_record[
            "result"
        ]
    )


    st.divider()


    st.header(
        f"💘 "
        f"{date_record['person_a']} "
        f"× "
        f"{date_record['person_b']}"
    )


    st.caption(
        "Their AI agents are speaking "
        "on their behalf."
    )


    for message in result.get(
        "conversation",
        []
    ):

        speaker = message.get(
            "speaker",
            "Agent"
        )

        text = message.get(
            "message",
            ""
        )


        with st.chat_message(
            "assistant"
        ):

            st.markdown(
                f"**{speaker}**"
            )

            st.write(
                text
            )


    score = result.get(
        "compatibility_score",
        0
    )


    st.subheader(
        f"Compatibility: "
        f"{score}%"
    )


    st.progress(
        max(
            0,
            min(
                score,
                100
            )
        ) / 100
    )


    breakdown = result.get(
        "compatibility_breakdown",
        {}
    )


    st.write(
        "### Compatibility Breakdown"
    )


    cols = st.columns(5)


    cols[0].metric(
        "Interests",
        f"{breakdown.get('interests', 0)}%"
    )

    cols[1].metric(
        "Values",
        f"{breakdown.get('values', 0)}%"
    )

    cols[2].metric(
        "Lifestyle",
        f"{breakdown.get('lifestyle', 0)}%"
    )

    cols[3].metric(
        "Personality",
        f"{breakdown.get('personality', 0)}%"
    )

    cols[4].metric(
        "Needs",
        f"{breakdown.get('needs', 0)}%"
    )


    left, right = st.columns(2)


    with left:

        st.write(
            "### ✅ Strengths"
        )

        for item in result.get(
            "strengths",
            []
        ):
            st.write(
                "•",
                item
            )


    with right:

        st.write(
            "### ⚠️ Differences"
        )

        for item in result.get(
            "differences",
            []
        ):
            st.write(
                "•",
                item
            )


    st.write(
        "### 💬 Agent Verdict"
    )

    st.write(
        result.get(
            "verdict",
            ""
        )
    )


# =========================================================
# RANKINGS
# =========================================================

if len(
    st.session_state[
        "profiles"
    ]
) >= 2:

    st.divider()

    st.header(
        "🏆 Match Rankings"
    )

    st.caption(
        "Each person's agent ranks other people "
        "using interests, hobbies, values, needs, "
        "personality and lifestyle."
    )


    rankings = build_rankings(
        st.session_state[
            "profiles"
        ]
    )


    ranking_person = st.selectbox(
        "Show rankings for",
        list(
            rankings.keys()
        ),
        key=
        "ranking_person"
    )


    person_rankings = (
        rankings[
            ranking_person
        ]
    )


    st.subheader(
        f"Best matches for "
        f"{ranking_person}"
    )


    for rank, match in enumerate(
        person_rankings,
        start=1
    ):

        score = (
            match[
                "score"
            ]
        )


        if rank == 1:
            medal = "🥇"

        elif rank == 2:
            medal = "🥈"

        elif rank == 3:
            medal = "🥉"

        else:
            medal = f"#{rank}"


        st.markdown(
            f"### {medal} "
            f"{match['name']} — "
            f"{score}%"
        )


        st.progress(
            score / 100
        )


        details = (
            match[
                "details"
            ]
        )


        with st.expander(
            "View match breakdown"
        ):

            cols = st.columns(3)


            cols[0].metric(
                "Interests",
                f"{details['interests']}%"
            )

            cols[1].metric(
                "Values",
                f"{details['values']}%"
            )

            cols[2].metric(
                "Lifestyle",
                f"{details['lifestyle']}%"
            )


            cols = st.columns(3)


            cols[0].metric(
                "Hobbies",
                f"{details['hobbies']}%"
            )

            cols[1].metric(
                "Personality",
                f"{details['personality']}%"
            )

            cols[2].metric(
                "Needs",
                f"{details['needs']}%"
            )


# =========================================================
# DATE HISTORY
# =========================================================

if st.session_state[
    "dates"
]:

    st.divider()

    st.header(
        "📜 Agent Date History"
    )


    for index, date in enumerate(
        st.session_state[
            "dates"
        ],
        start=1
    ):

        score = (
            date[
                "result"
            ].get(
                "compatibility_score",
                0
            )
        )


        st.write(
            f"{index}. "
            f"{date['person_a']} × "
            f"{date['person_b']} "
            f"— {score}%"
        )


# =========================================================
# CLEAR
# =========================================================

if st.session_state[
    "profiles"
]:

    st.divider()


    if st.button(
        "🗑️ Clear Everything"
    ):

        st.session_state[
            "profiles"
        ] = []

        st.session_state[
            "dates"
        ] = []

        st.session_state[
            "current_date"
        ] = None


        save_profiles()
        save_dates()

        st.rerun()