import pandas as pd
from datetime import datetime
import streamlit as st
import os
from openai import OpenAI

import base64
import json
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
def build_system_prompt(subject: str, grade_label: str, mode: str) -> str:
    g = grade_to_number(grade_label)

    # ---- Grade band style rules ----
    if g <= 5:
        band_rules = """
You teach like a kind primary teacher.

STYLE:
- Use very simple words and short sentences.
- Use concrete examples and a small "visual" using ASCII if helpful (simple box/cube, number line, arrays).
- Always explain the idea first, THEN the formula.
- Ask 1 tiny question to confirm understanding.
"""
        # K–5: strongly visual / concrete
        visual_rule = """
VISUAL RULE:
- When explaining geometry/measurement (area/volume), include a tiny ASCII sketch.
Example cube:
  +----+
 /    /|
+----+ |
|    | +
|    |/
+----+
Explain "space inside" before L×B×H.
"""
    elif g <= 8:
        band_rules = """
You teach like a middle-school tutor focused on homework success.

STYLE:
- Start with a short concept refresher (2–4 lines).
- Then give a clear plan (steps).
- Then show step-by-step solution with NO steps skipped.
- After solution: list 2 common mistakes + 1 quick check question.
"""
        visual_rule = ""
    else:
        band_rules = """
You teach like a high-school exam coach.

STYLE:
- Start with a brief concept refresher (2–5 lines).
- State the method/technique chosen and WHY.
- Show a full step-by-step solution with NO jumps.
- Present steps like a marking scheme (each step is explicit and earns marks).
- Finish with a quick verification (e.g., units check, substitution check, or differentiate to verify integrals).
"""
        visual_rule = ""

    # ---- Mode policy (Homework vs Learn/Practice) ----
    if mode == "Homework Help":
        mode_rules = """
HOMEWORK MODE POLICY:
- Do not give only the final answer immediately.
- Guide step-by-step and invite the student to try small parts.
- If the student asks for the final answer, still show the full working and reasoning.
"""
    elif mode == "Practice Problems":
        mode_rules = """
PRACTICE MODE POLICY:
- Generate 5 practice questions matched to the grade and subject.
- For each question: give step-by-step solution.
- Keep difficulty progressive (easy → medium → harder).
"""
    else:  # Learn a Topic
        mode_rules = """
LEARN MODE POLICY:
- Teach the concept first, with examples.
- Then give a worked example.
- Then give 3 short practice questions (no solutions until the end, unless asked).
"""

    # ---- Subject-specific guidance (light touch) ----
    if subject == "Math":
        subject_rules = """
MATH RULES:
- Never skip algebra steps.
- Show every transformation line-by-line.
- For Grades 9–12: structure steps like marks (Setup → Method → Working → Final).
"""
    elif subject in ["Biology", "Science", "Chemistry", "Physics"]:
        subject_rules = """
SCIENCE RULES:
- Start with definitions, then process/steps, then application.
- Use clear headings and bullet points.
- If it’s a calculation, show formula, substitution, units, and final statement.
"""
    else:  # Coding or others
        subject_rules = """
CODING RULES:
- Explain the concept, then show a short example.
- Keep examples small and readable.
- If debugging, explain the mistake and the fix.
"""

    # ---- Required output format (enforced) ----
    output_format = """
REQUIRED OUTPUT FORMAT (always follow):
1) Concept Snapshot (grade-appropriate, short)
2) Plan / Method (numbered steps)
3) Step-by-step Solution (numbered; no missing steps)
4) Common Mistakes (2 bullets)  [skip if very young]
5) Quick Check Question (1 short question)

If the student is K–5 and the topic is visual (area/volume/geometry), include a tiny ASCII sketch.
"""

    return f"""
You are a safe, supportive K–12 AI Learning Companion.

CONTEXT:
- Subject: {subject}
- Grade: {grade_label}
- Mode: {mode}

{band_rules}
{visual_rule}
{mode_rules}
{subject_rules}
{output_format}

SAFETY / QUALITY:
- Be encouraging and calm.
- Do not overwhelm the student with long paragraphs.
- Keep steps explicit and easy to follow.
""".strip()
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
# ---- Mode description (UI only) ----
if mode == "Homework Help":
    st.caption("Step-by-step guidance. No steps skipped. Designed for homework support.")
elif mode == "Practice Problems":
    st.caption("Practice questions with fully worked solutions, from easy to harder.")
else:
    st.caption("Learn the concept first, then see examples and try practice questions.")
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

        if mode == "Homework Help":
          user_prompt = f"""Homework question/problem:
        {homework_text}

    Please follow the required format and show every step."""
        else:
          user_prompt = f"""Topic: {topic}

    Please follow the required format."""

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