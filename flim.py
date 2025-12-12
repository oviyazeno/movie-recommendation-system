# app.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import os
import datetime
import hashlib
import base64
import binascii

# ---------- CONFIG ----------
MOVIES_FILE = "movies.csv"   # should have: movie_id,title,release_year,genre,director,imdb_rating,language,duration_minutes,created_at
USERS_FILE = "users.csv"     # should have: user_id,username,password_hash

# ---------- UTIL: robust CSV loaders ----------
def load_movies():
    """
    Loads movies.csv. If missing, creates with correct headers.
    If present but headerless, will assign expected headers.
    """
    expected = ["movie_id","title","release_year","genre","director","imdb_rating","language","duration_minutes","created_at"]
    if not os.path.exists(MOVIES_FILE):
        pd.DataFrame(columns=expected).to_csv(MOVIES_FILE, index=False)
    try:
        df = pd.read_csv(MOVIES_FILE)
        # fix headerless exports
        if list(df.columns) != expected:
            # try reading headerless with expected columns
            df = pd.read_csv(MOVIES_FILE, header=None, names=expected)
    except Exception:
        df = pd.DataFrame(columns=expected)
    # ensure types
    if not df.empty:
        # convert movie_id -> int when possible
        try:
            df['movie_id'] = pd.to_numeric(df['movie_id'], errors='coerce').fillna(0).astype(int)
        except Exception:
            pass
    return df

def save_movies(df):
    df.to_csv(MOVIES_FILE, index=False)

def load_users():
    """
    Loads users.csv. If missing, creates with headers.
    If present but headerless, assigns expected columns.
    Expected columns: user_id,username,password_hash
    """
    expected = ["user_id","username","password_hash"]
    if not os.path.exists(USERS_FILE):
        # create default admin row with plain password 'admin123' (will be converted to hash on first login or when create_user uses hashing)
        pd.DataFrame([{"user_id":1,"username":"admin","password_hash":"admin123"}]).to_csv(USERS_FILE,index=False)
    try:
        df = pd.read_csv(USERS_FILE)
        if list(df.columns) != expected:
            # try reading headerless with expected names
            df = pd.read_csv(USERS_FILE, header=None, names=expected)
    except Exception:
        df = pd.DataFrame(columns=expected)
    # normalize types
    if 'user_id' in df.columns and not df.empty:
        try:
            df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce').fillna(0).astype(int)
        except Exception:
            pass
    return df

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

# ---------- Password verification helpers ----------
def verify_scrypt_hash(stored_hash: str, password: str) -> bool:
    """
    Support for scrypt-style stored hashes like:
    scrypt:32768:8:1$<salt_b64_or_raw>$<hexdigest>
    This function will parse and verify if possible.
    If format doesn't match, returns False.
    """
    try:
        if not stored_hash.startswith("scrypt:"):
            return False
        # format: scrypt:N:r:p$SALT$HEX
        parts = stored_hash.split("$")
        if len(parts) < 3:
            return False
        prefix = parts[0]  # e.g. "scrypt:32768:8:1"
        salt_part = parts[1]
        hexhash = parts[2]

        # parse params
        _, params = prefix.split("scrypt:", 1)
        n_str, r_str, p_str = params.split(":")
        n = int(n_str)
        r = int(r_str)
        p = int(p_str)

        # try decode salt: it might be base64 or raw ascii
        salt = None
        try:
            salt = base64.b64decode(salt_part)
        except Exception:
            salt = salt_part.encode()

        dklen = len(hexhash) // 2
        # compute scrypt derived key
        derived = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=dklen)
        return binascii.hexlify(derived).decode() == hexhash.lower()
    except Exception:
        return False

def try_check_password(stored_hash: str, password: str) -> bool:
    """
    Try to validate password against stored_hash.
    Supports:
      - werkzeug pbkdf2 sha256 (check_password_hash)
      - scrypt:... custom formats (verify_scrypt_hash)
      - plain text stored password (direct equality) -> in that case, the caller may choose to replace with werkzeug hash
    Returns True if password matches, False otherwise.
    """
    if pd.isna(stored_hash):
        return False
    # 1) try werkzeug
    try:
        if stored_hash.startswith("$pbkdf2-sha256$") or stored_hash.startswith("pbkdf2:") or stored_hash.count('$')>2:
            # Common pbkdf2/werkzeug forms
            try:
                return check_password_hash(stored_hash, password)
            except Exception:
                pass
    except Exception:
        pass

    # 2) try scrypt custom verifier
    try:
        if stored_hash.startswith("scrypt:"):
            return verify_scrypt_hash(stored_hash, password)
    except Exception:
        pass

    # 3) direct equality (plain-text stored password) — allow it, but caller should upgrade hash after successful login
    try:
        if stored_hash == password:
            return True
    except Exception:
        pass

    # 4) fallback: try werkzeug check anyway (in case other formats)
    try:
        return check_password_hash(stored_hash, password)
    except Exception:
        return False

# ---------- Auth functions ----------
def create_user(username: str, password: str):
    df = load_users()
    if username in df['username'].values:
        raise ValueError("Username already exists")
    next_id = int(df['user_id'].max()) + 1 if not df.empty else 1
    hashed = generate_password_hash(password)
    new = pd.DataFrame([{"user_id": next_id, "username": username, "password_hash": hashed}])
    df = pd.concat([df, new], ignore_index=True)
    save_users(df)

def authenticate_user(username: str, password: str):
    """
    Returns role string: 'admin' or 'user' on success, or None on failure.
    Admin detection: username == 'admin' (case-insensitive)
    On plain-text stored password success, upgrades stored value to werkzeug hashed password.
    """
    df = load_users()
    if 'username' not in df.columns or 'password_hash' not in df.columns:
        return None
    user_row = df[df['username'] == username]
    if user_row.empty:
        return None
    stored = str(user_row.iloc[0]['password_hash'])
    ok = try_check_password(stored, password)
    if not ok:
        return None

    # If stored was plaintext (equal to password), upgrade to werkzeug hash
    # or if stored was some unsupported form but we validated via direct equality earlier
    # We'll detect by checking whether check_password_hash works now; if not, replace.
    try:
        # If stored is already a werkzeug-compatible hash, this returns True
        check_password_hash(stored, password)
        is_werkzeug = True
    except Exception:
        is_werkzeug = False
    # If not werkzeug-format but we validated (possibly plaintext), upgrade to hashed
    if not is_werkzeug:
        try:
            df.loc[df['username'] == username, 'password_hash'] = generate_password_hash(password)
            save_users(df)
        except Exception:
            pass

    return "admin" if username.lower() == "admin" else "user"

# ---------- Movie CRUD ----------
def add_movie(title, year, genre, director, rating, language, duration):
    df = load_movies()
    new_id = int(df['movie_id'].max()) + 1 if not df.empty else 1
    created_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    new = pd.DataFrame([{
        "movie_id": new_id,
        "title": title,
        "release_year": int(year) if year else "",
        "genre": genre,
        "director": director,
        "imdb_rating": float(rating) if rating != "" else "",
        "language": language,
        "duration_minutes": int(duration) if duration else "",
        "created_at": created_at
    }])
    df = pd.concat([df, new], ignore_index=True)
    save_movies(df)

def update_movie(movie_id, title=None, year=None, genre=None, director=None, rating=None, language=None, duration=None):
    df = load_movies()
    if int(movie_id) not in df['movie_id'].values:
        raise ValueError("Movie not found")
    if title is not None: df.loc[df['movie_id'] == int(movie_id), 'title'] = title
    if year is not None: df.loc[df['movie_id'] == int(movie_id), 'release_year'] = int(year)
    if genre is not None: df.loc[df['movie_id'] == int(movie_id), 'genre'] = genre
    if director is not None: df.loc[df['movie_id'] == int(movie_id), 'director'] = director
    if rating is not None: df.loc[df['movie_id'] == int(movie_id), 'imdb_rating'] = float(rating)
    if language is not None: df.loc[df['movie_id'] == int(movie_id), 'language'] = language
    if duration is not None: df.loc[df['movie_id'] == int(movie_id), 'duration_minutes'] = int(duration)
    save_movies(df)

def delete_movie(movie_id):
    df = load_movies()
    df = df[df['movie_id'] != int(movie_id)]
    save_movies(df)

# ---------- Recommendation ----------
def get_recommendations(df, base_title, topn=5):
    if df.empty or not base_title or str(base_title).strip() == "":
        return pd.DataFrame()
    df2 = df.copy()
    # combine text
    df2['combined'] = df2['genre'].fillna('') + " " + df2['director'].fillna('')
    vec = TfidfVectorizer(stop_words='english')
    try:
        tfidf = vec.fit_transform(df2['combined'])
    except Exception:
        return pd.DataFrame()
    matches = df2[df2['title'].str.contains(base_title, case=False, na=False)]
    if matches.empty:
        return pd.DataFrame()
    base_idx = matches.index[0]
    cos_sim = linear_kernel(tfidf, tfidf)
    sim_scores = list(enumerate(cos_sim[base_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1: topn+1]
    indices = [i[0] for i in sim_scores]
    return df2.iloc[indices][['movie_id','title','genre','imdb_rating']]

# ---------- Logout helper ----------
def safe_logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.success("Logged out.")
    try:
        st.experimental_rerun()
    except Exception:
        st.stop()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="MovieDb (Admin + Users)", layout="wide")
st.title("🎬 MovieDb — Admin & User Panel")

# initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

menu = st.sidebar.selectbox("Choose an action", ["Signup","Login"])

# ---------- Signup ----------
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
                st.success("User created. Now login from Login menu")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# ---------- Login ----------
elif menu == "Login":
    if not st.session_state.logged_in:
        st.header("🔐 Login")
        user = st.text_input("Username", key="login_user")
        pwd = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            role = authenticate_user(user, pwd)
            if role:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = role
                st.success(f"Welcome {user} ({role})")
            else:
                st.error("Invalid username or password")

    # logged in area
    if st.session_state.logged_in:
        df = load_movies()
        # ADMIN
        if st.session_state.role == "admin":
            st.subheader("👑 Admin Dashboard")
            admin_menu = st.selectbox("Admin actions",["Home","Add Movie","Update Movie","Delete Movie","Filter Movies","Recommendations","Logout"])
            if admin_menu=="Home":
                st.dataframe(df,use_container_width=True)
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
                        try:
                            add_movie(t.strip(), yr, g.strip(), d.strip(), r, lang.strip(), dur)
                            st.success("Movie added")
                        except Exception as e:
                            st.error(f"Add movie failed: {e}")
            elif admin_menu=="Update Movie":
                if df.empty:
                    st.warning("No movies to update.")
                else:
                    # safe selection list
                    try:
                        sel_list = df.apply(lambda r: f"{int(r['movie_id'])} - {r['title']}", axis=1).tolist()
                    except Exception:
                        sel_list = df['title'].astype(str).tolist()
                    sel = st.selectbox("Select movie", sel_list)
                    # parse id if present
                    try:
                        movie_id = int(str(sel).split(" - ")[0])
                    except Exception:
                        # fallback: pick by title
                        movie_id = int(df[df['title']==sel].iloc[0]['movie_id'])
                    row = df[df['movie_id']==movie_id].iloc[0]
                    new_title = st.text_input("Title", value=row['title'])
                    new_year = st.number_input("Year",1800,2100,int(row.get('release_year',2020)))
                    new_genre = st.text_input("Genre", value=row.get('genre',"") or "")
                    new_director = st.text_input("Director", value=row.get('director',"") or "")
                    new_rating = st.number_input("Rating", 0.0, 10.0, float(row.get('imdb_rating',0.0)), step=0.1)
                    new_lang = st.text_input("Language", value=row.get('language',"") or "")
                    new_dur = st.number_input("Duration (min)",1,1000,int(row.get('duration_minutes',0)))
                    if st.button("Update"):
                        try:
                            update_movie(movie_id, title=new_title, year=new_year, genre=new_genre, director=new_director, rating=new_rating, language=new_lang, duration=new_dur)
                            st.success("Movie updated")
                        except Exception as e:
                            st.error(f"Update failed: {e}")
            elif admin_menu=="Delete Movie":
                if df.empty:
                    st.warning("No movies to delete.")
                else:
                    try:
                        sel_list = df.apply(lambda r: f"{int(r['movie_id'])} - {r['title']}", axis=1).tolist()
                    except Exception:
                        sel_list = df['title'].astype(str).tolist()
                    sel = st.selectbox("Select movie to delete", sel_list)
                    try:
                        movie_id = int(str(sel).split(" - ")[0])
                    except Exception:
                        movie_id = int(df[df['title']==sel].iloc[0]['movie_id'])
                    if st.button("Delete Movie"):
                        try:
                            delete_movie(movie_id)
                            st.success("Movie deleted")
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
            elif admin_menu=="Filter Movies":
                if df.empty:
                    st.info("No movies yet.")
                else:
                    genre = st.selectbox("Genre", ["All"] + sorted(df['genre'].dropna().unique()))
                    language = st.selectbox("Language", ["All"] + sorted(df['language'].dropna().unique()))
                    rating = st.slider("Minimum rating",1.0,10.0,5.0)
                    filtered = df[((df['genre']==genre)|(genre=="All")) & ((df['language']==language)|(language=="All")) & (df['imdb_rating']>=rating)]
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

        # USER
        else:
            st.subheader("👤 User Dashboard")
            user_menu = st.selectbox("Choose", ["Home","Filter Movies","Recommendations","Logout"])
            df = load_movies()
            if user_menu == "Home":
                st.dataframe(df,use_container_width=True)
            elif user_menu == "Filter Movies":
                if df.empty:
                    st.info("No movies yet.")
                else:
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
                safe_logout()

st.sidebar.markdown("---")
st.sidebar.write("Data stored in CSV files (matching your SQL export format)")
