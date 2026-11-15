import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.retriever import retrieve_relevant_material
from src.tutor import (
    make_search_query,
    answer_question,
    generate_quiz
)
from src.database import (
    initialize_database,
    save_activity,
    get_all_activity
)


load_dotenv()
initialize_database()

st.set_page_config(
    page_title="Multilingual AI Tutor",
    page_icon="📚",
    layout="wide"
)


# -----------------------------
# PAGE HEADER
# -----------------------------

st.title("📚 Multilingual Curriculum-Grounded AI Tutor")

st.write(
    "Learn concepts using curriculum material, "
    "ask questions in your preferred language, "
    "and practise with adaptive quizzes."
)

st.caption(
    "Prototype: answers depend on the curriculum files "
    "available in the application."
)


# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a section",
    [
        "Student Tutor",
        "Practice Quiz",
        "Teacher Dashboard"
    ]
)

student = st.sidebar.text_input(
    "Student display name",
    value="Student 1",
    max_chars=60
).strip()

subject = st.sidebar.selectbox(
    "Select subject",
    [
        "Computer Networks",
        "DBMS"
    ]
)

language = st.sidebar.selectbox(
    "Preferred answer language",
    [
        "English",
        "Hindi",
        "Telugu",
        "Tamil",
        "Kannada",
        "Malayalam"
    ]
)


# -----------------------------
# HELPER FUNCTION
# -----------------------------

def get_sources(question, selected_subject):
    """Convert the query if possible and retrieve curriculum."""

    search_question = make_search_query(question)

    return retrieve_relevant_material(
        search_question,
        selected_subject,
        top_k=5,
        min_score=0.03
    )


# -----------------------------
# STUDENT TUTOR
# -----------------------------

if page == "Student Tutor":

    st.header("Ask Your Doubt")

    st.write(
        "Select a subject, type your question, "
        "and the tutor will search the curriculum."
    )

    question = st.text_area(
        "Enter your question",
        placeholder=(
            "Example: What is the difference between "
            "a hub and a switch?"
        ),
        height=120,
        key="student_question"
    )

    if st.button(
        "Find Answer",
        type="primary"
    ):

        if not student:
            st.warning("Enter a student display name.")
        elif not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner(
                "Searching curriculum and preparing an answer..."
            ):

                try:
                    sources = get_sources(
                        question,
                        subject
                    )

                    answer = answer_question(
                        question,
                        subject,
                        language,
                        sources
                    )

                    st.session_state["last_answer"] = answer
                    st.session_state["last_sources"] = sources
                    st.session_state["last_question"] = question
                    st.session_state["last_subject"] = subject

                    source_names = ", ".join(
                        sorted({
                            source["filename"]
                            for source in sources
                        })
                    )

                    save_activity(
                        student,
                        subject,
                        "Doubt Resolution",
                        question,
                        None,
                        source_names
                    )

                except Exception as error:
                    st.error(
                        "Something went wrong while processing "
                        "the question."
                    )
                    st.exception(error)

    if "last_answer" in st.session_state:

        st.subheader("Tutor's Explanation")

        st.markdown(
            st.session_state["last_answer"]
        )

        sources = st.session_state.get(
            "last_sources",
            []
        )

        if sources:
            st.subheader("Curriculum Sources")

            for source in sources:
                with st.expander(
                    f"📄 {source['filename']} "
                    f"(relevance: {source['score']:.2f})"
                ):
                    st.write(source["content"])

        else:
            st.info(
                "No relevant curriculum passages were found. "
                "Try a more specific question or add suitable notes."
            )

        st.caption(
            "Always verify important information against "
            "the original curriculum."
        )


# -----------------------------
# PRACTICE QUIZ
# -----------------------------

elif page == "Practice Quiz":

    st.header("Practice Quiz")

    st.write(
        "Generate multiple-choice questions from your "
        "selected subject's curriculum."
    )

    if st.button(
        "Generate Quiz",
        type="primary"
    ):

        if not student:
            st.warning("Enter a student display name.")
        else:
            with st.spinner("Preparing your quiz..."):

                try:
                    # Retrieve a broad set of passages from
                    # the selected subject.
                    sources = retrieve_relevant_material(
                        "important concepts definitions key facts",
                        subject,
                        top_k=10,
                        min_score=0.0
                    )

                    questions = generate_quiz(
                        subject,
                        language,
                        sources,
                        number=3
                    )

                    st.session_state["quiz_questions"] = questions
                    st.session_state["quiz_subject"] = subject
                    st.session_state["quiz_sources"] = sources

                except Exception as error:
                    st.error("Could not generate the quiz.")
                    st.exception(error)

    questions = st.session_state.get(
        "quiz_questions",
        []
    )

    if questions:

        st.subheader(
            f"Quiz: {st.session_state.get('quiz_subject', subject)}"
        )

        with st.form("quiz_form"):

            selected_answers = []

            for index, item in enumerate(questions):

                st.markdown(
                    f"**Question {index + 1}: "
                    f"{item['question']}**"
                )

                selected = st.radio(
                    "Choose one answer",
                    options=list(range(len(item["options"]))),
                    format_func=lambda choice, opts=item["options"]: (
                        opts[choice]
                    ),
                    key=f"quiz_answer_{index}"
                )

                selected_answers.append(selected)

            submitted = st.form_submit_button(
                "Submit Quiz"
            )

        if submitted:

            correct = 0

            for index, item in enumerate(questions):

                selected = selected_answers[index]
                answer = item["answer"]

                if selected == answer:
                    correct += 1

                st.markdown(
                    f"**Question {index + 1} explanation:** "
                    f"{item.get('explanation', 'Review the curriculum notes.')}"
                )

                if selected == answer:
                    st.success("Correct!")
                else:
                    st.info(
                        "Review this concept and try again."
                    )

                st.write(
                    "Correct answer: "
                    + item["options"][answer]
                )

            percentage = round(
                (correct / len(questions)) * 100,
                2
            )

            st.metric(
                "Your score",
                f"{correct}/{len(questions)}"
            )

            st.progress(
                int(percentage)
            )

            st.write(
                f"Percentage: {percentage}%"
            )

            sources = st.session_state.get(
                "quiz_sources",
                []
            )

            source_names = ", ".join(
                sorted({
                    source["filename"]
                    for source in sources
                })
            )

            save_activity(
                student,
                st.session_state.get(
                    "quiz_subject",
                    subject
                ),
                "Practice Quiz",
                f"Completed {len(questions)} questions",
                percentage,
                source_names
            )

            if percentage < 60:
                st.info(
                    "Recommendation: revise the relevant "
                    "curriculum material and practise again."
                )
            elif percentage < 80:
                st.info(
                    "Recommendation: review any missed "
                    "questions and attempt another quiz."
                )
            else:
                st.success(
                    "Good work! Try a more challenging "
                    "set of questions next."
                )

    elif st.session_state.get("quiz_questions") == []:
        st.info(
            "No quiz is currently available. Generate a quiz "
            "after checking that the curriculum files and "
            "Gemini API configuration are working."
        )


# -----------------------------
# TEACHER DASHBOARD
# -----------------------------

elif page == "Teacher Dashboard":

    st.header("Teacher Dashboard")

    st.write(
        "Review prototype learning activity and quiz results."
    )

    teacher_password = os.getenv(
        "TEACHER_PASSWORD",
        ""
    )

    if not teacher_password:
        st.warning(
            "Teacher dashboard access is not configured. "
            "Set TEACHER_PASSWORD in your local .env file "
            "before using this screen."
        )

    else:
        entered_password = st.text_input(
            "Teacher password",
            type="password"
        )

        if entered_password == teacher_password:

            rows = get_all_activity()

            columns = [
                "Student",
                "Subject",
                "Activity",
                "Question / Activity Details",
                "Score (%)",
                "Curriculum Sources",
                "Date"
            ]

            if not rows:
                st.info(
                    "No student activity has been recorded yet."
                )

            else:
                dataframe = pd.DataFrame(
                    rows,
                    columns=columns
                )

                st.subheader("Activity Summary")

                total_activities = len(dataframe)

                quiz_scores = dataframe.loc[
                    dataframe["Activity"] == "Practice Quiz",
                    "Score (%)"
                ].dropna()

                first, second = st.columns(2)

                first.metric(
                    "Total activities",
                    total_activities
                )

                if not quiz_scores.empty:
                    second.metric(
                        "Average quiz score",
                        f"{quiz_scores.mean():.1f}%"
                    )
                else:
                    second.metric(
                        "Quiz attempts",
                        0
                    )

                st.subheader("Recorded Activities")

                st.dataframe(
                    dataframe,
                    use_container_width=True
                )

                st.subheader("Quiz Results by Subject")

                if not quiz_scores.empty:

                    quiz_data = dataframe.loc[
                        dataframe["Activity"] == "Practice Quiz"
                    ].copy()

                    quiz_data["Score (%)"] = pd.to_numeric(
                        quiz_data["Score (%)"],
                        errors="coerce"
                    )

                    averages = quiz_data.groupby(
                        "Subject"
                    )["Score (%)"].mean()

                    st.bar_chart(averages)

                st.caption(
                    "This prototype records display names and "
                    "scores only; it does not authenticate student "
                    "identities or provide a production-secure "
                    "teacher account system."
                )

        elif entered_password:
            st.error("Incorrect teacher password.")