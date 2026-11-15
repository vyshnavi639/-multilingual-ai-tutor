from pathlib import Path
import re

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
CURRICULUM_FOLDER = PROJECT_FOLDER / "data" / "curriculum"


def read_file(file_path):
    """Read a text file or PDF and return its text."""

    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        pages = []

        for page in reader.pages:
            pages.append(page.extract_text() or "")

        return "\n".join(pages)

    return ""


def split_into_chunks(text, filename):
    """Split curriculum text into manageable passages."""

    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if len(paragraph) < 25:
            continue

        chunks.append({
            "content": paragraph,
            "filename": filename
        })

    return chunks


def load_documents():
    """Load curriculum passages from the curriculum folder."""

    documents = []

    if not CURRICULUM_FOLDER.exists():
        raise FileNotFoundError(
            f"Curriculum folder not found: {CURRICULUM_FOLDER}"
        )

    supported_extensions = {".txt", ".pdf"}

    for file_path in CURRICULUM_FOLDER.iterdir():

        if file_path.suffix.lower() not in supported_extensions:
            continue

        try:
            text = read_file(file_path)

            documents.extend(
                split_into_chunks(text, file_path.name)
            )

        except Exception as error:
            print(f"Could not read {file_path.name}: {error}")

    return documents


def normalize(text):
    """Normalize text for subject matching."""

    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def retrieve_relevant_material(
    question,
    subject,
    top_k=4,
    min_score=0.03
):
    """Return the most relevant curriculum passages."""

    if not question.strip():
        return []

    documents = load_documents()

    if not documents:
        return []

    # Restrict the search to the selected subject.
    subject_key = normalize(subject)
    subject_words = set(subject_key.split())

    filtered_documents = []

    for document in documents:
        filename = document["filename"]
        content = document["content"]

        # Subject is normally present in the filename or
        # curriculum text, for example "Computer Networks".
        combined = normalize(filename + " " + content)

        matches = subject_words.intersection(
            set(combined.split())
        )

        if matches:
            filtered_documents.append(document)

    if not filtered_documents:
        return []

    passages = [
        document["content"]
        for document in filtered_documents
    ]

    # Fit TF-IDF on the selected passages and question.
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    try:
        matrix = vectorizer.fit_transform(
            passages + [question]
        )
    except ValueError:
        return []

    passage_vectors = matrix[:-1]
    question_vector = matrix[-1]

    scores = cosine_similarity(
        question_vector,
        passage_vectors
    ).flatten()

    ranked = []

    for index, score in enumerate(scores):

        if score >= min_score:
            ranked.append({
                "filename": filtered_documents[index]["filename"],
                "content": filtered_documents[index]["content"],
                "score": float(score)
            })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked[:top_k]


if __name__ == "__main__":

    print("Curriculum search test")
    print("Available subjects: Computer Networks, DBMS")

    question = input("Enter your question: ")
    subject = input("Enter the subject: ")

    results = retrieve_relevant_material(
        question,
        subject
    )

    if results:
        for result in results:
            print("\nSource:", result["filename"])
            print("Relevance score:", round(result["score"], 3))
            print("Passage:", result["content"])
    else:
        print("No matching curriculum material found.")