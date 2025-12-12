# app.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import os

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
    
    try:
        df = pd.read_csv(USERS_FILE)
        if df.empty or 'username' not in df.columns or 'password_hash' not in df.columns:
            df = pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}])
            df.to_csv(USERS_FILE, index=False)
    except Exception as e:
        df = pd.DataFrame([{"username":"admin","password_hash":generate_password_hash("admin123")}])
        df.to_csv(USERS_FILE, index=False)
    
    return df

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def create_user(username, password):
    df = load_users()
    if not df.empty and username in df['username'].values:
        raise ValueError("Username already exists")
    hashed = generate_password_hash(password)
    new_df = pd.DataFrame([{"username": username, "password_hash": hashed}])
    df = pd.concat([df, new_df], ignore_index=True)
    save_users(df)

def authenticate_user(username, password):
    df = load_users()
    if df.empty or 'username' not in df.columns or 'password_hash' not in df.columns:
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
    
    try:
        df = pd.read_csv(MOVIES_FILE)
    except:
        df = pd.DataFrame(columns=["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"])
    
    # Ensure all columns exist
    for col in ["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes"]:
        if col not in df.columns:
            if col == "movie_id":
                df[col] = range(1, len(df) + 1) if not df.empty else []
            else:
                df[col] = None
    
    # Convert data types
    if not df.empty:
        if 'movie_id' in df.columns:
            df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').fillna(0).astype(int)
        if 'release_year' in df.columns:
            df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').fillna(2020).astype(int)
        if 'imdb_rating' in df.columns:
            df['imdb_rating'] = pd.to_numeric(df['imdb_rating'], errors='coerce').fillna(5.0)
        if 'duration_minutes' in df.columns:
            df['duration_minutes'] = pd.to_numeric(df['duration_minutes'], errors='coerce').fillna(120).astype(int)
    
    return df

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

def add_movie(title, year, genre, director, rating, language, duration):
    df = load_movies()
    if df.empty:
        new_id = 1
    else:
        max_id = df['movie_id'].max() if 'movie_id' in df.columns and not df['movie_id'].isna().all() else 0
        new_id = int(max_id) + 1
    
    new_row = pd.DataFrame([{
        "movie_id": new_id,
        "title": str(title),
        "release_year": int(year),
        "genre": str(genre),
        "director": str(director),
        "imdb_rating": float(rating),
        "language": str(language),
        "duration_minutes": int(duration)
    }])
    
    df = pd.concat([df, new_row], ignore_index=True)
    save_movies(df)

def update_movie(movie_id, title=None, genre=None, rating=None, director=None, language=None, year=None, duration=None):
    df = load_movies()
    if df.empty or 'movie_id' not in df.columns:
        raise ValueError("No movies found")
    
    df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').astype(int)
    
    if int(movie_id) not in df['movie_id'].values:
        raise ValueError(f"Movie with ID {movie_id} not found")
    
    idx = df.index[df['movie_id'] == int(movie_id)].tolist()
    if not idx:
        raise ValueError(f"Movie with ID {movie_id} not found")
    
    idx = idx[0]
    
    if title is not None: df.at[idx, 'title'] = str(title)
    if genre is not None: df.at[idx, 'genre'] = str(genre)
    if rating is not None: df.at[idx, 'imdb_rating'] = float(rating)
    if director is not None: df.at[idx, 'director'] = str(director)
    if language is not None: df.at[idx, 'language'] = str(language)
    if year is not None: df.at[idx, 'release_year'] = int(year)
    if duration is not None: df.at[idx, 'duration_minutes'] = int(duration)
    
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    if df.empty:
        raise ValueError("No movies found")
    
    df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').astype(int)
    df = df[df['movie_id'] != int(movie_id)]
    save_movies(df)

# -----------------------------
# Recommendation function
# -----------------------------
def get_recommendations(df, base_title, topn=5):
    if df.empty or not base_title or pd.isna(base_title) or base_title.strip() == "":
        return pd.DataFrame()
    
    df = df.copy()
    # Fill NaN values with empty strings
    df['genre'] = df['genre'].fillna('')
    df['director'] = df['director'].fillna('')
    
    # Create combined text for similarity
    df['combined'] = df['genre'] + " " + df['director']
    
    # Find the base movie
    try:
        matches = df[df['title'].astype(str).str.contains(str(base_title), case=False, na=False)]
        if matches.empty:
            return pd.DataFrame()
        
        base_idx = matches.index[0]
        
        # Calculate similarity
        if len(df) > 1:
            vec = TfidfVectorizer(stop_words='english')
            tfidf = vec.fit_transform(df['combined'])
            cos_sim = linear_kernel(tfidf, tfidf)
            
            sim_scores = list(enumerate(cos_sim[base_idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:topn+1]
            
            indices = [i[0] for i in sim_scores]
            return df.iloc[indices][['movie_id','title','genre','imdb_rating','director']].reset_index(drop=True)
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Recommendation error: {e}")
        return pd.DataFrame()

# -----------------------------
# Filter function
# -----------------------------
def filter_movies(df, genre="All", language="All", min_rating=0.0):
    filtered = df.copy()
    
    # Apply rating filter first
    filtered['imdb_rating'] = pd.to_numeric(filtered['imdb_rating'], errors='coerce')
    filtered = filtered[filtered['imdb_rating'] >= min_rating]
    
    # Apply genre filter
    if genre != "All":
        filtered = filtered[filtered['genre'].astype(str).str.contains(str(genre), case=False, na=False)]
    
    # Apply language filter
    if language != "All":
        filtered = filtered[filtered['language'].astype(str).str.contains(str(language), case=False, na=False)]
    
    return filtered.reset_index(drop=True)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MovieApp (Admin + Users)", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

# Sidebar navigation
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Choose an action", ["Home", "Signup", "User Login", "Admin Login"])

# -----------------------------
# Home Page
# -----------------------------
if menu == "Home":
    st.header("Welcome to Movie Database")
    st.write("""
    This application allows you to:
    - **Users**: Browse movies, filter by genre/language/rating, get recommendations
    - **Admins**: Add, update, and delete movies
    - **All**: Sign up for a new account
    
    Please use the sidebar to navigate to your desired section.
    """)
    
    # Show some movie stats
    try:
        df = load_movies()
        if not df.empty:
            st.subheader("📊 Movie Database Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Movies", len(df))
            with col2:
                st.metric("Average Rating", f"{df['imdb_rating'].mean():.1f}" if 'imdb_rating' in df.columns else "N/A")
            with col3:
                st.metric("Unique Genres", df['genre'].nunique() if 'genre' in df.columns else "N/A")
    except:
        pass

# -----------------------------
# Signup
# -----------------------------
elif menu == "Signup":
    st.header("📝 Create new user")
    new_user = st.text_input("Choose username", key="signup_user")
    new_pass = st.text_input("Choose password", type="password", key="signup_pass")
    confirm_pass = st.text_input("Confirm password", type="password", key="confirm_pass")
    
    if st.button("Signup"):
        if not new_user or not new_pass:
            st.error("Username and password are required")
        elif new_pass != confirm_pass:
            st.error("Passwords do not match")
        elif len(new_user.strip()) < 3:
            st.error("Username must be at least 3 characters long")
        elif len(new_pass.strip()) < 6:
            st.error("Password must be at least 6 characters long")
        else:
            try:
                create_user(new_user.strip(), new_pass.strip())
                st.success(f"User '{new_user}' created successfully! You can now login.")
                st.info("Please select 'User Login' from the sidebar to login.")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Signup failed: {e}")

# -----------------------------
# User Login
# -----------------------------
elif menu == "User Login":
    if not st.session_state.logged_in:
        st.header("🔐 User Login")
        user = st.text_input("Username", key="user_login_user")
        pwd = st.text_input("Password", type="password", key="user_login_pass")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Login as User"):
                if not user or not pwd:
                    st.error("Please enter both username and password")
                else:
                    if authenticate_user(user, pwd):
                        st.session_state.logged_in = True
                        st.session_state.username = user
                        st.session_state.role = "user"
                        st.success(f"Welcome {user}! Login successful.")
                        # Use rerun instead of experimental_rerun
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        with col2:
            if st.button("Back to Home"):
                st.rerun()
    
    # User Dashboard
    if st.session_state.logged_in and st.session_state.role == "user":
        st.header(f"👤 Welcome {st.session_state.username} (User)")
        
        user_menu = st.selectbox("Choose Action", ["View All Movies", "Filter Movies", "Get Recommendations", "Logout"])
        df = load_movies()
        
        if user_menu == "View All Movies":
            if not df.empty:
                st.subheader("All Movies")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No movies available in the database.")
                
        elif user_menu == "Filter Movies":
            st.subheader("Filter Movies")
            
            if not df.empty:
                # Get unique values
                genres = ["All"] + sorted([str(g) for g in df['genre'].dropna().unique() if str(g).strip() != ''])
                languages = ["All"] + sorted([str(l) for l in df['language'].dropna().unique() if str(l).strip() != ''])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    genre = st.selectbox("Genre", genres)
                with col2:
                    language = st.selectbox("Language", languages)
                with col3:
                    rating = st.slider("Minimum rating", 1.0, 10.0, 5.0, 0.1)
                
                filtered = filter_movies(df, genre, language, rating)
                
                if not filtered.empty:
                    st.write(f"**Found {len(filtered)} movie(s):**")
                    st.dataframe(filtered, use_container_width=True, hide_index=True)
                else:
                    st.warning("No movies match your filters.")
            else:
                st.info("No movies available to filter.")
                
        elif user_menu == "Get Recommendations":
            st.subheader("Get Movie Recommendations")
            
            if not df.empty:
                movie_titles = sorted([str(t) for t in df['title'].dropna().unique() if str(t).strip() != ''])
                
                if movie_titles:
                    selected_movie = st.selectbox("Select a movie", movie_titles)
                    topn = st.slider("Number of recommendations", 1, 10, 5)
                    
                    if st.button("Get Recommendations"):
                        if selected_movie:
                            with st.spinner("Finding similar movies..."):
                                recs = get_recommendations(df, selected_movie, topn)
                                
                            if not recs.empty:
                                st.success(f"Movies similar to '{selected_movie}':")
                                st.dataframe(recs, use_container_width=True, hide_index=True)
                            else:
                                st.warning(f"No recommendations found for '{selected_movie}'. Try selecting another movie.")
                else:
                    st.info("No movie titles available for recommendations.")
            else:
                st.info("No movies available for recommendations.")
                
        elif user_menu == "Logout":
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.success("Logged out successfully!")
            st.rerun()

# -----------------------------
# Admin Login
# -----------------------------
elif menu == "Admin Login":
    if not st.session_state.logged_in:
        st.header("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Login as Admin"):
                if not admin_user or not admin_pass:
                    st.error("Please enter both username and password")
                else:
                    if admin_user.lower() == "admin" and authenticate_user(admin_user, admin_pass):
                        st.session_state.logged_in = True
                        st.session_state.username = admin_user
                        st.session_state.role = "admin"
                        st.success("Admin login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid admin credentials")
        
        with col2:
            if st.button("Back to Home"):
                st.rerun()
    
    # Admin Dashboard
    if st.session_state.logged_in and st.session_state.role == "admin":
        st.header(f"👑 Admin Dashboard - Welcome {st.session_state.username}")
        
        admin_menu = st.selectbox("Admin Actions", 
                                 ["View All Movies", "Add New Movie", "Update Movie", "Delete Movie", 
                                  "Filter Movies", "Get Recommendations", "Logout"])
        
        df = load_movies()
        
        if admin_menu == "View All Movies":
            if not df.empty:
                st.subheader("All Movies in Database")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No movies in the database yet.")
                
        elif admin_menu == "Add New Movie":
            st.subheader("Add New Movie")
            
            with st.form("add_movie_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("Title*", placeholder="Enter movie title")
                    year = st.number_input("Release Year*", 1900, 2100, 2023)
                    genre = st.text_input("Genre*", placeholder="e.g., Action, Drama, Comedy")
                
                with col2:
                    director = st.text_input("Director", placeholder="Director name")
                    rating = st.number_input("IMDB Rating*", 0.0, 10.0, 7.0, 0.1)
                    language = st.text_input("Language", placeholder="e.g., English")
                    duration = st.number_input("Duration (minutes)*", 1, 500, 120)
                
                submitted = st.form_submit_button("Add Movie")
                
                if submitted:
                    if title.strip() and genre.strip():
                        try:
                            add_movie(title.strip(), year, genre.strip(), director.strip(), 
                                     rating, language.strip(), duration)
                            st.success(f"Movie '{title}' added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding movie: {e}")
                    else:
                        st.error("Title and Genre are required fields!")
                        
        elif admin_menu == "Update Movie":
            st.subheader("Update Movie Information")
            
            if not df.empty:
                movie_options = ["Select a movie"] + sorted(
                    [f"{int(row['movie_id'])} - {row['title']}" 
                     for _, row in df.iterrows() 
                     if pd.notna(row['movie_id']) and pd.notna(row['title'])]
                )
                
                selected = st.selectbox("Choose movie to update", movie_options)
                
                if selected != "Select a movie":
                    movie_id = int(selected.split(" - ")[0])
                    movie_data = df[df['movie_id'] == movie_id].iloc[0]
                    
                    with st.form("update_movie_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_title = st.text_input("Title", value=str(movie_data['title']) if pd.notna(movie_data['title']) else "")
                            new_year = st.number_input("Release Year", 1900, 2100, 
                                                      int(movie_data['release_year']) if pd.notna(movie_data['release_year']) else 2023)
                            new_genre = st.text_input("Genre", value=str(movie_data['genre']) if pd.notna(movie_data['genre']) else "")
                        
                        with col2:
                            new_director = st.text_input("Director", value=str(movie_data['director']) if pd.notna(movie_data['director']) else "")
                            new_rating = st.number_input("IMDB Rating", 0.0, 10.0, 
                                                        float(movie_data['imdb_rating']) if pd.notna(movie_data['imdb_rating']) else 5.0, 0.1)
                            new_language = st.text_input("Language", value=str(movie_data['language']) if pd.notna(movie_data['language']) else "")
                            new_duration = st.number_input("Duration (minutes)", 1, 500, 
                                                          int(movie_data['duration_minutes']) if pd.notna(movie_data['duration_minutes']) else 120)
                        
                        if st.form_submit_button("Update Movie"):
                            try:
                                update_movie(movie_id, new_title, new_genre, new_rating, 
                                           new_director, new_language, new_year, new_duration)
                                st.success("Movie updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating movie: {e}")
            else:
                st.info("No movies available to update.")
                
        elif admin_menu == "Delete Movie":
            st.subheader("Delete Movie")
            
            if not df.empty:
                movie_options = ["Select a movie"] + sorted(
                    [f"{int(row['movie_id'])} - {row['title']}" 
                     for _, row in df.iterrows() 
                     if pd.notna(row['movie_id']) and pd.notna(row['title'])]
                )
                
                selected = st.selectbox("Choose movie to delete", movie_options)
                
                if selected != "Select a movie":
                    movie_id = int(selected.split(" - ")[0])
                    movie_title = selected.split(" - ")[1]
                    
                    st.warning(f"⚠️ You are about to delete: **{movie_title}** (ID: {movie_id})")
                    st.warning("This action cannot be undone!")
                    
                    if st.button("Confirm Delete"):
                        try:
                            delete_movie(movie_id)
                            st.success(f"Movie '{movie_title}' deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting movie: {e}")
            else:
                st.info("No movies available to delete.")
                
        elif admin_menu == "Filter Movies":
            st.subheader("Filter Movies")
            
            if not df.empty:
                genres = ["All"] + sorted([str(g) for g in df['genre'].dropna().unique() if str(g).strip() != ''])
                languages = ["All"] + sorted([str(l) for l in df['language'].dropna().unique() if str(l).strip() != ''])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    genre = st.selectbox("Genre", genres, key="admin_filter_genre")
                with col2:
                    language = st.selectbox("Language", languages, key="admin_filter_language")
                with col3:
                    rating = st.slider("Minimum rating", 1.0, 10.0, 5.0, 0.1, key="admin_filter_rating")
                
                filtered = filter_movies(df, genre, language, rating)
                
                if not filtered.empty:
                    st.write(f"**Found {len(filtered)} movie(s):**")
                    st.dataframe(filtered, use_container_width=True, hide_index=True)
                else:
                    st.warning("No movies match your filters.")
            else:
                st.info("No movies available to filter.")
                
        elif admin_menu == "Get Recommendations":
            st.subheader("Get Movie Recommendations")
            
            if not df.empty:
                movie_titles = sorted([str(t) for t in df['title'].dropna().unique() if str(t).strip() != ''])
                
                if movie_titles:
                    selected_movie = st.selectbox("Select a movie", movie_titles, key="admin_rec_movie")
                    topn = st.slider("Number of recommendations", 1, 10, 5, key="admin_rec_topn")
                    
                    if st.button("Get Recommendations", key="admin_rec_button"):
                        if selected_movie:
                            with st.spinner("Finding similar movies..."):
                                recs = get_recommendations(df, selected_movie, topn)
                                
                            if not recs.empty:
                                st.success(f"Movies similar to '{selected_movie}':")
                                st.dataframe(recs, use_container_width=True, hide_index=True)
                            else:
                                st.warning(f"No recommendations found for '{selected_movie}'. Try selecting another movie.")
                else:
                    st.info("No movie titles available for recommendations.")
            else:
                st.info("No movies available for recommendations.")
                
        elif admin_menu == "Logout":
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.success("Admin logged out successfully!")
            st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.info("**Movie Database App**\n\nData is stored in CSV files.")
