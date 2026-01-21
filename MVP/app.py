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

    st.title("Smart Tutor AI - Math MVP")

    student_name = st.text_input("Enter your name")
    st.write("Select your grade and topic to begin.")

    grade = st.selectbox("Select Grade", ["Grade 6", "Grade 7", "Grade 8"])

    topics = {
        "Grade 6": ["Fractions", "Decimals", "Ratios", "Percentages"],
        "Grade 7": ["Integers", "Linear Equations", "Geometry", "Proportions"],
        "Grade 8": ["Linear Functions", "Pythagorean Theorem", "Graphs", "Systems of Equations"]
    }

    topic = st.selectbox("Select Topic", topics[grade])


# --- Safe default so Streamlit reruns never crash ---
resolved = pd.DataFrame()

if st.button("Generate Lesson"):

    # --- pull tutor notes from past resolved help requests ---
    tutor_insights = ""
    resolved = pd.DataFrame()

    try:
        req_df = pd.read_csv("help_requests.csv")  # ✅ make sure this filename matches your app
        if "tutor_notes" in req_df.columns:
            resolved = req_df[
                (req_df["topic"] == topic) &
                (req_df["status"] == "Resolved") &
                (req_df["tutor_notes"].notna())
            ]

            if not resolved.empty:
                tutor_insights = "\n".join(resolved["tutor_notes"].tail(3).tolist())
    except:
        pass

    # --- show Tutor Tip to student (ONLY ONCE) ---
    if not resolved.empty:
        tutor_tip = str(resolved["tutor_notes"].tail(1).values[0]).strip()
        if tutor_tip:
            st.info(f"💡 Tutor Tip: {tutor_tip}")

    # --- build lesson prompt (feeds tutor insights back into AI) ---
    lesson_prompt = f"""
Teach {topic} to a {grade} student.

Requirements:
- Explain clearly step-by-step
- Give 1 worked example
- Give 3 short practice questions
- Then create a short quiz (5 MCQs)

Tutor insights from previous help sessions (use these to improve your explanation):
{tutor_insights}
"""

    lesson = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": lesson_prompt}]
    )

    lesson_text = lesson.choices[0].message.content
    st.session_state.lesson_text = lesson_text
    st.markdown(lesson_text)

    # Optional: if your app treats "quiz_text" as same content, store it too
    st.session_state.quiz_text = lesson_text

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
    "topic": topic,
    "message": help_message,
    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "status": "Open",

    # 👇 add these
    "lesson_text": st.session_state.get("lesson_text", ""),
    "quiz_text": st.session_state.get("quiz_text", "")
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
            st.write(f"**Student:** {selected['student']}")
            st.write(f"**Topic:** {selected['topic']}")
            st.write(f"**Time:** {selected['time']}")
            st.write(f"**Message:** {selected['message']}")

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