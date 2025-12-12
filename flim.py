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
# Ensure CSVs exist
# -----------------------------
if not os.path.exists(MOVIES_FILE):
    pd.DataFrame(columns=["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]).to_csv(MOVIES_FILE, index=False)

if not os.path.exists(USERS_FILE):
    # default admin user: admin/admin123
    pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}]).to_csv(USERS_FILE, index=False)

# -----------------------------
# Auth / User functions
# -----------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}])
        df.to_csv(USERS_FILE, index=False)
        return df
    
    df = pd.read_csv(USERS_FILE)
    if 'username' not in df.columns or 'password_hash' not in df.columns:
        df = pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}])
        df.to_csv(USERS_FILE, index=False)
    return df

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def create_user(username, password):
    df = load_users()
    if username in df['username'].values:
        raise ValueError("Username already exists")
    hashed = generate_password_hash(password)
    df = pd.concat([df, pd.DataFrame([{"username": username, "password_hash": hashed}])], ignore_index=True)
    save_users(df)

def authenticate_user(username, password):
    df = load_users()
    if 'username' not in df.columns or 'password_hash' not in df.columns:
        return False
    user = df[df['username'] == username]
    if not user.empty and check_password_hash(user.iloc[0]['password_hash'], password):
        return True
    return False

# -----------------------------
# Movie functions
# -----------------------------
def load_movies():
    if not os.path.exists(MOVIES_FILE):
        df = pd.DataFrame(columns=["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"])
        df.to_csv(MOVIES_FILE, index=False)
        return df
    
    df = pd.read_csv(MOVIES_FILE)
    # Ensure all columns exist
    for col in ["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]:
        if col not in df.columns:
            df[col] = None if col != "movie_id" else (df.index + 1)
    return df

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

def add_movie(title, year, genre, director, rating, language, duration):
    df = load_movies()
    new_id = df['movie_id'].max() + 1 if not df.empty and pd.notna(df['movie_id'].max()) else 1
    new_row = pd.DataFrame([{
        "movie_id": int(new_id),
        "title": title,
        "release_year": int(year),
        "genre": genre,
        "director": director,
        "imdb_rating": float(rating),
        "language": language,
        "duration_minutes": int(duration)
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_movies(df)

def update_movie(movie_id, title=None, genre=None, rating=None, director=None, language=None, year=None, duration=None):
    df = load_movies()
    if movie_id not in df['movie_id'].values:
        raise ValueError("Movie not found")
    
    idx = df.index[df['movie_id'] == movie_id][0]
    if title: df.at[idx, 'title'] = title
    if genre: df.at[idx, 'genre'] = genre
    if rating is not None: df.at[idx, 'imdb_rating'] = float(rating)
    if director: df.at[idx, 'director'] = director
    if language: df.at[idx, 'language'] = language
    if year: df.at[idx, 'release_year'] = int(year)
    if duration: df.at[idx, 'duration_minutes'] = int(duration)
    
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    df = df[df['movie_id'] != movie_id]
    save_movies(df)

# -----------------------------
# Recommendation function - FIXED
# -----------------------------
def get_recommendations(df, base_title, topn=5):
    if df.empty or not base_title or pd.isna(base_title):
        return pd.DataFrame()
    
    df = df.copy()
    # Fill NaN values with empty strings
    df['genre'] = df['genre'].fillna('')
    df['director'] = df['director'].fillna('')
    
    # Create combined text for similarity
    df['combined'] = df['genre'] + " " + df['director']
    
    # Find the base movie
    matches = df[df['title'].astype(str).str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return pd.DataFrame()
    
    base_idx = matches.index[0]
    
    # Calculate similarity
    try:
        vec = TfidfVectorizer(stop_words='english')
        tfidf = vec.fit_transform(df['combined'])
        cos_sim = linear_kernel(tfidf, tfidf)
        
        sim_scores = list(enumerate(cos_sim[base_idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:topn+1]
        
        indices = [i[0] for i in sim_scores]
        return df.iloc[indices][['movie_id','title','genre','imdb_rating','director']]
    except Exception as e:
        st.error(f"Recommendation error: {e}")
        return pd.DataFrame()

# -----------------------------
# Filter function - FIXED
# -----------------------------
def filter_movies(df, genre="All", language="All", min_rating=0.0):
    filtered = df.copy()
    
    # Apply genre filter
    if genre != "All":
        filtered = filtered[filtered['genre'].astype(str).str.contains(genre, case=False, na=False)]
    
    # Apply language filter
    if language != "All":
        filtered = filtered[filtered['language'].astype(str).str.contains(language, case=False, na=False)]
    
    # Apply rating filter
    filtered = filtered[filtered['imdb_rating'] >= min_rating]
    
    return filtered

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
st.set_page_config(page_title="MovieApp (Admin + Users)", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

menu = st.sidebar.selectbox("Choose an action", ["Signup","User Login","Admin Login"])

# -----------------------------
# Signup
# -----------------------------
if menu == "Signup":
    st.header("📝 Create new user")
    new_user = st.text_input("Choose username", key="signup_user")
    new_pass = st.text_input("Choose password", type="password", key="signup_pass")
    if st.button("Signup"):
        if not new_user or not new_pass:
            st.error("Provide username and password")
        else:
            try:
                create_user(new_user.strip(), new_pass.strip())
                st.success("User created. Now login from User Login")
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
                st.success(f"Welcome {user} (user)")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    if st.session_state.logged_in and st.session_state.role == "user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        
        if user_menu == "Home":
            st.dataframe(df, use_container_width=True)
            
        elif user_menu == "Filter Movies":
            # Get unique values, handling NaN
            genres = ["All"] + sorted([str(g) for g in df['genre'].dropna().unique() if str(g).strip()])
            languages = ["All"] + sorted([str(l) for l in df['language'].dropna().unique() if str(l).strip()])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                genre = st.selectbox("Genre", genres)
            with col2:
                language = st.selectbox("Language", languages)
            with col3:
                rating = st.slider("Minimum rating", 1.0, 10.0, 5.0, 0.1)
            
            filtered = filter_movies(df, genre, language, rating)
            st.dataframe(filtered, use_container_width=True)
            
        elif user_menu == "Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N", 1, 20, 5)
            
            if st.button("Get recommendations"):
                if base.strip():
                    recs = get_recommendations(df, base.strip(), topn)
                    if recs.empty:
                        st.warning("No recommendations found or movie not found")
                    else:
                        st.write(f"**Movies similar to '{base}':**")
                        st.dataframe(recs, use_container_width=True)
                else:
                    st.warning("Please enter a movie title")
                    
        elif user_menu == "Logout":
            safe_logout()

# -----------------------------
# Admin Login
# -----------------------------
elif menu == "Admin Login":
    if not st.session_state.logged_in or st.session_state.role != "admin":
        st.header("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            if authenticate_user(admin_user, admin_pass) and admin_user.lower() == "admin":
                st.session_state.logged_in = True
                st.session_state.username = admin_user
                st.session_state.role = "admin"
                st.success("Admin login successful")
                st.experimental_rerun()
            else:
                st.error("Invalid admin credentials")

    if st.session_state.logged_in and st.session_state.role == "admin":
        st.subheader("👑 Admin Dashboard")
        admin_menu = st.selectbox("Admin actions", ["Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations", "Logout"])
        df = load_movies()
        
        if admin_menu == "Home":
            st.dataframe(df, use_container_width=True)
            
        elif admin_menu == "Add Movie":
            with st.form("add_movie_form", clear_on_submit=True):
                t = st.text_input("Title*", placeholder="Movie title")
                yr = st.number_input("Year*", 1800, 2100, 2020)
                g = st.text_input("Genre*", placeholder="e.g., Action, Drama")
                d = st.text_input("Director", placeholder="Director name")
                r = st.number_input("Rating*", 0.0, 10.0, 7.0, 0.1)
                lang = st.text_input("Language", placeholder="e.g., English, Hindi")
                dur = st.number_input("Duration (min)*", 1, 1000, 120)
                
                if st.form_submit_button("Add Movie"):
                    if t.strip() and g.strip():
                        try:
                            add_movie(t.strip(), yr, g.strip(), d.strip(), r, lang.strip(), dur)
                            st.success("Movie added successfully!")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Add movie failed: {e}")
                    else:
                        st.error("Title and Genre are required fields")
                        
        elif admin_menu == "Update Movie":
            if not df.empty:
                # Create a dropdown with movie titles
                movie_options = df.apply(lambda r: f"{int(r['movie_id'])} - {r['title']}", axis=1)
                sel = st.selectbox("Select movie to update", movie_options)
                
                if sel:
                    movie_id = int(sel.split(" - ")[0])
                    row = df[df['movie_id'] == movie_id].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_title = st.text_input("Title", value=row['title'] if pd.notna(row['title']) else "")
                        new_genre = st.text_input("Genre", value=row['genre'] if pd.notna(row['genre']) else "")
                        new_rating = st.number_input("Rating", value=float(row['imdb_rating']) if pd.notna(row['imdb_rating']) else 0.0, min_value=0.0, max_value=10.0, step=0.1)
                    with col2:
                        new_director = st.text_input("Director", value=row['director'] if pd.notna(row['director']) else "")
                        new_language = st.text_input("Language", value=row['language'] if pd.notna(row['language']) else "")
                        new_year = st.number_input("Year", value=int(row['release_year']) if pd.notna(row['release_year']) else 2020, min_value=1800, max_value=2100)
                        new_duration = st.number_input("Duration (min)", value=int(row['duration_minutes']) if pd.notna(row['duration_minutes']) else 120, min_value=1, max_value=1000)
                    
                    if st.button("Update Movie"):
                        try:
                            update_movie(movie_id, new_title, new_genre, new_rating, new_director, new_language, new_year, new_duration)
                            st.success("Movie updated successfully!")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")
            else:
                st.warning("No movies available to update")
                
        elif admin_menu == "Delete Movie":
            if not df.empty:
                movie_options = df.apply(lambda r: f"{int(r['movie_id'])} - {r['title']}", axis=1)
                sel = st.selectbox("Select movie to delete", movie_options)
                
                if sel:
                    movie_id = int(sel.split(" - ")[0])
                    st.warning(f"Are you sure you want to delete movie ID {movie_id}?")
                    
                    if st.button("Confirm Delete"):
                        try:
                            delete_movie(movie_id)
                            st.success("Movie deleted successfully!")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
            else:
                st.warning("No movies available to delete")
                
        elif admin_menu == "Filter Movies":
            genres = ["All"] + sorted([str(g) for g in df['genre'].dropna().unique() if str(g).strip()])
            languages = ["All"] + sorted([str(l) for l in df['language'].dropna().unique() if str(l).strip()])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                genre = st.selectbox("Genre filter", genres, key="admin_genre")
            with col2:
                language = st.selectbox("Language filter", languages, key="admin_language")
            with col3:
                rating = st.slider("Minimum rating filter", 1.0, 10.0, 5.0, 0.1, key="admin_rating")
            
            filtered = filter_movies(df, genre, language, rating)
            st.dataframe(filtered, use_container_width=True)
            
        elif admin_menu == "Recommendations":
            base = st.text_input("Type movie title for recommendations", key="admin_rec_input")
            topn = st.number_input("Top N", 1, 20, 5, key="admin_topn")
            
            if st.button("Get recommendations", key="admin_rec_button"):
                if base.strip():
                    recs = get_recommendations(df, base.strip(), topn)
                    if recs.empty:
                        st.warning("No recommendations found or movie not found")
                    else:
                        st.write(f"**Movies similar to '{base}':**")
                        st.dataframe(recs, use_container_width=True)
                else:
                    st.warning("Please enter a movie title")
                    
        elif admin_menu == "Logout":
            safe_logout()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files")
