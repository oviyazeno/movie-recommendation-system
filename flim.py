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
# Ensure CSVs exist and initialize
# -----------------------------
MOVIE_COLUMNS = ["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]

if not os.path.exists(MOVIES_FILE):
    pd.DataFrame(columns=MOVIE_COLUMNS).to_csv(MOVIES_FILE, index=False)

if not os.path.exists(USERS_FILE):
    # default admin user: admin/admin123
    pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}]).to_csv(USERS_FILE, index=False)

# -----------------------------
# Auth / User functions
# -----------------------------
def load_users():
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
    # Use pandas.concat for adding a new row
    new_user_df = pd.DataFrame([{"username": username, "password_hash": hashed}])
    df = pd.concat([df, new_user_df], ignore_index=True)
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
# Data Cleaning/Type Consistency Helper
# -----------------------------
def clean_movies_df(df):
    # Ensure all required columns exist, adding them if missing
    for col in MOVIE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Enforce data types to prevent comparison/math errors
    df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').astype('Int64') # Int64 allows for NaN/null integers
    df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').astype('Int64')
    df['duration_minutes'] = pd.to_numeric(df['duration_minutes'], errors='coerce').astype('Int64')
    df['imdb_rating'] = pd.to_numeric(df['imdb_rating'], errors='coerce').astype(float)
    
    # Fill string columns with empty string to avoid errors in concatenation/unique calls
    for col in ["title", "genre", "director", "language"]:
        df[col] = df[col].fillna('').astype(str).str.strip()
        
    return df.dropna(subset=['movie_id']) # Drop rows where movie_id couldn't be converted

# -----------------------------
# Movie functions
# -----------------------------
def load_movies():
    df = pd.read_csv(MOVIES_FILE)
    return clean_movies_df(df)

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

def add_movie(title, year, genre, director, rating, language, duration):
    df = load_movies()
    new_id = df['movie_id'].max() + 1 if not df.empty and pd.notna(df['movie_id'].max()) else 1
    
    new_movie_df = pd.DataFrame([{
        "movie_id": new_id,
        "title": title.strip(),
        "release_year": year,
        "genre": genre.strip(),
        "director": director.strip(),
        "imdb_rating": rating,
        "language": language.strip(),
        "duration_minutes": duration
    }])
    df = pd.concat([df, new_movie_df], ignore_index=True)
    save_movies(df)

def update_movie(movie_id, title=None, genre=None, rating=None):
    df = load_movies()
    # Check if movie_id exists and is an integer
    if not isinstance(movie_id, int) or movie_id not in df['movie_id'].values:
        raise ValueError("Movie not found or invalid ID type")
    
    # Use loc for efficient update and ensure non-None values are used
    if title is not None: df.loc[df['movie_id']==movie_id,'title'] = title.strip()
    if genre is not None: df.loc[df['movie_id']==movie_id,'genre'] = genre.strip()
    # Ensure rating is treated as a float
    if rating is not None: df.loc[df['movie_id']==movie_id,'imdb_rating'] = float(rating)
    
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    df = df[df['movie_id'] != movie_id]
    save_movies(df)

# -----------------------------
# Recommendation function
# -----------------------------
def get_recommendations(df, base_title, topn=5):
    # Only proceed if the DataFrame is not empty and the base title is provided
    if df.empty or not base_title.strip():
        return pd.DataFrame()
    
    # 1. Prepare data for TF-IDF (ensure necessary columns are string and not empty)
    df_recs = df[['movie_id', 'title', 'genre', 'director', 'imdb_rating']].copy()
    
    # Use a minimal clean-up for the recommendation set
    df_recs['genre'] = df_recs['genre'].astype(str).fillna('')
    df_recs['director'] = df_recs['director'].astype(str).fillna('')
    df_recs['title'] = df_recs['title'].astype(str).fillna('')
    
    # Create the combined feature string
    df_recs['combined'] = df_recs['genre'] + " " + df_recs['director']
    
    # Filter out entries with no features for recommendation calculation
    df_recs = df_recs[df_recs['combined'].str.strip() != '']
    
    if df_recs.empty:
        return pd.DataFrame()

    # 2. Find the index of the base movie
    # Using 'contains' is flexible but we must ensure we get one index.
    matches = df_recs[df_recs['title'].str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return pd.DataFrame() # No match found
    
    base_idx = matches.index[0] # Get the index in the filtered/clean df_recs

    # 3. Calculate TF-IDF and Cosine Similarity
    try:
        vec = TfidfVectorizer(stop_words='english')
        tfidf = vec.fit_transform(df_recs['combined'])
    except ValueError:
        # Handle case where all documents are empty after stop word removal, though unlikely here
        return pd.DataFrame()

    # Get the row index corresponding to base_idx in the tfidf matrix
    # The index in `df_recs.index` might not be sequential from 0, 
    # but the index in `tfidf` is sequential from 0. 
    # We need to find the positional index (iloc) of `base_idx` in `df_recs.index`.
    base_pos = df_recs.index.get_loc(base_idx)
    
    cos_sim = linear_kernel(tfidf, tfidf)
    sim_scores = list(enumerate(cos_sim[base_pos]))

    # 4. Sort and retrieve top recommendations
    # Exclude the first element (which is the movie itself with score 1.0)
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1: topn+1]
    
    # Get the positional indices (iloc) for the top scores
    indices_pos = [i[0] for i in sim_scores]
    
    # Map back to the original index in df_recs for slicing
    recs_df = df_recs.iloc[indices_pos][['movie_id','title','genre','imdb_rating']]
    
    return recs_df

# -----------------------------
# Logout helper
# -----------------------------
def safe_logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.success("Logged out successfully.")
    try:
        # Attempt a full rerun to clear the state/UI completely
        st.experimental_rerun() 
    except Exception:
        # st.stop() can be used as a fallback if rerun fails/is not supported in environment
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
                st.experimental_rerun() # Rerun to switch to dashboard
            else:
                st.error("Invalid username or password")

    if st.session_state.logged_in and st.session_state.role == "user":
        st.subheader(f"👤 User Dashboard: {st.session_state.username}")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        
        if user_menu == "Home":
            st.dataframe(df[MOVIE_COLUMNS],use_container_width=True) # Ensure consistent column order
        elif user_menu == "Filter Movies":
            # Use a copy of the dataframe to manipulate options safely
            filter_df = df.copy() 
            
            # Ensure unique options don't contain empty strings for better UX, though the logic handles it
            genre_options = sorted(filter_df['genre'][filter_df['genre']!=''].unique())
            language_options = sorted(filter_df['language'][filter_df['language']!=''].unique())

            genre = st.selectbox("Genre", ["All"] + genre_options)
            language = st.selectbox("Language", ["All"] + language_options)
            rating = st.slider("Minimum rating",1.0,10.0,5.0)

            # Filtering logic is robust due to clean_movies_df ensuring types and non-null strings
            filtered = filter_df[
                ((filter_df['genre']==genre)|(genre=="All")) & 
                ((filter_df['language']==language)|(language=="All")) & 
                (filter_df['imdb_rating']>=rating)
            ]
            
            st.dataframe(filtered[MOVIE_COLUMNS],use_container_width=True)
            
        elif user_menu == "Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get recommendations"):
                recs = get_recommendations(df, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.subheader(f"Recommendations for '{base}'")
                    st.dataframe(recs,use_container_width=True)
                    
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
            # Explicitly check for 'admin' username for admin role
            if authenticate_user(admin_user, admin_pass) and admin_user.lower()=="admin": 
                st.session_state.logged_in = True
                st.session_state.username = admin_user
                st.session_state.role = "admin"
                st.success("Admin login successful")
                st.experimental_rerun() # Rerun to switch to dashboard
            else:
                st.error("Invalid admin credentials")

    if st.session_state.logged_in and st.session_state.role=="admin":
        st.subheader(f"👑 Admin Dashboard: {st.session_state.username}")
        admin_menu = st.selectbox("Admin actions",["Home","Add Movie","Update Movie","Delete Movie","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        
        if admin_menu=="Home":
            st.dataframe(df[MOVIE_COLUMNS],use_container_width=True)
        elif admin_menu=="Add Movie":
            # Add movie form (no changes needed here, only in the function)
            with st.form("add_movie_form",clear_on_submit=True):
                t = st.text_input("Title")
                yr = st.number_input("Year",1800,2100,2020)
                g = st.text_input("Genre")
                d = st.text_input("Director")
                r = st.number_input("Rating",0.0,10.0,7.0,0.1)
                lang = st.text_input("Language")
                dur = st.number_input("Duration (min)",1,1000,120)
                if st.form_submit_button("Add Movie"):
                    if not all([t, g, d, lang]):
                        st.error("Title, Genre, Director, and Language are required.")
                    else:
                        try:
                            add_movie(t.strip(), yr, g.strip(), d.strip(), r, lang.strip(), dur)
                            st.success("Movie added")
                        except Exception as e:
                            st.error(f"Add movie failed: {e}")
                            
        elif admin_menu=="Update Movie":
            if not df.empty:
                # 1. Selection
                df_selection = df[df['title']!=''] # Filter out movies with no title for selection
                if df_selection.empty:
                    st.warning("No movies available to update.")
                else:
                    selection_list = df_selection.apply(lambda r:f"{r['movie_id']} - {r['title']}",axis=1).tolist()
                    sel = st.selectbox("Select movie to update", selection_list)
                    
                    movie_id = int(sel.split(" - ")[0])
                    row = df[df['movie_id']==movie_id].iloc[0]

                    # 2. Input Fields with current values
                    with st.form("update_movie_form"):
                        new_title = st.text_input("Title",value=row['title'])
                        new_genre = st.text_input("Genre",value=row['genre'] or "")
                        # The update function needs to handle the case where the existing rating is null/NaN
                        current_rating = float(row['imdb_rating']) if pd.notna(row['imdb_rating']) else 0.0
                        new_rating = st.number_input("Rating",value=current_rating,step=0.1,min_value=0.0,max_value=10.0)
                        
                        if st.form_submit_button("Update Movie"):
                            try:
                                # Only update fields if they have a non-empty/non-none value
                                title_update = new_title if new_title.strip() != row['title'] else None
                                genre_update = new_genre if new_genre.strip() != row['genre'] else None
                                rating_update = new_rating if new_rating != current_rating else None
                                
                                if title_update is None and genre_update is None and rating_update is None:
                                    st.info("No changes were made.")
                                else:
                                    # Pass the values (which can be None for no change)
                                    update_movie(movie_id,title_update,genre_update,rating_update)
                                    st.success("Movie updated")
                                    st.experimental_rerun() # Rerun to reload the movie list
                            except Exception as e:
                                st.error(f"Update failed: {e}")

        elif admin_menu=="Delete Movie":
            if not df.empty:
                df_selection = df[df['title']!='']
                if df_selection.empty:
                    st.warning("No movies available to delete.")
                else:
                    sel = st.selectbox("Select movie to delete", df_selection.apply(lambda r:f"{r['movie_id']} - {r['title']}",axis=1))
                    movie_id = int(sel.split(" - ")[0])
                    if st.button("Delete Movie"):
                        try:
                            delete_movie(movie_id)
                            st.success("Movie deleted")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
        
        elif admin_menu=="Filter Movies":
            # Same filtering logic as in User Dashboard
            filter_df = df.copy() 
            genre_options = sorted(filter_df['genre'][filter_df['genre']!=''].unique())
            language_options = sorted(filter_df['language'][filter_df['language']!=''].unique())

            genre = st.selectbox("Genre", ["All"] + genre_options)
            language = st.selectbox("Language", ["All"] + language_options)
            rating = st.slider("Minimum rating",1.0,10.0,5.0)

            filtered = filter_df[
                ((filter_df['genre']==genre)|(genre=="All")) & 
                ((filter_df['language']==language)|(language=="All")) & 
                (filter_df['imdb_rating']>=rating)
            ]
            st.dataframe(filtered[MOVIE_COLUMNS],use_container_width=True)
            
        elif admin_menu=="Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get"):
                recs = get_recommendations(df, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.subheader(f"Recommendations for '{base}'")
                    st.dataframe(recs,use_container_width=True)
                    
        elif admin_menu=="Logout":
            safe_logout()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files")
