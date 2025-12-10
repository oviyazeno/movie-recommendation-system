# app.py
"""
Full Streamlit movie app:
- Admin login
- User signup/login
- Add / Update / Delete Movies
- Content-based Recommendation (TF-IDF + Cosine)
- Uses SQL Server via pyodbc (editable to other DBs)
"""

import streamlit as st
import pandas as pd
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import numpy as np
from datetime import datetime

# ---------------------------
# CONFIG: Change these values
# ---------------------------
DB_DRIVER = "{ODBC Driver 17 for SQL Server}"
DB_SERVER = "localhost"  # e.g. localhost or server\instance
DB_NAME = "MovieDb"
DB_TRUSTED = True  # If False, set DB_USER and DB_PASSWORD
DB_USER = ""
DB_PASSWORD = ""

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin@123"  # will be hashed and created on first run
# ---------------------------

st.set_page_config(page_title="MovieApp", layout="wide")

# --------------------------------
# Database connection & utilities
# --------------------------------
def get_connection():
    if DB_TRUSTED:
        conn_str = f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};"
    return pyodbc.connect(conn_str, autocommit=True)

def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    # users table for user accounts
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(100) UNIQUE,
        password_hash NVARCHAR(300),
        is_admin BIT DEFAULT 0,
        created_at DATETIME DEFAULT GETDATE()
    );
    """)
    # movies table
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='movies' AND xtype='U')
    CREATE TABLE movies (
        id INT IDENTITY(1,1) PRIMARY KEY,
        title NVARCHAR(300),
        year INT,
        genre NVARCHAR(200),
        director NVARCHAR(200),
        rating FLOAT,
        language NVARCHAR(100),
        duration INT,
        created_at DATETIME DEFAULT GETDATE()
    );
    """)
    conn.close()

def ensure_default_admin():
    """Create default admin if not exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(1) FROM users WHERE username = ?", DEFAULT_ADMIN_USERNAME)
    exists = cursor.fetchone()[0] > 0
    if not exists:
        pw_hash = generate_password_hash(DEFAULT_ADMIN_PASSWORD)
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                       (DEFAULT_ADMIN_USERNAME, pw_hash))
    conn.close()

# ---------------------------
# User & Auth functions
# ---------------------------
def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    # check exists
    cursor.execute("SELECT COUNT(1) FROM users WHERE username = ?", username)
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False, "Username already taken."
    pw_hash = generate_password_hash(password)
    cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)", (username, pw_hash))
    conn.close()
    return True, "User registered."

def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, is_admin FROM users WHERE username = ?", username)
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False, "User not found", None
    uid, pw_hash, is_admin = row[0], row[1], row[2]
    if check_password_hash(pw_hash, password):
        return True, "Authenticated", {"id": uid, "username": username, "is_admin": bool(is_admin)}
    else:
        return False, "Wrong password", None

# ---------------------------
# Movie CRUD
# ---------------------------
def add_movie_db(movie):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO movies (title, year, genre, director, rating, language, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (movie['title'], movie['year'], movie['genre'], movie['director'],
          movie['rating'], movie['language'], movie['duration']))
    conn.close()

def update_movie_db(movie_id, movie):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE movies SET title=?, year=?, genre=?, director=?, rating=?, language=?, duration=?
    WHERE id=?
    """, (movie['title'], movie['year'], movie['genre'], movie['director'],
          movie['rating'], movie['language'], movie['duration'], movie_id))
    conn.close()

def delete_movie_db(movie_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.close()

def fetch_all_movies_df():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM movies ORDER BY id DESC", conn)
    conn.close()
    return df

def fetch_movie_by_id(movie_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, year, genre, director, rating, language, duration FROM movies WHERE id = ?", (movie_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(zip(["id","title","year","genre","director","rating","language","duration"], row))
    return None

# ---------------------------
# Recommendation engine
# ---------------------------
def build_recommendation_model(movies_df):
    # Create a 'soup' combining title, genre, director
    if movies_df.empty:
        return None
    df = movies_df.copy()
    df['soup'] = (df['title'].fillna('') + ' ' + df['genre'].fillna('') + ' ' + df['director'].fillna('')).str.lower()
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df['soup'])
    # compute cosine similarities
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    indices = pd.Series(df.index, index=df['id']).drop_duplicates()
    return {
        "df": df,
        "cosine_sim": cosine_sim,
        "indices": indices
    }

def recommend_movies(movie_id, model, top_n=5):
    if not model:
        return []
    df = model["df"]
    cosine_sim = model["cosine_sim"]
    indices = model["indices"]
    if movie_id not in indices.index:
        return []
    idx = indices[movie_id]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1: top_n+1]  # exclude itself
    movie_indices = [i[0] for i in sim_scores]
    return df.iloc[movie_indices].to_dict(orient='records')

# ---------------------------
# Session State helpers
# ---------------------------
def init_session():
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    if 'page' not in st.session_state:
        st.session_state['page'] = "Home"

init_session()

# ---------------------------
# UI: Pages
# ---------------------------
def home_page():
    st.title("🎬 MovieApp - Home")
    st.write("Welcome! Use the sidebar to navigate the app.")
    df = fetch_all_movies_df()
    if df.empty:
        st.info("No movies in DB. Admin can add movies.")
        return
    st.subheader("Latest movies")
    st.dataframe(df[['id','title','year','genre','director','rating','language','duration']])

def signup_page():
    st.title("Create an account")
    uname = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    pw2 = st.text_input("Confirm Password", type="password")
    if st.button("Sign up"):
        if not uname or not pw:
            st.warning("Enter username and password.")
        elif pw != pw2:
            st.warning("Passwords must match.")
        else:
            ok, msg = register_user(uname, pw)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

def login_page():
    st.title("Login")
    uname = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        ok, msg, user = authenticate_user(uname, pw)
        if ok:
            st.session_state['user'] = user
            st.success(f"Logged in as {user['username']}")
        else:
            st.error(msg)

def logout():
    st.session_state['user'] = None
    st.success("Logged out.")

def admin_dashboard():
    st.title("Admin Dashboard")
    st.write("Manage movies and users.")
    df = fetch_all_movies_df()
    st.subheader("All movies")
    st.dataframe(df[['id','title','year','genre','director','rating','language','duration']])

def add_movie_page():
    st.title("Add Movie")
    with st.form("add_movie_form"):
        title = st.text_input("Title")
        year = st.number_input("Year", min_value=1900, max_value=2100, value=2023)
        genre = st.text_input("Genre (comma separated)")
        director = st.text_input("Director")
        rating = st.number_input("Rating (0-10)", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
        language = st.text_input("Language")
        duration = st.number_input("Duration (mins)", min_value=1, max_value=1000, value=120)
        submitted = st.form_submit_button("Add Movie")
    if submitted:
        if not title:
            st.warning("Title is required.")
        else:
            movie = {
                "title": title,
                "year": int(year),
                "genre": genre,
                "director": director,
                "rating": float(rating),
                "language": language,
                "duration": int(duration)
            }
            try:
                add_movie_db(movie)
                st.success("Movie added.")
            except Exception as e:
                st.error(f"DB Error: {e}")

def update_delete_page():
    st.title("Update / Delete Movie")
    df = fetch_all_movies_df()
    if df.empty:
        st.info("No movies found.")
        return
    st.subheader("Select movie to edit")
    sel = st.selectbox("Choose movie id", options=df['id'].tolist(), format_func=lambda x: f"{x} - {df[df['id']==x]['title'].values[0]}")
    movie = fetch_movie_by_id(sel)
    if not movie:
        st.error("Movie not found.")
        return
    with st.form("edit_movie"):
        title = st.text_input("Title", value=movie['title'])
        year = st.number_input("Year", min_value=1900, max_value=2100, value=int(movie['year'] or 2023))
        genre = st.text_input("Genre", value=movie['genre'])
        director = st.text_input("Director", value=movie['director'])
        rating = st.number_input("Rating (0-10)", min_value=0.0, max_value=10.0, value=float(movie['rating'] or 7.0), step=0.1)
        language = st.text_input("Language", value=movie['language'])
        duration = st.number_input("Duration (mins)", min_value=1, max_value=1000, value=int(movie['duration'] or 120))
        update_btn = st.form_submit_button("Update")
        delete_btn = st.form_submit_button("Delete")
    if update_btn:
        updated = {
            "title": title,
            "year": int(year),
            "genre": genre,
            "director": director,
            "rating": float(rating),
            "language": language,
            "duration": int(duration)
        }
        try:
            update_movie_db(sel, updated)
            st.success("Movie updated.")
        except Exception as e:
            st.error(f"DB Error: {e}")
    if delete_btn:
        try:
            delete_movie_db(sel)
            st.success("Movie deleted.")
        except Exception as e:
            st.error(f"DB Error: {e}")

def recommendation_page():
    st.title("Recommendations")
    df = fetch_all_movies_df()
    if df.empty:
        st.info("No movies to recommend from.")
        return
    st.subheader("Pick a movie to get recommendations")
    sel = st.selectbox("Choose movie", options=df['id'].tolist(), format_func=lambda x: f"{x} - {df[df['id']==x]['title'].values[0]}")
    model = build_recommendation_model(df)
    if st.button("Recommend"):
        recs = recommend_movies(sel, model, top_n=6)
        if not recs:
            st.info("No recommendations found.")
            return
        st.markdown("### Recommended movies")
        for r in recs:
            st.write(f"**{r['title']}** ({r['year']}) — Genre: {r['genre']} — Director: {r['director']} — Rating: {r['rating']}")

# ---------------------------
# Main
# ---------------------------
def main():
    # initialize DB & admin (safe-guard)
    try:
        init_db()
        ensure_default_admin()
    except Exception as e:
        st.error("Database initialization error. Check DB connection/config at top of app.py.")
        st.exception(e)
        return

    # Sidebar - navigation
    st.sidebar.title("Navigation")
    user = st.session_state.get('user')
    if user:
        st.sidebar.write(f"Logged in as **{user['username']}**")
        if st.sidebar.button("Logout"):
            logout()
            st.experimental_rerun()
    else:
        if st.sidebar.button("Login / Signup"):
            st.session_state['page'] = "Login"

    menu = ["Home"]
    # public pages
    menu += ["Signup", "Login", "Recommendation"]
    # admin pages shown only to admin
    if user and user.get('is_admin'):
        menu += ["Admin Dashboard", "Add Movie", "Update/Delete Movie"]

    choice = st.sidebar.selectbox("Go to", menu, index=menu.index(st.session_state.get('page')) if st.session_state.get('page') in menu else 0)
    st.session_state['page'] = choice

    # Route to selected page
    if choice == "Home":
        home_page()
    elif choice == "Signup":
        signup_page()
    elif choice == "Login":
        login_page()
    elif choice == "Recommendation":
        recommendation_page()
    elif choice == "Admin Dashboard":
        if not user or not user.get('is_admin'):
            st.error("Admin only.")
        else:
            admin_dashboard()
    elif choice == "Add Movie":
        if not user or not user.get('is_admin'):
            st.error("Admin only.")
        else:
            add_movie_page()
    elif choice == "Update/Delete Movie":
        if not user or not user.get('is_admin'):
            st.error("Admin only.")
        else:
            update_delete_page()
    else:
        st.info("Select a page from the sidebar.")

    st.sidebar.markdown("---")
    st.sidebar.write("App last started at: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.sidebar.markdown("**DB:** " + DB_NAME)

if __name__ == "__main__":
    main()
