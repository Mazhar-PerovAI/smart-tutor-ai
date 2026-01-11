import streamlit as st
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Smart Tutor AI - Math MVP")

st.write("Select your grade and topic to generate a lesson.")

grade = st.selectbox("Select Grade", ["Grade 6", "Grade 7", "Grade 8"])

topics = {
    "Grade 6": ["Fractions", "Decimals", "Ratios", "Percentages"],
    "Grade 7": ["Integers", "Linear Equations", "Geometry", "Proportions"],
    "Grade 8": ["Linear Functions", "Pythagorean Theorem", "Graphs", "Systems of Equations"]
}

topic = st.selectbox("Select Topic", topics[grade])

if st.button("Generate Lesson"):
    prompt = f"""
    Teach the topic '{topic}' for {grade} students using this exact format:

    ### Concept Explanation
    Short 6-line explanation.

    ### Step-by-Step Example 1
    Problem + full solution.

    ### Step-by-Step Example 2
    Problem + full solution.

    ### Practice Problems
    5 questions, no solutions.

    ### 5-Question Quiz
    MCQs with A/B/C/D.

    ### Quiz Answers
    Provide answers.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    st.markdown(response.choices[0].message.content)