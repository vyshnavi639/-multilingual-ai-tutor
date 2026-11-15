import os
import json
import re

from dotenv import load_dotenv
from google import genai


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)


def get_client():
    """Return an AI client if an API key is available."""

    if not API_KEY:
        return None

    return genai.Client(api_key=API_KEY)


def generate_text(prompt):
    """Generate text with Gemini."""

    client = get_client()

    if client is None:
        return None

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text or ""


def make_search_query(question):
    """Convert a multilingual question into English search terms."""

    prompt = f"""
Convert the following student question into a short English
search query suitable for searching English curriculum notes.

Preserve technical terms and the original meaning.
Return only the search query, without explanation.

Student question:
{question}
"""

    try:
        result = generate_text(prompt)

        if result:
            return result.strip()

    except Exception:
        pass

    # Without AI, use the original question.
    return question


def answer_question(question, subject, language, sources):
    """Answer using retrieved curriculum passages."""

    if not sources:
        return (
            "I could not find enough relevant information in the "
            "selected curriculum material to answer this question "
            "reliably. Try a different question or add relevant "
            "notes to the curriculum."
        )

    context_parts = []

    for index, source in enumerate(sources, start=1):
        context_parts.append(
            f"Source {index}: {source['filename']}\n"
            f"{source['content']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a patient, helpful educational tutor.

Selected subject: {subject}
Required answer language: {language}

Student question:
{question}

Curriculum passages:
{context}

Instructions:
1. Answer the question using the supplied curriculum passages.
2. Explain in simple language suitable for a beginner.
3. Use a small example when useful.
4. If a detail is not supported by the passages, clearly say so.
5. Do not invent citations, page numbers, or source details.
6. Do not claim that you searched a source that was not supplied.
7. Use the required answer language.
8. Structure the response with short headings when useful.
"""

    try:
        response = generate_text(prompt)

        if response:
            return response.strip()

        return (
            "The AI service is not configured. "
            "Please configure the Gemini API key to enable "
            "AI-generated explanations."
        )

    except Exception as error:
        return (
            "The AI service could not generate an answer. "
            "Check the API key, model availability, internet "
            "connection, and usage limits. "
            f"Technical detail: {error}"
        )


def generate_quiz(subject, language, sources, number=3):
    """Generate a multiple-choice quiz from curriculum passages."""

    if not sources:
        return []

    context = "\n\n".join(
        source["content"] for source in sources
    )

    prompt = f"""
Create {number} beginner-friendly multiple-choice questions
based only on the following curriculum passages.

Subject: {subject}
Question language: {language}

Return ONLY valid JSON in this exact format:
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
    "explanation": "Short explanation based on the notes"
  }}
]

The answer field must be an integer from 0 to 3 representing
the correct option's index.

Do not include markdown code fences.

Curriculum:
{context}
"""

    try:
        response = generate_text(prompt)

        if not response:
            return []

        # Tolerate a model response that includes code fences.
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            response.strip(),
            flags=re.IGNORECASE
        )

        questions = json.loads(cleaned)

        valid_questions = []

        for item in questions:
            options = item.get("options", [])
            answer = item.get("answer")

            if (
                isinstance(item.get("question"), str)
                and len(options) == 4
                and isinstance(answer, int)
                and 0 <= answer < 4
            ):
                valid_questions.append(item)

        return valid_questions

    except Exception:
        return []