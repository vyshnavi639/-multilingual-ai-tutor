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


# --------------------------------------------------
# INITIALIZATION
# --------------------------------------------------

st.set_page_config(
    page_title="Multilingual AI Tutor",
    page_icon="📚",
    layout="wide"
)

load_dotenv()
initialize_database()


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

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


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

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


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_sources(question, selected_subject):
    """
    Search curriculum using the original question,
    translated question, and a relaxed threshold.

    Returns:
        sources: Retrieved curriculum passages.
        diagnostics: Information about search attempts.
    """

    diagnostics = []

    # ----------------------------------------------
    # SEARCH 1: ORIGINAL STUDENT QUESTION
    # ----------------------------------------------

    try:

        sources = retrieve_relevant_material(
            question,
            selected_subject,
            top_k=5,
            min_score=0.03
        )

        diagnostics.append({
            "Search": "Original student question",
            "Query": question,
            "Results": len(sources) if sources else 0
        })

        if sources:
            return sources, diagnostics

    except Exception as error:

        diagnostics.append({
            "Search": "Original student question",
            "Query": question,
            "Results": 0,
            "Error": str(error)
        })

    # ----------------------------------------------
    # SEARCH 2: TRANSLATED ENGLISH QUESTION
    # ----------------------------------------------

    try:

        translated_question = make_search_query(question)

        if (
            translated_question
            and translated_question.strip()
            and translated_question.strip().lower()
            != question.strip().lower()
        ):

            sources = retrieve_relevant_material(
                translated_question,
                selected_subject,
                top_k=5,
                min_score=0.03
            )

            diagnostics.append({
                "Search": "Translated question",
                "Query": translated_question,
                "Results": len(sources) if sources else 0
            })

            if sources:
                return sources, diagnostics

    except Exception as error:

        diagnostics.append({
            "Search": "Translated question",
            "Query": "Translation unavailable",
            "Results": 0,
            "Error": str(error)
        })

    # ----------------------------------------------
    # SEARCH 3: RELAXED RELEVANCE THRESHOLD
    # ----------------------------------------------

    try:

        sources = retrieve_relevant_material(
            question,
            selected_subject,
            top_k=5,
            min_score=0.0
        )

        diagnostics.append({
            "Search": "Relaxed relevance threshold",
            "Query": question,
            "Results": len(sources) if sources else 0
        })

        if sources:
            return sources, diagnostics

    except Exception as error:

        diagnostics.append({
            "Search": "Relaxed relevance threshold",
            "Query": question,
            "Results": 0,
            "Error": str(error)
        })

    return [], diagnostics


def get_source_names(sources):
    """Safely extract curriculum filenames."""

    return ", ".join(
        sorted({
            source.get("filename", "Unknown source")
            for source in sources
        })
    )


def show_search_diagnostics(diagnostics):
    """Display curriculum retrieval information."""

    with st.expander("🔍 Search Diagnostics"):

        if not diagnostics:
            st.info("No search information available.")
            return

        for item in diagnostics:

            st.write(
                f"**Search:** {item['Search']}"
            )

            st.write(
                f"**Query:** {item['Query']}"
            )

            st.write(
                f"**Retrieved passages:** {item['Results']}"
            )

            if item.get("Error"):
                st.error(item["Error"])

            st.divider()


# --------------------------------------------------
# STUDENT TUTOR
# --------------------------------------------------

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

            st.warning(
                "Enter a student display name."
            )

        elif not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Searching curriculum and preparing an answer..."
            ):

                try:

                    # Retrieve curriculum passages.
                    sources, diagnostics = get_sources(
                        question,
                        subject
                    )

                    # Generate curriculum-grounded answer.
                    answer = answer_question(
                        question,
                        subject,
                        language,
                        sources
                    )

                    # Store results in session state.
                    st.session_state["last_answer"] = answer

                    st.session_state["last_sources"] = sources

                    st.session_state["last_question"] = question

                    st.session_state["last_subject"] = subject

                    st.session_state["last_diagnostics"] = diagnostics

                    st.session_state["last_language"] = language

                    # Save activity.
                    save_activity(
                        student,
                        subject,
                        "Doubt Resolution",
                        question,
                        None,
                        get_source_names(sources)
                    )

                except Exception as error:

                    st.error(
                        "Something went wrong while processing "
                        "your question."
                    )

                    st.exception(error)

    # ----------------------------------------------
    # DISPLAY ANSWER
    # ----------------------------------------------

    if "last_answer" in st.session_state:

        st.subheader("Tutor's Explanation")

        st.markdown(
            st.session_state["last_answer"]
        )

        sources = st.session_state.get(
            "last_sources",
            []
        )

        # ------------------------------------------
        # DISPLAY CURRICULUM SOURCES
        # ------------------------------------------

        if sources:

            st.success(
                f"Successfully retrieved {len(sources)} "
                "curriculum passages."
            )

            st.subheader("Curriculum Sources")

            for index, source in enumerate(sources, start=1):

                filename = source.get(
                    "filename",
                    "Unknown source"
                )

                score = source.get(
                    "score",
                    0
                )

                with st.expander(
                    f"📄 {filename} "
                    f"(Relevance: {score:.2f})"
                ):

                    st.write(
                        source.get("content", "")
                    )

        else:

            st.warning(
                "No relevant curriculum passages were found."
            )

            st.info(
                "Check whether your curriculum files are "
                "uploaded, indexed and available for the "
                "selected subject."
            )

        # Display retrieval diagnostics.
        show_search_diagnostics(
            st.session_state.get(
                "last_diagnostics",
                []
            )
        )

        st.caption(
            "Always verify important information against "
            "the original curriculum."
        )


# --------------------------------------------------
# PRACTICE QUIZ
# --------------------------------------------------

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

            st.warning(
                "Enter a student display name."
            )

        else:

            with st.spinner(
                "Searching curriculum and preparing your quiz..."
            ):

                try:

                    sources = retrieve_relevant_material(
                        "important concepts definitions key facts",
                        subject,
                        top_k=10,
                        min_score=0.0
                    )

                    if not sources:

                        st.warning(
                            "No curriculum passages were found. "
                            "Check your curriculum files and indexing."
                        )

                        st.session_state["quiz_questions"] = []

                    else:

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

                    st.error(
                        "Could not generate the quiz."
                    )

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

                    options=list(
                        range(len(item["options"]))
                    ),

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

            save_activity(
                student,

                st.session_state.get(
                    "quiz_subject",
                    subject
                ),

                "Practice Quiz",

                f"Completed {len(questions)} questions",

                percentage,

                get_source_names(sources)
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
            "No quiz is currently available. Check your "
            "curriculum files and Gemini API configuration."
        )


# --------------------------------------------------
# TEACHER DASHBOARD
# --------------------------------------------------

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
                    "scores only. It does not authenticate student "
                    "identities or provide a production-secure "
                    "teacher account system."
                )

        elif entered_password:

            st.error(
                "Incorrect teacher password."
            )