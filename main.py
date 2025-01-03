import streamlit as st
import time
import pandas as pd
import plotly.express as px
import psycopg2
import json
from utils import get_questions
from dotenv import load_dotenv
import os

#load environment variables
load_dotenv()

# PostgreSQL connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv("HOST"),  # Adjust if needed
        database=os.getenv("DATABASE"),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        port = os.getenv("PORT_NO")
    )

# Helper to fetch scores from PostgreSQL
def get_scores():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM player_scores", conn)
    conn.close()
    return df

# Helper to update scores
def update_score(player, score):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE player_scores SET score = %s WHERE player_name = %s", (score, player))
    conn.commit()
    cur.close()
    conn.close()

# Helper to load player progress
def load_progress(player):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT current_question_index, answered_questions, questions_answered_count 
        FROM player_progress WHERE player_name = %s
    """, (player,))
    progress = cur.fetchone()
    conn.close()
    return progress if progress else (0, [], 0)

# Helper to save player progress
def save_progress(player, current_question, answered_questions, questions_answered_count):
    answered_questions = json.dumps(answered_questions)  
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO player_progress (player_name, current_question_index, answered_questions, questions_answered_count)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player_name) DO UPDATE
        SET current_question_index = EXCLUDED.current_question_index,
            answered_questions = EXCLUDED.answered_questions,
            questions_answered_count = EXCLUDED.questions_answered_count
    """, (player, current_question, answered_questions, questions_answered_count))
    conn.commit()
    cur.close()
    conn.close()

# Fetch questions
questions = get_questions()

# Player selection (lock after choosing)
if "selected_player" not in st.session_state:
    st.session_state.selected_player = None

if st.session_state.selected_player is None:
    selected_player = st.selectbox("Select your name:", ["Semilore", "Tomisin", "Joel", "Monica", "Lekan"])
    if st.button("Lock Player"):
        st.session_state.selected_player = selected_player

        # Load progress from database
        current_question, answered_questions, questions_answered_count = load_progress(selected_player)
        st.session_state.current_question = questions_answered_count  # Start from where they left off
        st.session_state.answered_questions = answered_questions

        st.rerun()
else:
    st.write(f"**Player:** {st.session_state.selected_player}")

# Initialize session state variables
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "show_next" not in st.session_state:
    st.session_state.show_next = False
if "question_answered" not in st.session_state:
    st.session_state.question_answered = False
if "current_question" not in st.session_state:
    st.session_state.current_question = 0

# Display current question
st.divider()
with st.container(height=250):
    current_q = questions[st.session_state.current_question]
    st.write(f"**Question {st.session_state.current_question + 1}:** {current_q['question']}")

    # Disable radio button if already answered
    selected_option = st.radio(
        "Choose an answer:",
        current_q["options"],
        disabled=st.session_state.question_answered
    )

# Submit button logic
if st.button("Submit Answer", disabled=st.session_state.question_answered):
    data = get_scores()
    current_score = data.loc[data["player_name"] == st.session_state.selected_player, "score"].values[0]

    if selected_option == current_q["answer"]:
        st.session_state.feedback = "Correct! 🎉 Majority agree with you"
        current_score += 1
    else:
        st.session_state.feedback = f"Wrong! 😢 Majority disagree with you'."
        
    if 'Correct' in st.session_state.feedback:
        st.success(st.session_state.feedback)
    else:
        st.error(st.session_state.feedback)
        

    # Update score in PostgreSQL
    update_score(st.session_state.selected_player, int(current_score))

    # Mark question as answered, increment count, and save progress
    st.session_state.question_answered = True
    st.session_state.answered_questions.append(st.session_state.current_question)
    new_count = st.session_state.current_question + 1
    save_progress(st.session_state.selected_player, st.session_state.current_question, st.session_state.answered_questions, new_count)

    with st.spinner("Loading next question..."):
        time.sleep(2)

    st.session_state.show_next = True
    st.rerun()

# Next question button
if st.session_state.show_next and st.button("Next Question"):
    if st.session_state.current_question < len(questions) - 1:
        st.session_state.current_question += 1
        st.session_state.feedback = ""
        st.session_state.show_next = False
        st.session_state.question_answered = False  # Reset for the new question
        st.rerun()
    else:
        st.write("Quiz complete!")

# Real-time leaderboard
st.divider()
scores_data = get_scores()
fig = px.bar(
    scores_data,
    x="player_name",
    y="score",
    color="player_name",
    text="score",
    title="Real-Time LeaderBoard"
)
fig.update_layout(yaxis_title="Score", xaxis_title="Player", showlegend=False)
fig.update_traces(textposition='outside')
st.plotly_chart(fig, use_container_width=True)