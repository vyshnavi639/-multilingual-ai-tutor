import os
import json
import re
import time
import random

import streamlit as st
from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# API CONFIGURATION
# --------------------------------------------------

def get_api_key():

    """Get API key from Streamlit Secrets or .env."""

    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")

        if api_key:
            return api_key

    except Exception:
        pass

    return os.getenv("GEMINI_API_KEY", "")


def get_model_name():

    """Get primary Gemini model."""

    try:
        model = st.secrets.get("GEMINI_MODEL", "")

        if model:
            return model

    except Exception:
        pass

    return os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )


def get_fallback_models():

    """Get optional backup models."""

    try:
        models = st.secrets.get(
            "GEMINI_FALLBACK_MODELS",
            ""
        )

    except Exception:
        models = os.getenv(
            "GEMINI_FALLBACK_MODELS",
            ""
        )

    if isinstance(models, str):

        return [
            model.strip()
            for model in models.split(",")
            if model.strip()
        ]

    return []


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

def get_client():

    """Create Gemini API client."""

    api_key = get_api_key()

    if not api_key:

        raise ValueError(
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to your .env file."
        )

    return genai.Client(api_key=api_key)


# --------------------------------------------------
# ERROR DETECTION
# --------------------------------------------------

def is_temporary_error(error):

    """Identify temporary Gemini API errors."""

    message = str(error).lower()

    indicators = [
        "503",
        "unavailable",
        "high demand",
        "429",
        "resource_exhausted",
        "rate limit",
        "500",
        "502",
        "504",
        "internal server error",
        "deadline exceeded",
        "temporarily unavailable",
        "timeout",
        "overloaded"
    ]

    return any(
        item in message
        for item in indicators
    )


def is_authentication_error(error):

    """Identify API authentication failures."""

    message = str(error).lower()

    indicators = [
        "401",
        "403",
        "unauthorized",
        "permission denied",
        "api key not valid",
        "invalid api key"
    ]

    return any(
        item in message
        for item in indicators
    )


# --------------------------------------------------
# GENERATE TEXT WITH RETRIES
# --------------------------------------------------

def generate_text(prompt):

    """
    Generate Gemini responses.

    Features:
    - Automatic retry
    - Exponential backoff
    - Random wait variation
    - Backup model support
    """

    client = get_client()

    primary_model = get_model_name()

    fallback_models = get_fallback_models()

    models = list(dict.fromkeys(
        [primary_model] + fallback_models
    ))

    max_attempts = 4

    last_error = None

    for model_name in models:

        print(
            f"Using Gemini model: {model_name}"
        )

        for attempt in range(max_attempts):

            try:

                response = client.models.generate_content(

                    model=model_name,

                    contents=prompt

                )

                if response and response.text:

                    return response.text.strip()

                raise ValueError(
                    "Gemini returned an empty response."
                )

            except Exception as error:

                last_error = error

                print(
                    f"Gemini model: {model_name}"
                )

                print(
                    f"Attempt {attempt + 1}/"
                    f"{max_attempts} failed: {error}"
                )

                # Authentication errors cannot
                # be solved by switching models.

                if is_authentication_error(error):

                    raise

                # Retry temporary errors.

                if is_temporary_error(error):

                    if attempt == max_attempts - 1:

                        print(
                            f"Maximum retries reached "
                            f"for {model_name}."
                        )

                        break

                    wait_time = min(
                        2 ** attempt,
                        15
                    )

                    wait_time += random.uniform(
                        0,
                        1
                    )

                    print(
                        f"Retrying in "
                        f"{wait_time:.1f} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

                # Do not repeatedly retry
                # permanent errors.

                print(
                    "Non-temporary Gemini error."
                )

                break

        # Try next configured model.

        if model_name != models[-1]:

            print(
                "Switching to backup Gemini model..."
            )

    if last_error:

        raise RuntimeError(
            f"All configured Gemini models failed. "
            f"Last error: {last_error}"
        ) from last_error

    raise RuntimeError(
        "No Gemini model was configured."
    )


# --------------------------------------------------
# MULTILINGUAL SEARCH QUERY
# --------------------------------------------------

def make_search_query(question):

    """
    Convert multilingual questions into
    English curriculum search queries.
    """

    prompt = f"""
Convert the following student question into a short
English search query suitable for searching
English curriculum notes.

Preserve technical terms and original meaning.

Return only the search query.

Student question:
{question}
"""

    try:

        result = generate_text(prompt)

        if result:

            return result.strip()

    except Exception as error:

        print(
            f"Search conversion failed: {error}"
        )

    # Fallback to original question.

    return question


# --------------------------------------------------
# ANSWER GENERATION
# --------------------------------------------------

def answer_question(
    question,
    subject,
    language,
    sources
):

    """
    Generate curriculum-grounded answers.
    """

    if not sources:

        return (
            "I could not find enough relevant information "
            "in the selected curriculum material to answer "
            "this question reliably. Try another question "
            "or add relevant notes to the curriculum."
        )

    context_parts = []

    for index, source in enumerate(
        sources,
        start=1
    ):

        filename = source.get(
            "filename",
            "Unknown source"
        )

        content = source.get(
            "content",
            ""
        )

        context_parts.append(
            f"Source {index}: {filename}\n{content}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a patient and helpful educational tutor.

Selected subject: {subject}

Required answer language: {language}

Student question:
{question}

Curriculum passages:
{context}

Instructions:

1. Answer using the supplied curriculum passages.
2. Explain in simple language suitable for beginners.
3. Give a small example when useful.
4. Clearly identify information not supported
   by the supplied passages.
5. Never invent citations or page numbers.
6. Do not claim to have searched unavailable sources.
7. Write entirely in the required language.
8. Use short headings when useful.
9. Make the explanation educational and clear.
10. Stay relevant to the selected subject.
"""

    try:

        response = generate_text(prompt)

        if response:

            return response.strip()

        return (
            "Gemini returned an empty response. "
            "Please try again."
        )

    except Exception as error:

        print(
            f"Answer generation error: {error}"
        )

        return (
            "The AI service is temporarily unavailable "
            "or could not process your request. "
            "Please try again later. "
            "Your curriculum data is not affected."
        )


# --------------------------------------------------
# QUIZ JSON EXTRACTION
# --------------------------------------------------

def extract_json(response):

    """
    Extract JSON from Gemini output.

    Handles optional markdown fences
    and additional surrounding text.
    """

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        response,
        flags=re.IGNORECASE
    )

    cleaned = cleaned.replace(
        "```",
        ""
    ).strip()

    start = cleaned.find("[")

    end = cleaned.rfind("]")

    if start == -1 or end == -1 or end < start:

        raise ValueError(
            "No valid JSON array found."
        )

    json_text = cleaned[start:end + 1]

    return json.loads(json_text)


# --------------------------------------------------
# QUIZ GENERATION
# --------------------------------------------------

def generate_quiz(
    subject,
    language,
    sources,
    number=3
):

    """
    Generate curriculum-based MCQs.

    Returns a validated list of questions.
    """

    if not sources:

        return []

    number = max(
        1,
        min(int(number), 10)
    )

    context = "\n\n".join(

        source.get("content", "")

        for source in sources

    )

    prompt = f"""
Create {number} beginner-friendly multiple-choice
questions based ONLY on the supplied curriculum.

Subject: {subject}

Question language: {language}

Return ONLY valid JSON in this format:

[
    {{
        "question": "Question text",
        "options": [
            "Option A",
            "Option B",
            "Option C",
            "Option D"
        ],
        "answer": 0,
        "explanation": "Short explanation"
    }}
]

RULES:

1. Generate exactly four options per question.
2. The correct answer must be an integer from 0 to 3.
3. Explanations must be based on the notes.
4. No markdown code fences.
5. Return valid JSON only.
6. Do not generate questions outside the curriculum.
7. Avoid duplicate questions.
8. Use the requested language.

Curriculum:

{context}
"""

    try:

        response = generate_text(prompt)

        if not response:

            return []

        questions = extract_json(response)

        if not isinstance(questions, list):

            return []

        valid_questions = []

        for item in questions:

            if not isinstance(item, dict):

                continue

            question = item.get("question")

            options = item.get("options")

            answer = item.get("answer")

            explanation = item.get(
                "explanation",
                ""
            )

            # Validate question.

            if not isinstance(question, str):

                continue

            if not question.strip():

                continue

            # Validate options.

            if not isinstance(options, list):

                continue

            if len(options) != 4:

                continue

            if not all(
                isinstance(option, str)
                and option.strip()
                for option in options
            ):

                continue

            # Validate correct answer.

            if not isinstance(answer, int):

                continue

            if isinstance(answer, bool):

                continue

            if answer < 0 or answer > 3:

                continue

            # Validate explanation.

            if not isinstance(explanation, str):

                explanation = ""

            valid_questions.append({

                "question": question.strip(),

                "options": options,

                "answer": answer,

                "explanation": explanation.strip()

            })

        return valid_questions[:number]

    except Exception as error:

        print(
            f"Quiz generation failed: {error}"
        )

        return []


# --------------------------------------------------
# END OF GEMINI MODULE
# --------------------------------------------------