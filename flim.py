import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import os

# FILE NAMES
MOVIES_FILE = "movies.csv"
USERS_FILE = "users.csv"

# ---------------------
# Ensure files exist
# ---------------------
if not os.path.exists(USERS_FILE):
    pd.DataFrame([{"username": "admin", "password_hash": "admin123"}]).to_csv(USERS_FILE, index=False)

if not os.path.exists(MOVIES_FILE):
    pd.DataFrame(columns=[
        "movie_id","title","release_year","genre","director",
        "imdb_rating","language","duration_minutes","created_at"
    ]).to_csv(MOVIES_FILE, index=False)

# ---------------------
# USER FUNCTIONS
# ---------------------
def load_users():
    return pd.read_csv(USERS_FILE)

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def create_user(username, password):
    df = load_users()

    if username in df['username'].values:
        raise ValueError("Username already exists")

    # allow both hashed and plain
    hashed = generate_password_hash(password)

    df = pd.concat([df, pd.DataFrame([{
        "username": username,
        "password_hash": hashed
    }])])

    save_users(df)

def authenticate_user(username, password):
    df = load_users()

    if username not in df['username'].values:
        return False

    row = df[df['username'] == username].iloc[0]
    stored = row['password_hash']

    # allow plain text OR hashed
    try:
        return check_password_hash(stored, password)
    except:
        return stored == password

# ---------------------
# MOVIE FUNCTIONS
# ---------------------
def load_movies():
    return pd.read_csv(MOVIES_FILE)

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

def add_movie(row_dict):
    df = load_movies()
    new_id = df['movie_id'].max() + 1 if not df.empty else 1
    row_dict["movie_id"] = new_id
    df = pd.concat([df, pd.DataFrame([row_dict])])
    save_movies(df)

def update_movie(movie_id, new_data):
    df = load_movies()
    for k, v in new_data.items():
        df.loc[df["movie_id"] == movie_id, k] = v
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    df = df[df["movie_id"] != movie_id]
    save_movies(df)

# ---------------------
# LOGOUT
# ---------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.experimental_rerun()

# ---------------------
# STREAMLIT UI
# ---------------------
st.set_page_config(page_title="MovieDb", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

 menu = st.sidebar.selectbox("Choose", ["Signup", "User Login", "Admin Login"])

# -----------------------
# SIGNUP
# -----------------------
if menu == "Signup":
    st.header("Create User")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Signup"):
        if not u or not p:
            st.error("Enter both fields")
        else:
            try:
                create_user(u, p)
                st.success("User created. Login now.")
            except Exception as e:
                st.error(str(e))

# -----------------------
# USER LOGIN
# -----------------------
elif menu == "User Login":
    if not st.session_state.logged_in:
        st.header("User Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate_user(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = "user"
                st.success("Login successful")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    if st.session_state.logged_in and st.session_state.role == "user":
        st.header("👤 User Dashboard")

        df = load_movies()
        st.dataframe(df)

        if st.button("Logout"):
            logout()

# -----------------------
# ADMIN LOGIN
# -----------------------
elif menu == "Admin Login":
    if not st.session_state.logged_in:
        st.header("Admin Login")
        u = st.text_input("Admin username")
        p = st.text_input("Admin password", type="password")

        if st.button("Login as Admin"):
            if u.lower() == "admin" and authenticate_user(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = "admin"
                st.success("Admin Logged In")
                st.experimental_rerun()
            else:
                st.error("Invalid admin credentials")

    if st.session_state.logged_in and st.session_state.role == "admin":
        st.header("👑 Admin Dashboard")
        df = load_movies()

        option = st.selectbox("Choose action", [
            "Home", "Add Movie", "Update Movie", "Delete Movie", "Logout"
        ])

        if option == "Home":
            st.dataframe(df)

        elif option == "Add Movie":
            t = st.text_input("Title")
            y = st.number_input("Year", 1800, 2100, 2020)
            g = st.text_input("Genre")
            d = st.text_input("Director")
            r = st.number_input("Rating", 0.0, 10.0, 7.0)
            l = st.text_input("Language")
            dur = st.number_input("Duration Minutes", 1, 500)
            ca = st.text_input("Created At")

            if st.button("Add Movie"):
                add_movie({
                    "title": t,
                    "release_year": y,
                    "genre": g,
                    "director": d,
                    "imdb_rating": r,
                    "language": l,
                    "duration_minutes": dur,
                    "created_at": ca
                })
                st.success("Movie added")

        elif option == "Update Movie":
            if df.empty:
                st.warning("No movies")
            else:
                sel = st.selectbox("Select", df["movie_id"])
                movie_id = int(sel)
                row = df[df["movie_id"] == movie_id].iloc[0]

                new_title = st.text_input("Title", row["title"])
                new_genre = st.text_input("Genre", row["genre"])
                new_rating = st.number_input("Rating", 0.0, 10.0, float(row["imdb_rating"]))

                if st.button("Update"):
                    update_movie(movie_id, {
                        "title": new_title,
                        "genre": new_genre,
                        "imdb_rating": new_rating
                    })
                    st.success("Updated")

        elif option == "Delete Movie":
            if df.empty:
                st.warning("No movies")
            else:
                sel = st.selectbox("Delete", df["movie_id"])
                if st.button("Delete Movie"):
                    delete_movie(int(sel))
                    st.success("Movie deleted")

        elif option == "Logout":
            logout()
