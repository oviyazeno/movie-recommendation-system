import streamlit as st
import pandas as pd
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# ===========================================
# DATABASE CONNECTION
# ===========================================
def get_connection():
    server = 'localhost'  # Change if needed
    database = 'MovieDb'
    driver = '{ODBC Driver 17 for SQL Server}'
    return pyodbc.connect(f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;")

# ===========================================
# FETCH MOVIES
# ===========================================
def fetch_movies():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM movies", conn)
    conn.close()
    return df

# ===========================================
# USER AUTH FUNCTIONS (WITHOUT ROLE)
# ===========================================
def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    hashed = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hashed)
    )
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        return True
    return False

# ===========================================
# STREAMLIT CONFIG
# ===========================================
st.set_page_config(page_title="Movie Recommendation System", layout="wide")
st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")

# ===========================================
# SESSION STATE
# ===========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# ===========================================
# LOGIN / SIGNUP
# ===========================================
menu = ["Login", "Signup"]
if not st.session_state.logged_in:
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Signup":
        st.header("📝 Create New User Account")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        if st.button("Signup"):
            create_user(new_user, new_pass)
            st.success(f"User account '{new_user}' created successfully!")

    elif choice == "Login":
        st.header("🔐 User Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.success(f"Welcome {user}! Login Successful")
            else:
                st.error("Invalid username or password")

# ===========================================
# AFTER LOGIN - USER PAGES
# ===========================================
if st.session_state.logged_in:
    st.sidebar.title(f"Welcome, {st.session_state.username}")
    user_menu = ["Home", "Filter Movies", "Recommendations", "Logout"]
    choice = st.sidebar.selectbox("User Menu", user_menu)

    # -----------------------------
    # LOGOUT
    # -----------------------------
    if choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.success("Logged out successfully!")
        st.stop()  # Stops current run and refreshes page

    # -----------------------------
    # HOME → SHOW ALL MOVIES
    # -----------------------------
    elif choice == "Home":
        st.header("📌 All Movies")
        df = fetch_movies()
        st.dataframe(df, use_container_width=True)

    # -----------------------------
    # FILTER MOVIES
    # -----------------------------
    elif choice == "Filter Movies":
        st.header("🔍 Filter Movies")
        df = fetch_movies()
        genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
        language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
        rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)

        filtered_df = df[
            ((df["genre"] == genre) | (genre == "All")) &
            ((df["language"] == language) | (language == "All")) &
            (df["imdb_rating"] >= rating)
        ]
        st.dataframe(filtered_df, use_container_width=True)

    # -----------------------------
    # RECOMMENDATION ENGINE
    # -----------------------------
    elif choice == "Recommendations":
        st.header("🤖 Movie Recommendations")
        df = fetch_movies()
        df['combined'] = df['genre'] + " " + df['director']

        vec = TfidfVectorizer(stop_words='english')
        tfidf = vec.fit_transform(df['combined'])
        cos_sim = linear_kernel(tfidf, tfidf)

        movie_list = df['title'].tolist()
        movie = st.selectbox("Select a Movie", movie_list)
        idx = df[df['title'] == movie].index[0]
        sim_scores = list(enumerate(cos_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
        movie_indices = [i[0] for i in sim_scores]

        st.success("Recommended Movies")
        st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
