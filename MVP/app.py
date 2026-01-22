import pandas as pd
from datetime import datetime
import streamlit as st
import os
from openai import OpenAI

# =========================
# PLATFORM CONFIG
# =========================
GRADE_OPTIONS = [
    "Kindergarten",
    "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
    "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11", "Grade 12"
]

def grade_to_number(g):
    return 0 if g == "Kindergarten" else int(g.split()[-1])

def allowed_subjects_for_grade(grade):
    g = grade_to_number(grade)
    if g <= 8:
        return ["Math", "Science", "Coding"]
    return ["Math", "Biology", "Physics", "Chemistry", "Coding"]

MODE_OPTIONS = ["Learn a Topic", "Practice Problems", "Homework Help"]
def build_system_prompt(subject, grade, mode):
    g = grade_to_number(grade)

    if g <= 5:
        tone = "Use simple words, short steps, and encouragement."
    elif g <= 8:
        tone = "Use clear step-by-step explanations with checks for understanding."
    else:
        tone = "Use structured, exam-ready explanations with reasoning."

    if mode == "Homework Help":
        policy = (
            "Guide step-by-step. Do not jump to final answers immediately. "
            "Ask the student to try parts before showing full solutions."
        )
    else:
        policy = "Teach for understanding with examples and practice."

    return f"""
You are a safe K–12 AI learning companion.
Subject: {subject}
Grade: {grade}
Mode: {mode}

Rules:
- {tone}
- {policy}
- End with one short check question.
"""
resolved = pd.DataFrame()
help_message = ""

# Page configuration
st.set_page_config(page_title="Smart Tutor AI", page_icon="📘", layout="centered")

# Sidebar navigation
page = st.sidebar.selectbox("Navigate", ["Tutor", "Parent Dashboard", "Tutor Dashboard", "Why Parents Trust Us"])

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or "")
# -------------------------
# Tutor Page
# -------------------------
if page == "Tutor":

    st.title("Smart Learning Companion")

student_name = st.text_input("Student name", value=st.session_state.get("student_name","Student"))
st.session_state.student_name = student_name

grade = st.selectbox("Grade", GRADE_OPTIONS, index=7)
subject = st.selectbox("Subject", allowed_subjects_for_grade(grade))
mode = st.radio("Learning Mode", MODE_OPTIONS, horizontal=True)

topic = ""
homework_text = ""

if mode in ["Learn a Topic", "Practice Problems"]:
    topic = st.text_input("Topic (e.g. fractions, linear equations)").strip()
else:
    homework_text = st.text_area("Paste homework question").strip()

# --- Safe default so Streamlit reruns never crash ---
resolved = pd.DataFrame()

if st.button("Generate Help / Explanation"):
    if mode != "Homework Help" and not topic:
        st.warning("Please enter a topic.")
    elif mode == "Homework Help" and not homework_text:
        st.warning("Please paste the homework question.")
    else:
        system_prompt = build_system_prompt(subject, grade, mode)

        user_prompt = (
            homework_text if mode == "Homework Help"
            else f"Topic: {topic}"
        )

        lesson = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        lesson_text = lesson.choices[0].message.content
        st.session_state.lesson_text = lesson_text
        st.markdown(lesson_text)

    if "lesson_text" in st.session_state:

        quiz_prompt = f"Create 5 multiple choice questions about {topic} with answers."
        quiz = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": quiz_prompt}]
        )

        quiz_text = quiz.choices[0].message.content

# ✅ ADD THIS LINE
        st.session_state.quiz_text = quiz_text

        st.write(quiz_text)

        answers = []
        for i in range(5):
            answers.append(st.selectbox(f"Answer Q{i+1}", ["A", "B", "C", "D"], key=f"a{i}"))

        if st.button("Submit Quiz"):

            lines = quiz_text.splitlines()
            correct = []

            for line in lines:
                if ":" in line and line.strip()[0].isdigit():
                    correct.append(line.split(":")[1].strip().upper())

            score = 0
            for i in range(min(len(correct), len(answers))):
                if answers[i] == correct[i]:
                    score += 1

            st.success(f"Your score: {score}/5")

            # Feedback comment
            if score == 5:
                comment = "🌟 Excellent — You’ve mastered this topic!"
            elif score == 4:
                comment = "👍 Very good — Just a small revision needed."
            elif score == 3:
                comment = "🙂 Good — Practice a bit more."
            elif score == 2:
                comment = "⚠ Needs improvement — Review the lesson again."
            else:
                comment = "❗ Let’s revisit the basics."

            st.info(comment)

            # Save to CSV
            record = {
                "student": student_name,
                "grade": grade,
                "topic": topic,
                "score": score,
                "comment": comment,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            try:
                df = pd.read_csv("progress.csv")
                df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            except:
                df = pd.DataFrame([record])

            df.to_csv("progress.csv", index=False)
            st.info("Progress saved successfully.")
    st.subheader("Need Live Help from a Tutor?")

    help_message = st.text_area(
    "Describe what you need help with (topic, question, confusion)"
)
# Ensure student_name exists before button
student_name = st.session_state.get("student_name", "").strip()

if not student_name:
    student_name = st.text_input("Student name", value="Student").strip()
    st.session_state.student_name = student_name
if st.button("Request Live Help"):
    help_request = {
    "student": student_name,
    "grade": grade,
    "subject": subject,
    "mode": mode,
    "topic": topic,
    "homework_text": homework_text,
    "message": help_message,
    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "status": "Open",
    "lesson_text": st.session_state.get("lesson_text",""),
    "quiz_text": st.session_state.get("quiz_text","")
}

    try:
        df = pd.read_csv("help_requests.csv")
        df = pd.concat([df, pd.DataFrame([help_request])], ignore_index=True)
    except:
        df = pd.DataFrame([help_request])

    df.to_csv("help_requests.csv", index=False)
    st.success("Your request has been sent to the tutor team.")
    # Show progress
    st.subheader("Your Progress")
    try:
        df = pd.read_csv("progress.csv")
        if student_name:
            st.dataframe(df[df["student"] == student_name])
        else:
            st.dataframe(df)
    except:
        st.write("No progress yet.")
        # -------------------------
# Tutor Dashboard
# -------------------------
elif page == "Tutor Dashboard":

    st.title("Tutor Application & Dashboard")

    st.subheader("Apply to Become a Tutor")

    tutor_name = st.text_input("Full Name")
    tutor_email = st.text_input("Email")
    tutor_subject = st.selectbox("Subject Expertise", ["Math", "Science", "English"])
    tutor_level = st.selectbox("Grade Level", ["Grade 6", "Grade 7", "Grade 8"])
    tutor_experience = st.text_area("Brief Teaching Experience")

    if st.button("Submit Application"):

        tutor_record = {
            "name": tutor_name,
            "email": tutor_email,
            "subject": tutor_subject,
            "grade": tutor_level,
            "experience": tutor_experience,
            "status": "Pending"
        }

        try:
            df = pd.read_csv("tutors.csv")
            df = pd.concat([df, pd.DataFrame([tutor_record])], ignore_index=True)
        except:
            df = pd.DataFrame([tutor_record])

        df.to_csv("tutors.csv", index=False)
        st.success("Application submitted successfully!")

    st.subheader("Approved Tutors")

    try:
        df = pd.read_csv("tutors.csv")
        approved = df[df["status"] == "Approved"]
        st.dataframe(approved)
    except:
        st.write("No tutors approved yet.")
        st.subheader("Live Help Requests from Students")
    try:
        requests_df = pd.read_csv("help_requests.csv")
        st.dataframe(requests_df)
        if len(requests_df) > 0:
            selected_index = st.selectbox(
                "Select a help request to view details",
                requests_df.index.tolist()
            )

            selected = requests_df.loc[selected_index]

            st.markdown("### Student Request Details")

            st.write(f"**Student:** {selected.get('student','')}")
            st.write(f"**Grade:** {selected.get('grade','')}")
            st.write(f"**Subject:** {selected.get('subject','')}")
            st.write(f"**Mode:** {selected.get('mode','')}")

        if selected.get("topic"):
            st.write(f"**Topic:** {selected.get('topic','')}")

            st.write(f"**Time:** {selected.get('time','')}")
            st.write(f"**Message:** {selected.get('message','')}")

            st.markdown("### Lesson Student Saw")
            st.markdown(selected.get("lesson_text", "No lesson context available"))

            st.markdown("### Quiz Student Saw")
            st.markdown(selected.get("quiz_text", "No quiz context available"))
            st.markdown("### Tutor Notes (How you helped)")

            tutor_notes = st.text_area(
            "Write how you explained the concept, steps, tips, or mistakes to avoid",
            value=selected.get("tutor_notes", "")
)
            if st.button("Mark as Resolved"):
             requests_df.loc[selected_index, "tutor_notes"] = tutor_notes
             requests_df.loc[selected_index, "status"] = "Resolved"
             requests_df.loc[selected_index, "resolved_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
             requests_df.to_csv("help_requests.csv", index=False)
            st.success("Help request resolved and tutor notes saved.")           
    except:
     st.write("No live help requests yet.")

# -------------------------
# Trust Page
# -------------------------
elif page == "Why Parents Trust Us":

    st.title("Why Parents Trust Smart Tutor AI")

    st.write("""
    ✅ Curriculum-aligned lessons  
    ✅ Child-safe AI responses  
    ✅ No ads or distractions  
    ✅ Transparent learning goals  
    ✅ Designed with educators  
    ✅ Privacy-first platform  
    """)
    # -------------------------
# Parent Dashboard
# -------------------------
elif page == "Parent Dashboard":

    st.title("Parent Dashboard")

    try:
        df = pd.read_csv("progress.csv")
        students = df["student"].unique().tolist()
        selected = st.selectbox("Select Student", students)

        st.subheader(f"Results for {selected}")
        st.dataframe(df[df["student"] == selected])

    except:
        st.write("No results available yet.")

    st.subheader("Meet Our Tutor Team")

    try:
        tutors_df = pd.read_csv("tutors.csv")
        approved_tutors = tutors_df[tutors_df["status"] == "Approved"]

        if len(approved_tutors) > 0:
            st.dataframe(
                approved_tutors[["name", "subject", "grade", "experience"]]
            )
        else:
            st.write("No tutors approved yet.")
    except:
        st.write("Tutor team information not available yet.")