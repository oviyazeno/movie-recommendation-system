# app.py
import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import os
import hashlib

CSV_FILE = "users_movies.csv"  # your combined CSV

# -----------------------------
# Ensure file exists
# -----------------------------
if not os.path.exists(CSV_FILE):
    # Create file with headers if missing
    pd.DataFrame(columns=["id","username_or_title","password_or_year","genre","director","rating","language","duration","added_on"]).to_csv(CSV_FILE, index=False, sep="\t")

# -----------------------------
# Helper functions
# -----------------------------
def verify_scrypt(stored_hash, password):
    """Verify scrypt password hash"""
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
    df = pd.read_csv(CSV_FILE, sep="\t", dtype=str)
    # Users: password starts with scrypt
    users = df[df['password_or_year'].str.startswith("scrypt", na=False)][['username_or_title','password_or_year']].set_index('username_or_title').to_dict()['password_or_year']
    # Movies: password column not scrypt
    movies = df[~df['password_or_year'].str.startswith("scrypt", na=False)][['username_or_title','password_or_year','genre','director','rating','language','duration','added_on']]
    movies.columns = ['title','year','genre','director','rating','language','duration','added_on']
    # Convert numeric columns
    movies['rating'] = movies['rating'].astype(float)
    movies['year'] = movies['year'].astype(int)
    movies['duration'] = movies['duration'].astype(int)
    return users, movies

def save_movies(movies_df):
    df = pd.read_csv(CSV_FILE, sep="\t", dtype=str)
    users_df = df[df['password_or_year'].str.startswith("scrypt", na=False)]
    movies_df_copy = movies_df.copy()
    movies_df_copy = movies_df_copy.reset_index(drop=True)
    movies_df_copy.insert(0,'id', range(1,len(movies_df_copy)+1))
    movies_df_copy = movies_df_copy[['id','title','year','genre','director','rating','language','duration','added_on']]
    combined = pd.concat([users_df, movies_df_copy], ignore_index=True)
    combined.to_csv(CSV_FILE, sep="\t", index=False, header=False)

# -----------------------------
# Movie functions
# -----------------------------
def add_movie(title, year, genre, director, rating, language, duration):
    users, movies = load_users_and_movies()
    new_movie = pd.DataFrame([{
        'title': title, 'year': year, 'genre': genre, 'director': director,
        'rating': rating, 'language': language, 'duration': duration, 'added_on': pd.Timestamp.now()
    }])
    movies = pd.concat([movies,new_movie], ignore_index=True)
    save_movies(movies)
    return movies

def update_movie(idx, title=None, genre=None, rating=None):
    users, movies = load_users_and_movies()
    if title: movies.at[idx,'title'] = title
    if genre: movies.at[idx,'genre'] = genre
    if rating: movies.at[idx,'rating'] = rating
    save_movies(movies)
    return movies

def delete_movie(idx):
    users, movies = load_users_and_movies()
    movies = movies.drop(idx).reset_index(drop=True)
    save_movies(movies)
    return movies

# -----------------------------
# Recommendation function
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
    return df.iloc[indices][['title','genre','rating']]

# -----------------------------
# Logout helper
# -----------------------------
def safe_logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.success("Logged out successfully.")
    st.experimental_rerun()

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MovieDb", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in=False
    st.session_state.username=None
    st.session_state.role=None

menu = st.sidebar.selectbox("Choose an action", ["Signup","User Login","Admin Login"])

users, movies = load_users_and_movies()

# -----------------------------
# Signup
# -----------------------------
if menu=="Signup":
    st.header("📝 Create new user")
    new_user = st.text_input("Choose username", key="signup_user")
    new_pass = st.text_input("Choose password", type="password", key="signup_pass")
    if st.button("Signup"):
        if not new_user or not new_pass:
            st.error("Provide username and password")
        else:
            # Add user to CSV
            hashed = f"scrypt:{new_pass}"  # Placeholder: in production use proper scrypt hash
            users[new_user.strip()] = hashed
            # Save users
            df = pd.read_csv(CSV_FILE, sep="\t", dtype=str)
            new_row = pd.DataFrame([[len(df)+1,new_user.strip(),hashed,'','','','','','']], columns=df.columns)
            df = pd.concat([df,new_row], ignore_index=True)
            df.to_csv(CSV_FILE, sep="\t", index=False, header=False)
            st.success("User created. Now login from User Login")

# -----------------------------
# User Login
# -----------------------------
elif menu=="User Login":
    if not st.session_state.logged_in or st.session_state.role!="user":
        st.header("🔐 User Login")
        username = st.text_input("Username", key="user_login_user")
        password = st.text_input("Password", type="password", key="user_login_pass")
        if st.button("Login as User"):
            if username in users and verify_scrypt(users[username], password):
                st.session_state.logged_in=True
                st.session_state.username=username
                st.session_state.role="user"
                st.success(f"Welcome {username} (User)")
            else:
                st.error("Invalid username or password")
    if st.session_state.logged_in and st.session_state.role=="user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
        if user_menu=="Home":
            st.dataframe(movies,use_container_width=True)
        elif user_menu=="Filter Movies":
            genre = st.selectbox("Genre", ["All"] + sorted(movies['genre'].dropna().unique()))
            language = st.selectbox("Language", ["All"] + sorted(movies['language'].dropna().unique()))
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            filtered = movies[((movies['genre']==genre)|(genre=="All")) & ((movies['language']==language)|(language=="All")) & (movies['rating']>=rating)]
            st.dataframe(filtered,use_container_width=True)
        elif user_menu=="Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get recommendations"):
                recs = get_recommendations(movies, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.dataframe(recs,use_container_width=True)
        elif user_menu=="Logout":
            safe_logout()

# -----------------------------
# Admin Login
# -----------------------------
elif menu=="Admin Login":
    if not st.session_state.logged_in or st.session_state.role!="admin":
        st.header("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
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
        admin_menu = st.selectbox("Admin actions", ["Home","Add Movie","Update Movie","Delete Movie","Filter Movies","Recommendations","Logout"])
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
                dur = st.number_input("Duration (min)",1,1000,120)
                if st.form_submit_button("Add Movie"):
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
                    movies = update_movie(idx,new_title,new_genre,new_rating)
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
        elif admin_menu=="Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get"):
                recs = get_recommendations(movies, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.dataframe(recs,use_container_width=True)
        elif admin_menu=="Logout":
            safe_logout()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files")
