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
MOVIE_COLUMNS = ["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]

# -----------------------------
# Ensure CSVs exist
# -----------------------------
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
# Movie functions
# -----------------------------
def load_movies():
    df = pd.read_csv(MOVIES_FILE)
    
    # --- FIX 1: Ensure columns exist, correct types, and handle nulls ---
    for col in MOVIE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Ensure numeric columns are correct, handling potential NaN/nulls
    df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').astype('Int64')
    df['imdb_rating'] = pd.to_numeric(df['imdb_rating'], errors='coerce').astype(float)
    
    # Ensure string columns are non-null strings for filtering/recommendations
    for col in ["title", "genre", "director", "language"]:
        df[col] = df[col].fillna('').astype(str).str.strip()
        
    return df

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
        
    if title: df.loc[df['movie_id']==movie_id,'title'] = title.strip()
    if genre: df.loc[df['movie_id']==movie_id,'genre'] = genre.strip()
    # FIX 2: Ensure rating is treated as a float
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
    # FIX 3: Recommendation logic correction
    if df.empty or not base_title.strip():
        return pd.DataFrame()
    
    df_recs = df.copy()
    
    # Combined feature column created from clean strings (done in load_movies)
    df_recs['combined'] = df_recs['genre'] + " " + df_recs['director']
    
    # Filter out entries with no features for recommendation calculation
    df_recs = df_recs[df_recs['combined'].str.strip() != '']
    
    if df_recs.empty:
        return pd.DataFrame()

    # Find the movie index using its title
    matches = df_recs[df_recs['title'].str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return pd.DataFrame() 
    
    # Get the PANDAS index (label) of the first match
    base_movie_idx_label = matches.index[0]
    
    # Calculate TF-IDF
    vec = TfidfVectorizer(stop_words='english')
    try:
        tfidf = vec.fit_transform(df_recs['combined'])
    except ValueError:
        return pd.DataFrame()

    # CRITICAL FIX: Find the POSITIONAL index (iloc) of the base movie 
    # within the df_recs dataframe (which matches the tfidf matrix index)
    base_pos = df_recs.index.get_loc(base_movie_idx_label)
    
    # Calculate Cosine Similarity
    cos_sim = linear_kernel(tfidf, tfidf)
    
    # Get similarity scores for the base movie (using the positional index)
    sim_scores = list(enumerate(cos_sim[base_pos])) 
    
    # Sort and retrieve top N (excluding the movie itself)
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1: topn+1]
    
    # Get the POSITIONAL indices (iloc) for the top scores
    indices_pos = [i[0] for i in sim_scores]
    
    # Return the recommended movies using iloc on the clean df_recs
    return df_recs.iloc[indices_pos][['movie_id','title','genre','imdb_rating']]


# -----------------------------
# Logout helper
# -----------------------------
def safe_logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.success("Logged out successfully.")
    try:
        st.experimental_rerun()
    except Exception:
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
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    if st.session_state.logged_in and st.session_state.role == "user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        
        if user_menu == "Home":
            st.dataframe(df,use_container_width=True)
            
        elif user_menu == "Filter Movies":
            # Uses the cleaned data from load_movies()
            filter_df = df.copy() 
            genre_options = sorted(filter_df['genre'][filter_df['genre']!=''].unique())
            language_options = sorted(filter_df['language'][filter_df['language']!=''].unique())
            
            genre = st.selectbox("Genre", ["All"] + genre_options)
            language = st.selectbox("Language", ["All"] + language_options)
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            
            # Filtering works reliably because imdb_rating is float and genre/language are non-null strings
            filtered = filter_df[
                ((filter_df['genre']==genre)|(genre=="All")) & 
                ((filter_df['language']==language)|(language=="All")) & 
                (filter_df['imdb_rating']>=rating)
            ]
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
            if authenticate_user(admin_user, admin_pass) and admin_user.lower()=="admin":
                st.session_state.logged_in = True
                st.session_state.username = admin_user
                st.session_state.role = "admin"
                st.success("Admin login successful")
                st.experimental_rerun()
            else:
                st.error("Invalid admin credentials")

    if st.session_state.logged_in and st.session_state.role=="admin":
        st.subheader("👑 Admin Dashboard")
        admin_menu = st.selectbox("Admin actions",["Home","Add Movie","Update Movie","Delete Movie","Filter Movies","Recommendations","Logout"])
        df = load_movies()
        
        if admin_menu=="Home":
            st.dataframe(df,use_container_width=True)
            
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
                    try:
                        add_movie(t.strip(), yr, g.strip(), d.strip(), r, lang.strip(), dur)
                        st.success("Movie added")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Add movie failed: {e}")
                        
        elif admin_menu=="Update Movie":
            if not df.empty:
                df_selection = df[df['title']!='']
                if df_selection.empty:
                    st.warning("No movies available to update.")
                else:
                    selection_list = df_selection.apply(lambda r:f"{r['movie_id']} - {r['title']}",axis=1).tolist()
                    sel = st.selectbox("Select movie to update", selection_list)
                    
                    movie_id = int(sel.split(" - ")[0])
                    row = df[df['movie_id']==movie_id].iloc[0]

                    # FIX 4: Safely retrieve current rating for UI input
                    current_rating = float(row['imdb_rating']) if pd.notna(row['imdb_rating']) else 0.0
                    
                    new_title = st.text_input("Title",value=row['title'])
                    new_genre = st.text_input("Genre",value=row['genre'] or "")
                    new_rating = st.number_input("Rating",value=current_rating,step=0.1,min_value=0.0,max_value=10.0)
                    
                    if st.button("Update"):
                        try:
                            # Only update if there is a change
                            title_update = new_title if new_title.strip() != row['title'] else None
                            genre_update = new_genre if new_genre.strip() != row['genre'] else None
                            rating_update = new_rating if new_rating != current_rating else None
                            
                            update_movie(movie_id, new_title, new_genre, new_rating)
                            st.success("Movie updated")
                            st.experimental_rerun()
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
            # Uses the cleaned data from load_movies()
            filter_df = df.copy() 
            genre_options = sorted(filter_df['genre'][filter_df['genre']!=''].unique())
            language_options = sorted(filter_df['language'][filter_df['language']!=''].unique())

            genre = st.selectbox("Genre", ["All"] + genre_options)
            language = st.selectbox("Language", ["All"] + language_options)
            rating = st.slider("Minimum rating",1.0,10.0,5.0)
            
            # Filtering works reliably because imdb_rating is float and genre/language are non-null strings
            filtered = filter_df[
                ((filter_df['genre']==genre)|(genre=="All")) & 
                ((filter_df['language']==language)|(language=="All")) & 
                (filter_df['imdb_rating']>=rating)
            ]
            st.dataframe(filtered,use_container_width=True)
            
        elif admin_menu=="Recommendations":
            base = st.text_input("Type movie title for recommendations")
            topn = st.number_input("Top N",1,20,5)
            if st.button("Get"):
                recs = get_recommendations(df, base, topn)
                if recs.empty:
                    st.warning("No recommendations found")
                else:
                    st.dataframe(recs,use_container_width=True)
                    
        elif admin_menu=="Logout":
            safe_logout()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files")
