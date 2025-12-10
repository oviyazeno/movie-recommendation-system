# app.py
import streamlit as st
import pandas as pd
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# -----------------------------
# DB CONNECTION
# -----------------------------
SERVER = "localhost"
DATABASE = "MovieDb"
DRIVER = "{ODBC Driver 17 for SQL Server}"

def get_connection():
    conn_str = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# -----------------------------
# Ensure admin exists
# -----------------------------
def ensure_admin_exists():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM dbo.users WHERE username = ?", ("admin",))
        row = cur.fetchone()
        if not row:
            hashed = generate_password_hash("admin123")
            cur.execute("INSERT INTO dbo.users (username, password_hash) VALUES (?, ?)", ("admin", hashed))
            conn.commit()
        conn.close()
    except Exception as e:
        # If users table does not exist or DB not reachable, show later as errors in UI
        print("ensure_admin_exists error:", e)

ensure_admin_exists()

# -----------------------------
# Auth / User functions
# -----------------------------
def create_user(username: str, password: str):
    conn = get_connection()
    cur = conn.cursor()
    hashed = generate_password_hash(password)
    cur.execute("INSERT INTO dbo.users (username, password_hash) VALUES (?, ?)", (username, hashed))
    conn.commit()
    conn.close()

def authenticate_user(username: str, password: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM dbo.users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        return True
    return False

# -----------------------------
# Movies helpers
# -----------------------------
def fetch_movies_df():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM dbo.movies", conn)
    finally:
        conn.close()
    return df

def add_movie_sql(title, year, genre, director, rating, language, duration):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO dbo.movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, year or None, genre or None, director or None, rating or None, language or None, duration or None))
    conn.commit()
    conn.close()

def update_movie_sql(movie_id, title=None, genre=None, rating=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT movie_id FROM dbo.movies WHERE movie_id = ?", (movie_id,))
    if not cur.fetchone():
        conn.close()
        raise ValueError("Movie not found")
    # update only provided fields
    parts = []
    params = []
    if title is not None:
        parts.append("title = ?"); params.append(title)
    if genre is not None:
        parts.append("genre = ?"); params.append(genre)
    if rating is not None:
        parts.append("imdb_rating = ?"); params.append(rating)
    if parts:
        q = "UPDATE dbo.movies SET " + ", ".join(parts) + " WHERE movie_id = ?"
        params.append(movie_id)
        cur.execute(q, tuple(params))
        conn.commit()
    conn.close()

def delete_movie_sql(movie_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.movies WHERE movie_id = ?", (movie_id,))
    conn.commit()
    conn.close()

# -----------------------------
# ALTER TABLE - Add Column (safe)
# -----------------------------
ALLOWED_TYPES = {
    "VARCHAR(100)": "VARCHAR(100)",
    "VARCHAR(255)": "VARCHAR(255)",
    "INT": "INT",
    "DECIMAL(3,1)": "DECIMAL(3,1)",
    "DATETIME": "DATETIME"
}

def add_column_to_movies(col_name: str, col_type: str, allow_nulls: bool = True):
    # basic validation of column name: letters, numbers, underscore only
    import re
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", col_name):
        raise ValueError("Invalid column name. Use letters, numbers and underscore only (no spaces).")
    if col_type not in ALLOWED_TYPES:
        raise ValueError("Invalid column type.")
    sql_type = ALLOWED_TYPES[col_type]
    null_clause = "NULL" if allow_nulls else "NOT NULL"
    q = f"ALTER TABLE dbo.movies ADD [{col_name}] {sql_type} {null_clause}"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q)
    conn.commit()
    conn.close()

# -----------------------------
# Recommendation helper
# -----------------------------
def get_recommendations(df: pd.DataFrame, base_title: str, topn: int = 5):
    if df.empty or base_title is None or base_title.strip() == "":
        return pd.DataFrame()
    # combine fields (safe for NaNs)
    df = df.copy()
    df['combined'] = df['genre'].fillna('') + " " + df['director'].fillna('')
    vec = TfidfVectorizer(stop_words='english')
    tfidf = vec.fit_transform(df['combined'])
    # find index of base (first match case-insensitive)
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
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MovieApp (Admin + Users)", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None  # 'admin' or 'user'

menu = st.sidebar.selectbox("Choose an action", ["Signup", "User Login", "Admin Login"])

# -----------------------------
# SIGNUP
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
# USER LOGIN
# -----------------------------
elif menu == "User Login":
    if not st.session_state.logged_in or st.session_state.role != "user":
        st.header("🔐 User Login")
        user = st.text_input("Username", key="user_login_user")
        pwd = st.text_input("Password", type="password", key="user_login_pass")
        if st.button("Login as User"):
            try:
                if authenticate_user(user, pwd):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.role = "user"
                    st.success(f"Welcome {user} (user).")
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.error(f"Login error: {e}")
    else:
        st.success(f"Already logged in as {st.session_state.username}")
    # If logged in as user, show user dashboard
    if st.session_state.logged_in and st.session_state.role == "user":
        st.subheader("👤 User Dashboard")
        user_menu = st.selectbox("Choose", ["Home", "Filter Movies", "Recommendations", "Logout"])
        if user_menu == "Home":
            st.write("All movies:")
            try:
                df = fetch_movies_df()
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to load movies: {e}")

        elif user_menu == "Filter Movies":
            try:
                df = fetch_movies_df()
                genre = st.selectbox("Genre", ["All"] + sorted(df['genre'].dropna().unique().tolist()))
                language = st.selectbox("Language", ["All"] + sorted(df['language'].dropna().unique().tolist()))
                rating = st.slider("Minimum rating", 1.0, 10.0, 5.0)
                filtered = df[
                    ((df['genre'] == genre) | (genre == "All")) &
                    ((df['language'] == language) | (language == "All")) &
                    (df['imdb_rating'] >= rating)
                ]
                st.dataframe(filtered, use_container_width=True)
            except Exception as e:
                st.error(f"Filter error: {e}")

        elif user_menu == "Recommendations":
            try:
                df = fetch_movies_df()
                base = st.text_input("Type movie title (partial or full) for recommendations")
                topn = st.number_input("How many recommendations?", min_value=1, max_value=20, value=5)
                if st.button("Get recommendations"):
                    recs = get_recommendations(df, base, topn)
                    if recs.empty:
                        st.warning("No recommendations found (check title).")
                    else:
                        st.dataframe(recs, use_container_width=True)
            except Exception as e:
                st.error(f"Recommendation error: {e}")

        elif user_menu == "Logout":
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.success("Logged out successfully.")
            st.experimental_rerun()

# -----------------------------
# ADMIN LOGIN
# -----------------------------
elif menu == "Admin Login":
    # Admin login form
    if not st.session_state.logged_in or st.session_state.role != "admin":
        st.header("🔐 Admin Login")
        admin_user = st.text_input("Admin username", key="admin_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            try:
                if authenticate_user(admin_user, admin_pass) and admin_user.lower() == "admin":
                    st.session_state.logged_in = True
                    st.session_state.username = admin_user
                    st.session_state.role = "admin"
                    st.success("Admin login successful.")
                else:
                    st.error("Invalid admin credentials.")
            except Exception as e:
                st.error(f"Admin login error: {e}")
    # Admin dashboard
    if st.session_state.logged_in and st.session_state.role == "admin":
        st.subheader("👑 Admin Dashboard")
        admin_menu = st.selectbox("Admin actions", [
            "Home",
            "Add Movie",
            "Update Movie",
            "Delete Movie",
            "Alter Table - Add Column",
            "Filter Movies",
            "Recommendations",
            "Logout"
        ])

        # Home
        if admin_menu == "Home":
            try:
                df = fetch_movies_df()
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading movies: {e}")

        # Add Movie
        elif admin_menu == "Add Movie":
            st.markdown("### ➕ Add Movie")
            with st.form("add_movie_form", clear_on_submit=True):
                t = st.text_input("Title")
                yr = st.number_input("Release Year", min_value=1800, max_value=2100, value=2020)
                g = st.text_input("Genre")
                d = st.text_input("Director")
                r = st.number_input("IMDb Rating", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
                lang = st.text_input("Language")
                dur = st.number_input("Duration (minutes)", min_value=1, max_value=1000, value=120)
                submitted = st.form_submit_button("Add Movie")
                if submitted:
                    try:
                        add_movie_sql(t.strip(), int(yr), g.strip() or None, d.strip() or None, float(r), lang.strip() or None, int(dur))
                        st.success("Movie added.")
                    except Exception as e:
                        st.error(f"Add movie failed: {e}")

        # Update Movie
        elif admin_menu == "Update Movie":
            st.markdown("### ✏️ Update Movie")
            try:
                df = fetch_movies_df()
                if df.empty:
                    st.info("No movies available to update.")
                else:
                    sel = st.selectbox("Select movie", df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist())
                    movie_id = int(sel.split(" - ")[0])
                    row = df[df['movie_id'] == movie_id].iloc[0]
                    new_title = st.text_input("Title", value=row['title'])
                    new_genre = st.text_input("Genre", value=row['genre'] or "")
                    new_rating = st.number_input("IMDb rating", value=float(row['imdb_rating'] or 0.0), step=0.1)
                    if st.button("Update"):
                        try:
                            update_movie_sql(movie_id, title=new_title.strip(), genre=new_genre.strip(), rating=float(new_rating))
                            st.success("Updated successfully.")
                        except Exception as e:
                            st.error(f"Update failed: {e}")
            except Exception as e:
                st.error(f"Load movies failed: {e}")

        # Delete Movie
        elif admin_menu == "Delete Movie":
            st.markdown("### 🗑 Delete Movie")
            try:
                df = fetch_movies_df()
                if df.empty:
                    st.info("No movies to delete.")
                else:
                    sel = st.selectbox("Select movie to delete", df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist())
                    movie_id = int(sel.split(" - ")[0])
                    if st.button("Delete Movie"):
                        try:
                            delete_movie_sql(movie_id)
                            st.success("Movie deleted.")
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
            except Exception as e:
                st.error(f"Load movies failed: {e}")

        # ALTER TABLE - Add Column
        elif admin_menu == "Alter Table - Add Column":
            st.markdown("### ⚙️ Add Column to movies (safe choices)")
            st.info("Column name must be letters/numbers/underscore (no spaces). Choose a datatype from allowed list.")
            col_name = st.text_input("Column name (e.g., country)")
            col_type = st.selectbox("Column type", list(ALLOWED_TYPES.keys()))
            allow_nulls = st.checkbox("Allow NULLs", value=True)
            if st.button("Add Column"):
                try:
                    add_column_to_movies(col_name.strip(), col_type, allow_nulls)
                    st.success(f"Column '{col_name}' added to movies.")
                except Exception as e:
                    st.error(f"Add column failed: {e}")

        # Filter Movies (admin)
        elif admin_menu == "Filter Movies":
            try:
                df = fetch_movies_df()
                genre = st.selectbox("Genre", ["All"] + sorted(df['genre'].dropna().unique().tolist()))
                language = st.selectbox("Language", ["All"] + sorted(df['language'].dropna().unique().tolist()))
                rating = st.slider("Minimum rating", 1.0, 10.0, 5.0)
                filtered = df[
                    ((df['genre'] == genre) | (genre == "All")) &
                    ((df['language'] == language) | (language == "All")) &
                    (df['imdb_rating'] >= rating)
                ]
                st.dataframe(filtered, use_container_width=True)
            except Exception as e:
                st.error(f"Filter error: {e}")

        # Recommendations (admin)
        elif admin_menu == "Recommendations":
            try:
                df = fetch_movies_df()
                base = st.text_input("Type movie title for recommendations")
                topn = st.number_input("Top N", min_value=1, max_value=20, value=5)
                if st.button("Get"):
                    recs = get_recommendations(df, base, topn)
                    if recs.empty:
                        st.warning("No recommendations found.")
                    else:
                        st.dataframe(recs, use_container_width=True)
            except Exception as e:
                st.error(f"Recommendation error: {e}")

        # Logout
        elif admin_menu == "Logout":
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.success("Logged out.")
            st.experimental_rerun()

# -----------------------------
# Footer / DB info
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.write("Database:", f"`{DATABASE}`")
st.sidebar.write("Server:", SERVER)
