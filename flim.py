# app.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import os
import re

# -----------------------------
# CSV FILES
# -----------------------------
MOVIES_FILE = "movies.csv"
USERS_FILE = "users.csv"

# -----------------------------
# Ensure files exist
# -----------------------------
if not os.path.exists(MOVIES_FILE):
    pd.DataFrame(columns=["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]).to_csv(MOVIES_FILE, index=False)

if not os.path.exists(USERS_FILE):
    # default admin user: admin/admin123
    pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}]).to_csv(USERS_FILE, index=False)

# -----------------------------
# CSV helpers
# -----------------------------
def load_users():
    return pd.read_csv(USERS_FILE)

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def load_movies():
    return pd.read_csv(MOVIES_FILE)

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

# -----------------------------
# Auth / User functions
# -----------------------------
def create_user(username, password):
    df = load_users()
    if username in df['username'].values:
        raise ValueError("Username already exists")
    hashed = generate_password_hash(password)
    df = pd.concat([df, pd.DataFrame([{"username": username, "password_hash": hashed}])])
    save_users(df)

def authenticate_user(username, password):
    df = load_users()
    user = df[df['username'] == username]
    if not user.empty and check_password_hash(user.iloc[0]['password_hash'], password):
        return True
    return False

# -----------------------------
# Movie functions
# -----------------------------
def add_movie(title, year, genre, director, rating, language, duration):
    df = load_movies()
    new_id = df['movie_id'].max() + 1 if not df.empty else 1
    df = pd.concat([df, pd.DataFrame([{
        "movie_id": new_id,
        "title": title,
        "release_year": year,
        "genre": genre,
        "director": director,
        "imdb_rating": rating,
        "language": language,
        "duration_minutes": duration
    }])])
    save_movies(df)

def update_movie(movie_id, title=None, genre=None, rating=None):
    df = load_movies()
    if movie_id not in df['movie_id'].values:
        raise ValueError("Movie not found")
    if title: df.loc[df['movie_id']==movie_id,'title'] = title
    if genre: df.loc[df['movie_id']==movie_id,'genre'] = genre
    if rating is not None: df.loc[df['movie_id']==movie_id,'imdb_rating'] = rating
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    df = df[df['movie_id'] != movie_id]
    save_movies(df)

# -----------------------------
# Alter table - add column
# -----------------------------
ALLOWED_TYPES = {
    "VARCHAR(100)": "object",
    "VARCHAR(255)": "object",
    "INT": "int64",
    "DECIMAL(3,1)": "float",
    "DATETIME": "object"
}

def add_column_to_movies(col_name: str, col_type: str, allow_nulls: bool = True):
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", col_name):
        raise ValueError("Invalid column name. Use letters, numbers and underscore only (no spaces).")
    if col_type not in ALLOWED_TYPES:
        raise ValueError("Invalid column type.")
    df = load_movies()
    dtype = ALLOWED_TYPES[col_type]
    df[col_name] = pd.Series([None]*len(df), dtype=dtype)
    save_movies(df)

# -----------------------------
# Recommendation helper
# -----------------------------
def get_recommendations(df, base_title, topn=5):
    if df.empty or not base_title.strip():
        return pd.DataFrame()
    df = df.copy()
    df['combined'] = df['genre'].fillna('') + " " + df['director'].fillna('')
    vec = TfidfVectorizer(stop_words='english')
    tfidf = vec.fit_transform(df['combined'])
    matches = df[df['title'].str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return pd.DataFrame()
    base_idx = matches.index[0]
    cos_sim = linear_kernel(tfidf, tfidf)
    sim_scores = list(enumerate(cos_sim[base_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1: topn+1]
    indices = [i[0] for i in sim_scores]
    return df.iloc[indices][['movie_id','title','genre','imdb_rating']]

# -----------------------------
# Logout helper
# -----------------------------
def safe_logout_message_and_refresh():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.success("Logged out successfully.")
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)
        st.stop()

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MovieApp (Admin + Users)", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

menu = st.sidebar.selectbox("Choose an action", ["Signup", "User Login", "Admin Login"])

# -----------------------------
# Signup
# -----------------------------
if menu == "Signup":
    st.header("📝 Create new user")
    new_user = st.text_input("Choose username", key="signup_user")
    new_pass = st.text_input("Choose password", type="password", key="signup_pass")
    if st.button("Signup"):
        if not new_user or not new_pass:
            st.error("Provide username and password.")
        else:
            try:
                create_user(new_user.strip(), new_pass.strip())
                st.success("User created. Now login from User Login.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# -----------------------------
# User Login
# -----------------------------
elif menu == "User Login":
    if not st.session_state.logged_in or st.session_state.role != "user":
        st.header("🔐 User Login")
        user = st.text_input("Username", key="user_login_user")
        pwd = st.text_input("Password", type="password", key="user_login_pass")
        if st.button("Login as User"):
            if authenticate_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = "user"
                st.success(f"Welcome {user} (user).")
            else:
                st.error("Invalid username or password.")
    if st.session_state.logged_in and st.session_state.role == "user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        if user_menu == "Home":
            st.dataframe(df, use_container_width=True)
        elif user_menu == "Filter Movies":
            genre = st.selectbox("Genre", ["All"] + sorted(df['genre'].dropna().unique()))
            language = st.selectbox("Language", ["All"] + sorted(df['language'].dropna().unique()))
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            filtered = df[((df['genre']==genre)|(genre=="All")) & ((df['language']==language)|(language=="All")) & (df['imdb_rating']>=rating)]
            st.dataframe(filtered,use_container_width=True)
        elif user_menu == "Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get recommendations"):
                recs = get_recommendations(df, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.dataframe(recs,use_container_width=True)
        elif user_menu == "Logout":
            safe_logout_message_and_refresh()

# -----------------------------
# Admin Login
# -----------------------------
elif menu == "Admin Login":
    if not st.session_state.logged_in or st.session_state.role != "admin":
        st.header("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            if authenticate_user(admin_user, admin_pass) and admin_user.lower()=="admin":
                st.session_state.logged_in = True
                st.session_state.username = admin_user
                st.session_state.role = "admin"
                st.success("Admin login successful.")
            else:
                st.error("Invalid admin credentials.")
    if st.session_state.logged_in and st.session_state.role=="admin":
        st.subheader("👑 Admin Dashboard")
        admin_menu = st.selectbox("Admin actions",[
            "Home","Add Movie","Update Movie","Delete Movie",
            "Alter Table - Add Column","Filter Movies","Recommendations","Logout"
        ])
        df = load_movies()
        # Home
        if admin_menu=="Home":
            st.dataframe(df,use_container_width=True)
        # Add Movie
        elif admin_menu=="Add Movie":
            with st.form("add_movie_form",clear_on_submit=True):
                t = st.text_input("Title")
                yr = st.number_input("Year",1800,2100,2020)
                g = st.text_input("Genre")
                d = st.text_input("Director")
                r = st.number_input("Rating",0.0,10.0,7.0,0.1)
                lang = st.text_input("Language")
                dur = st.number_input("Duration (min)",1,1000,120)
                if st.form_submit_button("Add Movie"):
                    add_movie(t.strip(), yr, g.strip(), d.strip(), r, lang.strip(), dur)
                    st.success("Movie added")
        # Update Movie
        elif admin_menu=="Update Movie":
            if not df.empty:
                sel = st.selectbox("Select movie", df.apply(lambda r:f"{r['movie_id']} - {r['title']}",axis=1))
                movie_id = int(sel.split(" - ")[0])
                row = df[df['movie_id']==movie_id].iloc[0]
                new_title = st.text_input("Title",value=row['title'])
                new_genre = st.text_input("Genre",value=row['genre'] or "")
                new_rating = st.number_input("Rating",value=float(row['imdb_rating'] or 0.0),step=0.1)
                if st.button("Update"):
                    update_movie(movie_id,new_title,new_genre,new_rating)
                    st.success("Movie updated")
        # Delete Movie
        elif admin_menu=="Delete Movie":
            if not df.empty:
                sel = st.selectbox("Select movie to delete", df.apply(lambda r:f"{r['movie_id']} - {r['title']}",axis=1))
                movie_id = int(sel.split(" - ")[0])
                if st.button("Delete Movie"):
                    delete_movie(movie_id)
                    st.success("Movie deleted")
        # Alter Table
        elif admin_menu=="Alter Table - Add Column":
            col_name = st.text_input("Column name")
            col_type = st.selectbox("Column type", list(ALLOWED_TYPES.keys()))
            allow_nulls = st.checkbox("Allow NULLs", value=True)
            if st.button("Add Column"):
                add_column_to_movies(col_name.strip(), col_type, allow_nulls)
                st.success(f"Column '{col_name}' added to movies.")
        # Filter Movies
        elif admin_menu=="Filter Movies":
            genre = st.selectbox("Genre", ["All"] + sorted(df['genre'].dropna().unique()))
            language = st.selectbox("Language", ["All"] + sorted(df['language'].dropna().unique()))
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            filtered = df[((df['genre']==genre)|(genre=="All")) & ((df['language']==language)|(language=="All")) & (df['imdb_rating']>=rating)]
            st.dataframe(filtered,use_container_width=True)
        # Recommendations
        elif admin_menu=="Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get"):
                recs = get_recommendations(df, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.dataframe(recs,use_container_width=True)
        # Logout
        elif admin_menu=="Logout":
            safe_logout_message_and_refresh()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files")
