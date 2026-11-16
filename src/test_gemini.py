import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: API key not found in .env")
else:
    print("API key loaded successfully.")

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents="Explain what a computer network is in two sentences."
        )

        print("\nGEMINI RESPONSE:")
        print(response.text)

    except Exception as error:
        print("\nGEMINI CONNECTION FAILED:")
        print(type(error).__name__)
        print(str(error))