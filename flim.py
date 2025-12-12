# app.py
import streamlit as st
import pandas as pd
import hashlib

CSV_FILE = "users_movies.csv"  # your updated CSV with users + movies

# -----------------------------
# Helper functions
# -----------------------------
def verify_scrypt(stored_hash, password):
    """Verify password against scrypt hash in your CSV"""
    try:
        parts = stored_hash.split('$')
        if len(parts) != 3:
            return False
        params, salt, hashed = parts
        N, r, p, dklen = map(int, params.replace('scrypt:', '').split(':'))
        new_hash = hashlib.scrypt(password.encode(), salt=salt.encode(), n=N, r=r, p=p, dklen=64).hex()
        return new_hash == hashed
    except:
        return False

def load_users_and_movies():
    df = pd.read_csv(CSV_FILE, sep="\t", header=None)
    # Users: rows where password starts with scrypt
    users = df[df[2].str.startswith("scrypt", na=False)][[1,2]].set_index(1).to_dict()['2']
    # Movies: rows where password is not scrypt (or title column is movie title)
    movies = df[~df[2].str.startswith("scrypt", na=False)][[1,2,3,4,5,6,7,8]]
    movies.columns = ['title','year','genre','director','rating','language','duration','added_on']
    return users, movies

def save_movies(df):
    # Save back to CSV, but preserve user rows
    df_users = pd.read_csv(CSV_FILE, sep="\t", header=None)
    user_rows = df_users[df_users[2].str.startswith("scrypt", na=False)]
    # convert movies df to same format
    movie_rows = df.copy()
    movie_rows = movie_rows.reset_index(drop=True)
    movie_rows.insert(0, 'movie_id', range(1,len(movie_rows)+1))
    movie_rows = movie_rows[['movie_id','title','year','genre','director','rating','language','duration','added_on']]
    # Combine and save
    combined = pd.concat([user_rows, movie_rows], ignore_index=True)
    combined.to_csv(CSV_FILE, sep="\t", index=False, header=False)

# -----------------------------
# Movie functions
# -----------------------------
def add_movie(title, year, genre, director, rating, language, duration):
    df = movies.copy()
    new_movie = pd.DataFrame([{
        'title': title, 'year': year, 'genre': genre, 'director': director,
        'rating': rating, 'language': language, 'duration': duration, 'added_on': pd.Timestamp.now()
    }])
    df = pd.concat([df, new_movie], ignore_index=True)
    save_movies(df)
    return df

def update_movie(idx, title=None, genre=None, rating=None):
    df = movies.copy()
    if title: df.at[idx,'title'] = title
    if genre: df.at[idx,'genre'] = genre
    if rating: df.at[idx,'rating'] = rating
    save_movies(df)
    return df

def delete_movie(idx):
    df = movies.copy()
    df = df.drop(idx).reset_index(drop=True)
    save_movies(df)
    return df

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MovieDb", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

users, movies = load_users_and_movies()

menu = st.sidebar.selectbox("Choose action", ["User Login","Admin Login"])

# -----------------------------
# User Login
# -----------------------------
if menu=="User Login":
    if not st.session_state.logged_in or st.session_state.role!="user":
        st.subheader("🔐 User Login")
        username = st.text_input("Username", key="user_login")
        password = st.text_input("Password", type="password", key="user_pass")
        if st.button("Login as User"):
            if username in users and verify_scrypt(users[username], password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = "user"
                st.success(f"Welcome {username} (User)")
            else:
                st.error("Invalid username or password")
    if st.session_state.logged_in and st.session_state.role=="user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Logout"])
        if user_menu=="Home":
            st.dataframe(movies,use_container_width=True)
        elif user_menu=="Filter Movies":
            genre = st.selectbox("Genre", ["All"] + sorted(movies['genre'].dropna().unique()))
            language = st.selectbox("Language", ["All"] + sorted(movies['language'].dropna().unique()))
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            filtered = movies[((movies['genre']==genre)|(genre=="All")) & ((movies['language']==language)|(language=="All")) & (movies['rating']>=rating)]
            st.dataframe(filtered,use_container_width=True)
        elif user_menu=="Logout":
            st.session_state.logged_in=False
            st.session_state.username=None
            st.session_state.role=None
            st.success("Logged out successfully.")
            st.experimental_rerun()

# -----------------------------
# Admin Login
# -----------------------------
elif menu=="Admin Login":
    if not st.session_state.logged_in or st.session_state.role!="admin":
        st.subheader("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_login")
        admin_pass = st.text_input("Password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            if admin_user.lower()=="admin" and admin_user in users and verify_scrypt(users[admin_user], admin_pass):
                st.session_state.logged_in=True
                st.session_state.username=admin_user
                st.session_state.role="admin"
                st.success("Admin login successful")
            else:
                st.error("Invalid admin credentials")
    if st.session_state.logged_in and st.session_state.role=="admin":
        st.subheader("👑 Admin Dashboard")
        admin_menu = st.selectbox("Choose action", ["Home","Add Movie","Update Movie","Delete Movie","Filter Movies","Logout"])
        if admin_menu=="Home":
            st.dataframe(movies,use_container_width=True)
        elif admin_menu=="Add Movie":
            with st.form("add_movie_form", clear_on_submit=True):
                t = st.text_input("Title")
                yr = st.number_input("Year",1800,2100,2020)
                g = st.text_input("Genre")
                d = st.text_input("Director")
                r = st.number_input("Rating",0.0,10.0,7.0,0.1)
                lang = st.text_input("Language")
                dur = st.number_input("Duration",1,500,120)
                if st.form_submit_button("Add"):
                    movies = add_movie(t,yr,g,d,r,lang,dur)
                    st.success("Movie added")
        elif admin_menu=="Update Movie":
            if not movies.empty:
                sel = st.selectbox("Select movie", movies['title'])
                idx = movies[movies['title']==sel].index[0]
                new_title = st.text_input("Title", value=movies.at[idx,'title'])
                new_genre = st.text_input("Genre", value=movies.at[idx,'genre'])
                new_rating = st.number_input("Rating", value=float(movies.at[idx,'rating']), step=0.1)
                if st.button("Update"):
                    movies = update_movie(idx, new_title, new_genre, new_rating)
                    st.success("Movie updated")
        elif admin_menu=="Delete Movie":
            if not movies.empty:
                sel = st.selectbox("Select movie to delete", movies['title'])
                idx = movies[movies['title']==sel].index[0]
                if st.button("Delete"):
                    movies = delete_movie(idx)
                    st.success("Movie deleted")
        elif admin_menu=="Filter Movies":
            genre = st.selectbox("Genre", ["All"] + sorted(movies['genre'].dropna().unique()))
            language = st.selectbox("Language", ["All"] + sorted(movies['language'].dropna().unique()))
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            filtered = movies[((movies['genre']==genre)|(genre=="All")) & ((movies['language']==language)|(language=="All")) & (movies['rating']>=rating)]
            st.dataframe(filtered,use_container_width=True)
        elif admin_menu=="Logout":
            st.session_state.logged_in=False
            st.session_state.username=None
            st.session_state.role=None
            st.success("Logged out successfully.")
            st.experimental_rerun()
