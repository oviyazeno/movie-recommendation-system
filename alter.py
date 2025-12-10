# app.py
"""
Streamlit Movie Recommender (Admin + Users)
Single-file app that connects to SQL Server via pyodbc.

How to run:
  1. Make sure SQL Server is running and you have a working ODBC driver (e.g. "ODBC Driver 17 for SQL Server").
  2. Install dependencies: pip install streamlit pyodbc pandas
  3. Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import pyodbc
import hashlib
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# ==========================
# CONFIG - edit to suit
# ==========================
SERVER = "localhost"                    # your SQL Server host
DATABASE = "MovieDb"                    # your database
DRIVER = "{ODBC Driver 17 for SQL Server}"  # adjust if necessary

# Connection string used by connect()
CNXN_STR = (
    f"DRIVER={DRIVER};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

# Default admin credentials (change here if you like)
# We store only a hash here. If you want to change password,
# change ADMIN_PASSWORD_PLAIN then re-run.
ADMIN_USERNAME = "Zeno"
ADMIN_PASSWORD_PLAIN = "Zeno@123"
ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD_PLAIN.encode("utf-8")).hexdigest()

# ==========================
# DB helpers
# ==========================
def connect() -> Tuple[pyodbc.Connection, pyodbc.Cursor]:
    """Return an open connection and cursor. Caller must close()."""
    cnxn = pyodbc.connect(CNXN_STR, autocommit=False)
    cursor = cnxn.cursor()
    return cnxn, cursor

def try_connect() -> Tuple[bool, Optional[str]]:
    """Test DB connection; return success flag and optional error."""
    try:
        cnxn, cursor = connect()
        cursor.execute("SELECT 1")
        cnxn.close()
        return True, None
    except Exception as e:
        return False, str(e)

# ==========================
# Utility functions
# ==========================
def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def row_to_dict(row) -> Dict:
    # expects the movies table to be in the schema below
    return {
        "movie_id": int(row.movie_id),
        "title": row.title,
        "release_year": int(row.release_year) if row.release_year is not None else None,
        "genre": row.genre or "",
        "director": row.director or "",
        "imdb_rating": float(row.imdb_rating) if row.imdb_rating is not None else None,
        "language": row.language or "",
        "duration_minutes": int(row.duration_minutes) if row.duration_minutes is not None else None,
        "created_at": row.created_at
    }

# ==========================
# SCHEMA CREATION (run once)
# ==========================
def ensure_tables():
    """Create minimal tables if they don't exist."""
    cnxn, cursor = connect()
    try:
        # users
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U'))
        BEGIN
            CREATE TABLE dbo.users (
                user_id INT IDENTITY(1,1) PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT GETDATE()
            );
        END
        """)
        # search_history
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[search_history]') AND type in (N'U'))
        BEGIN
            CREATE TABLE dbo.search_history (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                movie_title VARCHAR(500) NOT NULL,
                search_time DATETIME DEFAULT GETDATE(),
                CONSTRAINT FK_search_history_user FOREIGN KEY (user_id) REFERENCES dbo.users(user_id)
            );
        END
        """)
        # movies
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[movies]') AND type in (N'U'))
        BEGIN
            CREATE TABLE dbo.movies (
                movie_id INT IDENTITY(1,1) PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                release_year INT NULL,
                genre VARCHAR(255) NULL,
                director VARCHAR(255) NULL,
                imdb_rating DECIMAL(3,1) NULL,
                language VARCHAR(100) NULL,
                duration_minutes INT NULL,
                created_at DATETIME DEFAULT GETDATE()
            );
        END
        """)
        cnxn.commit()
    finally:
        cnxn.close()

# ==========================
# Basic DB fetch helpers
# ==========================
def load_all_movies() -> List[Dict]:
    cnxn, cursor = connect()
    try:
        rows = cursor.execute("SELECT movie_id, title, release_year, genre, director, imdb_rating, language, duration_minutes, created_at FROM dbo.movies").fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        cnxn.close()

def df_all_movies() -> pd.DataFrame:
    rows = load_all_movies()
    if not rows:
        return pd.DataFrame(columns=["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes","created_at"])
    return pd.DataFrame(rows)

def find_movie_by_title(title_partial: str) -> List[Dict]:
    cnxn, cursor = connect()
    try:
        rows = cursor.execute("SELECT movie_id, title, release_year, genre, director, imdb_rating, language, duration_minutes, created_at FROM dbo.movies WHERE title LIKE ?", ('%' + title_partial + '%',)).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        cnxn.close()

# ==========================
# ADMIN CRUD
# ==========================
def admin_insert_movie(title, release_year, genre, director, rating, language, duration):
    cnxn, cursor = connect()
    try:
        cursor.execute("""
            INSERT INTO dbo.movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, release_year if release_year else None, genre, director, rating if rating else None, language, duration if duration else None))
        cnxn.commit()
    finally:
        cnxn.close()

def admin_update_movie_field(movie_id:int, field:str, value):
    # field should be validated by caller
    cnxn, cursor = connect()
    try:
        query = f"UPDATE dbo.movies SET {field} = ? WHERE movie_id = ?"
        cursor.execute(query, (value, movie_id))
        cnxn.commit()
    finally:
        cnxn.close()

def admin_delete_movie(movie_id:int):
    cnxn, cursor = connect()
    try:
        cursor.execute("DELETE FROM dbo.movies WHERE movie_id = ?", (movie_id,))
        cnxn.commit()
    finally:
        cnxn.close()

def admin_bulk_insert(movies_list: List[tuple]):
    cnxn, cursor = connect()
    try:
        query = """
            INSERT INTO dbo.movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.fast_executemany = True
        cursor.executemany(query, movies_list)
        cnxn.commit()
    finally:
        cnxn.close()

# ==========================
# USER management & history
# ==========================
def user_register(username: str, password: str) -> Tuple[bool,str]:
    cnxn, cursor = connect()
    try:
        phash = hash_password(password)
        try:
            cursor.execute("INSERT INTO dbo.users (username, password_hash) VALUES (?, ?)", (username, phash))
            cnxn.commit()
            return True, "Registered successfully"
        except pyodbc.IntegrityError:
            return False, "Username already exists"
    finally:
        cnxn.close()

def user_login(username: str, password: str) -> Tuple[bool, Optional[int]]:
    cnxn, cursor = connect()
    try:
        row = cursor.execute("SELECT user_id, password_hash FROM dbo.users WHERE username = ?", (username,)).fetchone()
        if not row:
            return False, None
        user_id, stored_hash = int(row.user_id), row.password_hash
        if stored_hash == hash_password(password):
            return True, user_id
        return False, None
    finally:
        cnxn.close()

def save_search_history(user_id: int, movie_title: str):
    cnxn, cursor = connect()
    try:
        cursor.execute("INSERT INTO dbo.search_history (user_id, movie_title) VALUES (?, ?)", (user_id, movie_title))
        cnxn.commit()
    finally:
        cnxn.close()

def get_user_history(user_id:int, limit:int=50):
    cnxn, cursor = connect()
    try:
        rows = cursor.execute("SELECT movie_title, search_time FROM dbo.search_history WHERE user_id = ? ORDER BY search_time DESC", (user_id,)).fetchmany(limit)
        return [(r.movie_title, r.search_time) for r in rows]
    finally:
        cnxn.close()

# ==========================
# SIMPLE CONTENT-BASED RECOMMENDER
# ==========================
def genre_overlap_score(base_genre, other_genre):
    base_set = set([g.strip().lower() for g in str(base_genre).replace('/', ',').split(',') if g.strip()])
    other_set = set([g.strip().lower() for g in str(other_genre).replace('/', ',').split(',') if g.strip()])
    if not base_set:
        return 0.0
    return len(base_set.intersection(other_set)) / max(1, len(base_set))

def compute_score(base_movie:dict, candidate:dict):
    score = 0.0
    if base_movie.get('director') and candidate.get('director'):
        if base_movie['director'].strip().lower() == candidate['director'].strip().lower():
            score += 3.0
    score += genre_overlap_score(base_movie.get('genre',''), candidate.get('genre','')) * 2.0
    # normalize rating contribution (0..1)
    if candidate.get('imdb_rating') is not None:
        try:
            score += (float(candidate.get('imdb_rating')) / 10.0)
        except:
            pass
    if base_movie.get('release_year') and candidate.get('release_year'):
        diff = int(candidate['release_year']) - int(base_movie['release_year'])
        if abs(diff) <= 5:
            score += 0.2
        elif abs(diff) <= 15:
            score += 0.05
    return score

def recommend_similar_from_df(df: pd.DataFrame, base_title: str, limit=8):
    matches = df[df['title'].str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return None, []
    exact = matches[matches['title'].str.lower() == base_title.strip().lower()]
    base_row = exact.iloc[0] if not exact.empty else matches.iloc[0]
    base_movie = base_row.to_dict()
    candidates = df[df['movie_id'] != base_movie['movie_id']].to_dict('records')
    scored = []
    for c in candidates:
        s = compute_score(base_movie, c)
        scored.append((s, c))
    # sort by score then rating
    scored.sort(key=lambda x: (x[0], x[1].get('imdb_rating') or 0), reverse=True)
    recs = [c for s,c in scored[:limit]]
    return base_movie, recs

# ==========================
# STREAMLIT UI
# ==========================
st.set_page_config(page_title="Movie Recommender (Admin + Users)", layout="wide")
st.title("🎬 Movie Recommendation — Owner (Admin) & Users (Clients)")

# test DB connection early
ok, err = try_connect()
if not ok:
    st.error("Cannot connect to database. Check SERVER/DATABASE/DRIVER and that SQL Server is running.")
    st.code(f"Connection error: {err}")
    st.stop()

# ensure tables exist
ensure_tables()

# sidebar environment info
st.sidebar.markdown("### Configuration")
st.sidebar.write("DB:", f"`{DATABASE}`")
st.sidebar.write("Server:", SERVER)
st.sidebar.write("Driver:", DRIVER)
st.sidebar.markdown("---")

role = st.sidebar.selectbox("I am a", ["Visitor / User", "Owner (Admin)"])

# ---------------------------
# OWNER (ADMIN)
# ---------------------------
if role == "Owner (Admin)":
    st.sidebar.subheader("Admin login")
    admin_user = st.sidebar.text_input("Admin username")
    admin_pass = st.sidebar.text_input("Admin password", type="password")
    if st.sidebar.button("Login as Admin"):
        if admin_user == ADMIN_USERNAME and hash_password(admin_pass) == ADMIN_PASSWORD_HASH:
            st.session_state['is_admin'] = True
            st.sidebar.success("Admin authenticated")
        else:
            st.session_state['is_admin'] = False
            st.sidebar.error("Invalid admin credentials")

    if st.session_state.get('is_admin'):
        st.header("👑 Admin Dashboard")
        admin_menu = st.sidebar.selectbox("Admin actions", ["View Movies", "Add Movie", "Bulk Insert", "Update Movie", "Delete Movie", "View Search Logs", "Health Check"])
        # View Movies
        if admin_menu == "View Movies":
            st.subheader("All Movies (admin view)")
            try:
                df = df_all_movies()
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to fetch movies: {e}")

        # Add Movie
        elif admin_menu == "Add Movie":
            st.subheader("Add a new movie")
            with st.form("admin_add"):
                t = st.text_input("Title")
                yr = st.number_input("Release Year", min_value=1800, max_value=2100, value=2020)
                g = st.text_input("Genre (comma separated)")
                d = st.text_input("Director")
                r = st.number_input("IMDb Rating", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
                lang = st.text_input("Language")
                dur = st.number_input("Duration (minutes)", min_value=1, max_value=1000, value=120)
                submitted = st.form_submit_button("Add movie")
                if submitted:
                    try:
                        admin_insert_movie(title=t, release_year=int(yr), genre=g, director=d, rating=float(r), language=lang, duration=int(dur))
                        st.success("Movie added")
                    except Exception as e:
                        st.error(f"Insert failed: {e}")

        # Bulk Insert
        elif admin_menu == "Bulk Insert":
            st.subheader("Bulk insert sample movies")
            st.write("Use once to populate demo data.")
            if st.button("Insert demo movies"):
                demo = [
                    ('Avatar', 2009, 'Sci-Fi', 'James Cameron', 7.8, 'English', 162),
                    ('Titanic', 1997, 'Romance, Drama', 'James Cameron', 7.9, 'English', 195),
                    ('Inception', 2010, 'Sci-Fi', 'Christopher Nolan', 8.8, 'English', 148),
                    ('Interstellar', 2014, 'Sci-Fi', 'Christopher Nolan', 8.6, 'English', 169),
                    ('The Dark Knight', 2008, 'Action', 'Christopher Nolan', 9.0, 'English', 152)
                ]
                try:
                    admin_bulk_insert(demo)
                    st.success("Demo data inserted.")
                except Exception as e:
                    st.error(f"Bulk insert error: {e}")

        # Update Movie
        elif admin_menu == "Update Movie":
            st.subheader("Update movie details")
            df = df_all_movies()
            if df.empty:
                st.info("No movies to update.")
            else:
                options = df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist()
                sel = st.selectbox("Select movie", options)
                movie_id = int(sel.split(" - ")[0])
                row = df[df['movie_id'] == movie_id].iloc[0]
                new_title = st.text_input("Title", value=row['title'])
                new_genre = st.text_input("Genre", value=row['genre'])
                new_rating = st.number_input("IMDb rating", value=float(row['imdb_rating']) if row['imdb_rating'] else 0.0, step=0.1)
                if st.button("Update"):
                    try:
                        admin_update_movie_field(movie_id=movie_id, field="title", value=new_title)
                        admin_update_movie_field(movie_id=movie_id, field="genre", value=new_genre)
                        admin_update_movie_field(movie_id=movie_id, field="imdb_rating", value=float(new_rating))
                        st.success("Updated")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

        # Delete Movie
        elif admin_menu == "Delete Movie":
            st.subheader("Delete a movie")
            df = df_all_movies()
            if df.empty:
                st.info("No movies to delete.")
            else:
                options = df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist()
                sel = st.selectbox("Select movie to delete", options)
                movie_id = int(sel.split(" - ")[0])
                if st.button("Delete"):
                    try:
                        admin_delete_movie(movie_id=movie_id)
                        st.success("Deleted")
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

        # View Search Logs
        elif admin_menu == "View Search Logs":
            st.subheader("Search history (all users)")
            try:
                cnxn, cursor = connect()
                df_logs = pd.read_sql("SELECT sh.id, sh.user_id, u.username, sh.movie_title, sh.search_time FROM dbo.search_history sh LEFT JOIN dbo.users u ON sh.user_id = u.user_id ORDER BY sh.search_time DESC", cnxn)
                st.dataframe(df_logs, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to fetch logs: {e}")
            finally:
                try:
                    cnxn.close()
                except:
                    pass

        elif admin_menu == "Health Check":
            st.subheader("Health & info")
            st.write("DB connection OK ✅")
            st.write("Total movies:", len(df_all_movies()))
            try:
                cnxn, cursor = connect()
                cursor.execute("SELECT COUNT(*) FROM dbo.users")
                users_count = cursor.fetchone()[0]
                cnxn.close()
                st.write("Total users:", users_count)
            except Exception as e:
                st.write("Could not count users:", e)

    else:
        st.info("Please login as admin using the sidebar (default admin credentials are set in the app).")

# ---------------------------
# VISITOR / USER Section
# ---------------------------
else:
    st.header("👤 User Panel")
    user_col1, user_col2 = st.columns(2)
    with user_col1:
        st.subheader("Register")
        reg_user = st.text_input("Choose username", key="reg_user")
        reg_pass = st.text_input("Choose password", type="password", key="reg_pass")
        if st.button("Register"):
            if not reg_user or not reg_pass:
                st.error("Please provide username and password")
            else:
                ok, msg = user_register(reg_user.strip(), reg_pass)
                if ok:
                    st.success(msg + " — now login from the Login area")
                else:
                    st.error(msg)

    with user_col2:
        st.subheader("Login")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            ok, user_id = user_login(login_user.strip(), login_pass)
            if ok:
                st.success("Login successful")
                st.session_state['user_id'] = user_id
                st.session_state['username'] = login_user.strip()
            else:
                st.error("Invalid credentials")

    # If logged in show user features
    if st.session_state.get('user_id'):
        st.markdown(f"### Welcome, **{st.session_state.get('username')}**")
        user_menu = st.selectbox("Choose action", ["Search Movies", "Recommendations", "My Search History", "Profile / Logout"])

        # Search movies
        if user_menu == "Search Movies":
            q = st.text_input("Search title (partial / full)")
            if st.button("Search"):
                try:
                    results = find_movie_by_title(q)
                    if results:
                        df_res = pd.DataFrame(results)
                        st.dataframe(df_res, use_container_width=True)
                        save_search_history(st.session_state['user_id'], q)
                        st.success("Search saved to history")
                        top = df_res.iloc[0]
                        st.markdown("**Top match quick facts:**")
                        st.write(f"**{top['title']}** — {top['release_year']} — {top['genre']} — Director: {top['director']} — ⭐ {top['imdb_rating']}")
                        st.info("Tip: try 'Recommendations' for similar movies.")
                    else:
                        st.warning("No movies found")
                except Exception as e:
                    st.error(f"Search failed: {e}")

        # Recommendations
        elif user_menu == "Recommendations":
            st.write("Type a base title and get content-based recommendations.")
            base = st.text_input("Base movie title (partial / full)")
            topn = st.number_input("How many recommendations?", min_value=1, max_value=20, value=5)
            if st.button("Get Recommendations"):
                try:
                    df = df_all_movies()
                    base_mov, recs = recommend_similar_from_df(df, base, limit=int(topn))
                    if base_mov is None:
                        st.warning("No base movie found")
                    else:
                        save_search_history(st.session_state['user_id'], base)
                        st.subheader("Base movie")
                        st.write(f"**{base_mov['title']}** — {base_mov['genre']} — {base_mov['director']} — ⭐ {base_mov['imdb_rating']}")
                        st.subheader("Recommended")
                        st.table(pd.DataFrame(recs))
                except Exception as e:
                    st.error(f"Recommendation failed: {e}")

        # Search history
        elif user_menu == "My Search History":
            rows = get_user_history(st.session_state['user_id'])
            if rows:
                dfh = pd.DataFrame(rows, columns=["movie_title","search_time"])
                st.dataframe(dfh)
            else:
                st.info("No search history yet.")

        # Profile / Logout
        elif user_menu == "Profile / Logout":
            st.write(f"Username: **{st.session_state.get('username')}**")
            if st.button("Logout"):
                st.session_state.pop('user_id', None)
                st.session_state.pop('username', None)
                st.success("Logged out")

    else:
        st.info("Register or login to use search & recommendations.")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("App ready — edit SERVER/DATABASE at top of app.py if needed.")
