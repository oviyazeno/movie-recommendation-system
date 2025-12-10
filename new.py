# import streamlit as st
# import pandas as pd
# import pyodbc
#
#
# # -----------------------------
# # DATABASE CONNECTION
# # -----------------------------
# def get_connection():
#     server = 'localhost'
#     database = 'MovieDb'
#     driver = '{ODBC Driver 17 for SQL Server}'
#     return pyodbc.connect(
#         f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
#     )
#
#
# # -----------------------------
# # FETCH ALL MOVIES
# # -----------------------------
# def fetch_movies():
#     conn = get_connection()
#     df = pd.read_sql("SELECT * FROM movies", conn)
#     conn.close()
#     return df
#
#
# # -----------------------------
# # STREAMLIT UI
# # -----------------------------
# st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# st.write("Your full visual project with CRUD + Filters + Recommendations")
#
# menu = ["Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations"]
# choice = st.sidebar.selectbox("Menu", menu)
#
# # ======================================================
# # 1️⃣ HOME
# # ======================================================
# if choice == "Home":
#     st.header("📌 All Movies in Database")
#     df = fetch_movies()
#     st.dataframe(df, use_container_width=True)
#
#
# # ======================================================
# # 2️⃣ ADD MOVIE
# # ======================================================
# elif choice == "Add Movie":
#     st.header("➕ Add New Movie")
#
#     title = st.text_input("Movie Title")
#     year = st.number_input("Release Year", min_value=1900, max_value=2100)
#     genre = st.text_input("Genre")
#     director = st.text_input("Director")
#     rating = st.number_input("IMDB Rating", min_value=1.0, max_value=10.0, step=0.1)
#     language = st.text_input("Language")
#     duration = st.number_input("Duration (Minutes)", min_value=30, max_value=300)
#
#     if st.button("Add Movie"):
#         conn = get_connection()
#         cursor = conn.cursor()
#
#         cursor.execute("""
#             INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, (title, year, genre, director, rating, language, duration))
#
#         conn.commit()
#         conn.close()
#         st.success("Movie Added Successfully!")
#
#
# # ======================================================
# # 3️⃣ UPDATE MOVIE
# # ======================================================
# elif choice == "Update Movie":
#     st.header("✏️ Update Movie Details")
#
#     df = fetch_movies()
#     movie_list = df['title'].tolist()
#
#     selected_movie = st.selectbox("Choose Movie to Update", movie_list)
#
#     movie_data = df[df['title'] == selected_movie].iloc[0]
#
#     new_title = st.text_input("Title", movie_data['title'])
#     new_genre = st.text_input("Genre", movie_data['genre'])
#     new_rating = st.number_input("Rating", value=float(movie_data['imdb_rating']), step=0.1)
#
#     if st.button("Update Movie"):
#         conn = get_connection()
#         cursor = conn.cursor()
#         cursor.execute("""
#             UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
#         """, (new_title, new_genre, new_rating, movie_data['movie_id']))
#
#         conn.commit()
#         conn.close()
#         st.success("Movie Updated Successfully!")
#
#
# # ======================================================
# # 4️⃣ DELETE MOVIE
# # ======================================================
# elif choice == "Delete Movie":
#     st.header("🗑️ Delete Movie")
#
#     df = fetch_movies()
#     movie_list = df['title'].tolist()
#
#     selected_movie = st.selectbox("Select movie to delete", movie_list)
#     movie_id = df[df['title'] == selected_movie]['movie_id'].values[0]
#
#     if st.button("Delete Movie"):
#         conn = get_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
#         conn.commit()
#         conn.close()
#         st.error("Movie Deleted!")
#
#
# # ======================================================
# # 5️⃣ FILTER MOVIES
# # ======================================================
# elif choice == "Filter Movies":
#     st.header("🔍 Filter Movies by Genre / Rating / Language")
#
#     df = fetch_movies()
#
#     genre = st.selectbox("Select Genre", ["All"] + df["genre"].dropna().unique().tolist())
#     language = st.selectbox("Select Language", ["All"] + df["language"].dropna().unique().tolist())
#     rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
#
#     filtered_df = df[
#         ((df["genre"] == genre) | (genre == "All")) &
#         ((df["language"] == language) | (language == "All")) &
#         (df["imdb_rating"] >= rating)
#         ]
#
#     st.dataframe(filtered_df, use_container_width=True)
#
#
# # ======================================================
# # 6️⃣ RECOMMENDATION ENGINE
# # ======================================================
# elif choice == "Recommendations":
#     st.header("🤖 Movie Recommendations")
#
#     df = fetch_movies()
#
#     genre = st.selectbox("Select Genre You Like", df["genre"].dropna().unique())
#     min_rating = st.slider("Minimum Rating", 1.0, 10.0, 7.0)
#
#     recommended = df[(df["genre"] == genre) & (df["imdb_rating"] >= min_rating)]
#
#     if len(recommended) == 0:
#         st.warning("No recommendations found!")
#     else:
#         st.success("Recommended Movies")
#         st.dataframe(recommended, use_container_width=True)
#
# app.py
# import streamlit as st
# import pandas as pd
# import pyodbc
# import hashlib
# from typing import List, Dict
# from datetime import datetime
#
# # ============================================
# # CONFIG / DB CONNECTION
# # ============================================
# SERVER = 'localhost'
# DATABASE = 'MovieDb'
# DRIVER = '{ODBC Driver 17 for SQL Server}'
#
# CNXN_STR = f"""
# DRIVER={DRIVER};
# SERVER={SERVER};
# DATABASE={DATABASE};
# Trusted_Connection=True;
# """
#
# # Default admin credentials (change here if you want)
# ADMIN_USERNAME = "Zeno"
# ADMIN_PASSWORD = "Zeno@123"  # plain here only for initial login; app compares hashed
#
# def connect():
#     cnxn = pyodbc.connect(CNXN_STR)
#     return cnxn, cnxn.cursor()
#
# def hash_password(plain: str) -> str:
#     return hashlib.sha256(plain.encode('utf-8')).hexdigest()
#
# # ============================================
# # SCHEMA CREATION (run once if missing)
# # ============================================
# def ensure_tables():
#     cnxn, cursor = connect()
#     try:
#         # users table
#         cursor.execute("""
#         IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U'))
#         BEGIN
#             CREATE TABLE dbo.users (
#                 user_id INT IDENTITY(1,1) PRIMARY KEY,
#                 username VARCHAR(255) UNIQUE NOT NULL,
#                 password_hash VARCHAR(255) NOT NULL,
#                 created_at DATETIME DEFAULT GETDATE()
#             )
#         END
#         """)
#         # search_history table
#         cursor.execute("""
#         IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[search_history]') AND type in (N'U'))
#         BEGIN
#             CREATE TABLE dbo.search_history (
#                 id INT IDENTITY(1,1) PRIMARY KEY,
#                 user_id INT NOT NULL,
#                 movie_title VARCHAR(255) NOT NULL,
#                 search_time DATETIME DEFAULT GETDATE(),
#                 FOREIGN KEY (user_id) REFERENCES dbo.users(user_id)
#             )
#         END
#         """)
#         # movies table (if not exists) — basic schema; adapt as needed
#         cursor.execute("""
#         IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[movies]') AND type in (N'U'))
#         BEGIN
#             CREATE TABLE dbo.movies (
#                 movie_id INT IDENTITY(1,1) PRIMARY KEY,
#                 title VARCHAR(500) NOT NULL,
#                 release_year INT NULL,
#                 genre VARCHAR(255) NULL,
#                 director VARCHAR(255) NULL,
#                 imdb_rating DECIMAL(3,1) NULL,
#                 language VARCHAR(100) NULL,
#                 duration_minutes INT NULL,
#                 created_at DATETIME DEFAULT GETDATE()
#             )
#         END
#         """)
#         cnxn.commit()
#     finally:
#         cnxn.close()
#
# # ============================================
# # HELPERS: row -> dict + fetch functions
# # ============================================
# def row_to_dict(row):
#     return {
#         "movie_id": row[0],
#         "title": row[1],
#         "release_year": row[2],
#         "genre": row[3] or "",
#         "director": row[4] or "",
#         "imdb_rating": float(row[5]) if row[5] is not None else 0.0,
#         "language": row[6] or "",
#         "duration_minutes": row[7] or 0,
#         "created_at": row[8]
#     }
#
# def load_all_movies(cursor) -> List[Dict]:
#     cursor.execute("SELECT * FROM movies")
#     rows = cursor.fetchall()
#     return [row_to_dict(r) for r in rows]
#
# def df_all_movies() -> pd.DataFrame:
#     cnxn, cursor = connect()
#     try:
#         rows = load_all_movies(cursor)
#         return pd.DataFrame(rows)
#     finally:
#         cnxn.close()
#
# def find_movie_by_title(cursor, title_partial) -> List[Dict]:
#     cursor.execute("SELECT * FROM movies WHERE title LIKE ?", ('%' + title_partial + '%',))
#     rows = cursor.fetchall()
#     return [row_to_dict(r) for r in rows]
#
# # ============================================
# # ADMIN: CRUD operations
# # ============================================
# def admin_insert_movie(cursor, conn, title, release_year, genre, director, rating, language, duration):
#     cursor.execute("""
#         INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#     """, (title, release_year, genre, director, rating, language, duration))
#     conn.commit()
#
# def admin_update_movie_field(conn, cursor, movie_id, field, value):
#     query = f"UPDATE movies SET {field} = ? WHERE movie_id = ?"
#     cursor.execute(query, (value, movie_id))
#     conn.commit()
#
# def admin_delete_movie(conn, cursor, movie_id):
#     cursor.execute("DELETE FROM movies WHERE movie_id = ?", (movie_id,))
#     conn.commit()
#
# def admin_bulk_insert(conn, cursor, movies_list):
#     query = """
#         INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#     """
#     cursor.executemany(query, movies_list)
#     conn.commit()
#
# # ============================================
# # USER management & search history
# # ============================================
# def user_register(username: str, password: str) -> (bool, str):
#     cnxn, cursor = connect()
#     try:
#         password_hash = hash_password(password)
#         try:
#             cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
#             cnxn.commit()
#             return True, "Registered successfully"
#         except pyodbc.IntegrityError:
#             return False, "Username already exists"
#     finally:
#         cnxn.close()
#
# def user_login(username: str, password: str) -> (bool, int):
#     cnxn, cursor = connect()
#     try:
#         cursor.execute("SELECT user_id, password_hash FROM users WHERE username = ?", (username,))
#         res = cursor.fetchone()
#         if not res:
#             return False, None
#         user_id, stored_hash = res[0], res[1]
#         if stored_hash == hash_password(password):
#             return True, int(user_id)
#         else:
#             return False, None
#     finally:
#         cnxn.close()
#
# def save_search_history(user_id: int, movie_title: str):
#     cnxn, cursor = connect()
#     try:
#         cursor.execute("INSERT INTO search_history (user_id, movie_title) VALUES (?, ?)", (user_id, movie_title))
#         cnxn.commit()
#     finally:
#         cnxn.close()
#
# def get_user_history(user_id: int, limit: int = 50):
#     cnxn, cursor = connect()
#     try:
#         cursor.execute("SELECT movie_title, search_time FROM search_history WHERE user_id = ? ORDER BY search_time DESC", (user_id,))
#         return cursor.fetchall()
#     finally:
#         cnxn.close()
#
# # ============================================
# # RECOMMENDER (content-based)
# # ============================================
# def genre_overlap_score(base_genre, other_genre):
#     base_set = set([g.strip().lower() for g in str(base_genre).replace('/', ',').split(',') if g.strip()])
#     other_set = set([g.strip().lower() for g in str(other_genre).replace('/', ',').split(',') if g.strip()])
#     if not base_set:
#         return 0.0
#     return len(base_set.intersection(other_set)) / max(1, len(base_set))
#
# def compute_score(base_movie, candidate):
#     score = 0.0
#     if base_movie.get('director') and candidate.get('director'):
#         if base_movie['director'].strip().lower() == candidate['director'].strip().lower():
#             score += 3.0
#     score += genre_overlap_score(base_movie.get('genre',''), candidate.get('genre','')) * 2.0
#     score += (candidate.get('imdb_rating', 0) / 10.0)
#     if base_movie.get('release_year') and candidate.get('release_year'):
#         diff = candidate['release_year'] - base_movie['release_year']
#         if abs(diff) <= 5:
#             score += 0.2
#         elif abs(diff) <= 15:
#             score += 0.05
#     return score
#
# def recommend_similar_from_df(df: pd.DataFrame, base_title: str, limit=8):
#     matches = df[df['title'].str.contains(base_title, case=False, na=False)]
#     if matches.empty:
#         return None, []
#     exact = matches[matches['title'].str.lower() == base_title.strip().lower()]
#     base_row = exact.iloc[0] if not exact.empty else matches.iloc[0]
#     base_movie = base_row.to_dict()
#     candidates = df[df['movie_id'] != base_movie['movie_id']].to_dict('records')
#     scored = []
#     for c in candidates:
#         s = compute_score(base_movie, c)
#         scored.append((s, c))
#     scored.sort(key=lambda x: (x[0], x[1].get('imdb_rating',0)), reverse=True)
#     recs = [c for s,c in scored[:limit]]
#     return base_movie, recs
#
# # ============================================
# # STREAMLIT UI
# # ============================================
# st.set_page_config(page_title="Movie Recommender (Owner + Users)", layout="wide")
# st.title("🎬 Movie Recommendation — Owner (Admin) & Users (Clients)")
#
# # ensure tables exist
# ensure_tables()
#
# # Sidebar: choose role
# role = st.sidebar.selectbox("I am a", ["Visitor / User", "Owner (Admin)"])
#
# # ---------------------------
# # OWNER (ADMIN) Section
# # ---------------------------
# if role == "Owner (Admin)":
#     st.sidebar.subheader("Admin login")
#     admin_user = st.sidebar.text_input("Admin username")
#     admin_pass = st.sidebar.text_input("Admin password", type="password")
#     if st.sidebar.button("Login as Admin"):
#         if admin_user == ADMIN_USERNAME and admin_pass == ADMIN_PASSWORD:
#             st.session_state['is_admin'] = True
#             st.sidebar.success("Admin authenticated")
#         else:
#             st.session_state['is_admin'] = False
#             st.sidebar.error("Invalid admin credentials")
#
#     if st.session_state.get('is_admin'):
#         st.header("👑 Admin Dashboard")
#         admin_menu = st.sidebar.selectbox("Admin actions", ["View Movies", "Add Movie", "Bulk Insert", "Update Movie", "Delete Movie", "View Search Logs"])
#         # View Movies
#         if admin_menu == "View Movies":
#             st.subheader("All Movies (admin view)")
#             try:
#                 df = df_all_movies()
#                 st.dataframe(df, use_container_width=True)
#             except Exception as e:
#                 st.error(f"Failed to fetch movies: {e}")
#
#         # Add Movie
#         elif admin_menu == "Add Movie":
#             st.subheader("Add a new movie")
#             with st.form("admin_add"):
#                 t = st.text_input("Title")
#                 yr = st.number_input("Release Year", min_value=1800, max_value=2100, value=2020)
#                 g = st.text_input("Genre")
#                 d = st.text_input("Director")
#                 r = st.number_input("IMDb Rating", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
#                 lang = st.text_input("Language")
#                 dur = st.number_input("Duration (minutes)", min_value=1, max_value=1000, value=120)
#                 submitted = st.form_submit_button("Add movie")
#                 if submitted:
#                     try:
#                         cnxn, cursor = connect()
#                         admin_insert_movie(cursor=cursor, conn=cnxn, title=t, release_year=int(yr), genre=g, director=d, rating=float(r), language=lang, duration=int(dur))
#                         cnxn.close()
#                         st.success("Movie added")
#                     except Exception as e:
#                         st.error(f"Insert failed: {e}")
#
#         # Bulk Insert
#         elif admin_menu == "Bulk Insert":
#             st.subheader("Bulk insert sample movies")
#             st.write("Use once to populate demo data.")
#             if st.button("Insert demo movies"):
#                 demo = [
#                     ('Avatar', 2009, 'Sci-Fi', 'James Cameron', 7.8, 'English', 162),
#                     ('Titanic', 1997, 'Romance Drama', 'James Cameron', 7.9, 'English', 195),
#                     ('Inception', 2010, 'Sci-Fi', 'Christopher Nolan', 8.8, 'English', 148),
#                     ('Interstellar', 2014, 'Sci-Fi', 'Christopher Nolan', 8.6, 'English', 169),
#                     ('The Dark Knight', 2008, 'Action', 'Christopher Nolan', 9.0, 'English', 152)
#                 ]
#                 try:
#                     cnxn, cursor = connect()
#                     admin_bulk_insert(conn=cnxn, cursor=cursor, movies_list=demo)
#                     cnxn.close()
#                     st.success("Demo data inserted.")
#                 except Exception as e:
#                     st.error(f"Bulk insert error: {e}")
#
#         # Update Movie
#         elif admin_menu == "Update Movie":
#             st.subheader("Update movie details")
#             df = df_all_movies()
#             if df.empty:
#                 st.info("No movies to update.")
#             else:
#                 options = df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist()
#                 sel = st.selectbox("Select movie", options)
#                 movie_id = int(sel.split(" - ")[0])
#                 row = df[df['movie_id'] == movie_id].iloc[0]
#                 new_title = st.text_input("Title", value=row['title'])
#                 new_genre = st.text_input("Genre", value=row['genre'])
#                 new_rating = st.number_input("IMDb rating", value=float(row['imdb_rating']), step=0.1)
#                 if st.button("Update"):
#                     try:
#                         cnxn, cursor = connect()
#                         admin_update_movie_field(conn=cnxn, cursor=cursor, movie_id=movie_id, field="title", value=new_title)
#                         admin_update_movie_field(conn=cnxn, cursor=cursor, movie_id=movie_id, field="genre", value=new_genre)
#                         admin_update_movie_field(conn=cnxn, cursor=cursor, movie_id=movie_id, field="imdb_rating", value=float(new_rating))
#                         cnxn.close()
#                         st.success("Updated")
#                     except Exception as e:
#                         st.error(f"Update failed: {e}")
#
#         # Delete Movie
#         elif admin_menu == "Delete Movie":
#             st.subheader("Delete a movie")
#             df = df_all_movies()
#             if df.empty:
#                 st.info("No movies to delete.")
#             else:
#                 options = df.apply(lambda r: f"{r['movie_id']} - {r['title']}", axis=1).tolist()
#                 sel = st.selectbox("Select movie to delete", options)
#                 movie_id = int(sel.split(" - ")[0])
#                 if st.button("Delete"):
#                     try:
#                         cnxn, cursor = connect()
#                         admin_delete_movie(conn=cnxn, cursor=cursor, movie_id=movie_id)
#                         cnxn.close()
#                         st.success("Deleted")
#                     except Exception as e:
#                         st.error(f"Delete failed: {e}")
#
#         # View Search Logs
#         elif admin_menu == "View Search Logs":
#             st.subheader("Search history (all users)")
#             cnxn, cursor = connect()
#             try:
#                 df_logs = pd.read_sql("SELECT sh.id, sh.user_id, u.username, sh.movie_title, sh.search_time FROM dbo.search_history sh LEFT JOIN dbo.users u ON sh.user_id = u.user_id ORDER BY sh.search_time DESC", cnxn)
#                 st.dataframe(df_logs, use_container_width=True)
#             except Exception as e:
#                 st.error(f"Failed to fetch logs: {e}")
#             finally:
#                 cnxn.close()
#
#     else:
#         st.warning("Please login as admin using the sidebar (default admin/admin123)")
#
# # ---------------------------
# # VISITOR / USER Section
# # ---------------------------
# else:
#     st.header("👤 User Panel")
#     user_col1, user_col2 = st.columns(2)
#     with user_col1:
#         st.subheader("Register")
#         reg_user = st.text_input("Choose username", key="reg_user")
#         reg_pass = st.text_input("Choose password", type="password", key="reg_pass")
#         if st.button("Register"):
#             ok, msg = user_register(reg_user, reg_pass)
#             if ok:
#                 st.success(msg + " — now login from the Login area")
#             else:
#                 st.error(msg)
#
#     with user_col2:
#         st.subheader("Login")
#         login_user = st.text_input("Username", key="login_user")
#         login_pass = st.text_input("Password", type="password", key="login_pass")
#         if st.button("Login"):
#             ok, user_id = user_login(login_user, login_pass)
#             if ok:
#                 st.success("Login successful")
#                 st.session_state['user_id'] = user_id
#                 st.session_state['username'] = login_user
#             else:
#                 st.error("Invalid credentials")
#         user_menu = st.selectbox("Choose action", ["Search Movies", "Recommendations", "My Search History", "Profile / Logout"])
#
#         # Search movies
#         if user_menu == "Search Movies":
#             q = st.text_input("Search title (partial / full)")
#             if st.button("Search"):
#                 cnxn, cursor = connect()
#                 try:
#                     results = find_movie_by_title(cursor, q)
#                     cnxn.close()
#                     if results:
#                         df_res = pd.DataFrame(results)
#                         st.dataframe(df_res, use_container_width=True)
#                         # store search history
#                         save_search_history(st.session_state['user_id'], q)
#                         st.success(f"Search saved to history")
#                         # fun facts: show top result and quick facts
#                         top = df_res.iloc[0]
#                         st.markdown("**Top match quick facts:**")
#                         st.write(f"**{top['title']}** — {top['release_year']} — {top['genre']} — Director: {top['director']} — ⭐ {top['imdb_rating']}")
#                         st.info("Fun fact: You can click 'Recommendations' for similar movies.")
#                     else:
#                         st.warning("No movies found")
#                 except Exception as e:
#                     st.error(f"Search failed: {e}")
#
#         # Recommendations
#         elif user_menu == "Recommendations":
#             st.write("Type a base title and get content-based recommendations.")
#             base = st.text_input("Base movie title (partial / full)")
#             topn = st.number_input("How many recommendations?", min_value=1, max_value=20, value=5)
#             if st.button("Get Recommendations"):
#                 try:
#                     df = df_all_movies()
#                     base_mov, recs = recommend_similar_from_df(df, base, limit=int(topn))
#                     if base_mov is None:
#                         st.warning("No base movie found")
#                     else:
#                         save_search_history(st.session_state['user_id'], base)
#                         st.subheader("Base movie")
#                         st.write(f"**{base_mov['title']}** — {base_mov['genre']} — {base_mov['director']} — ⭐ {base_mov['imdb_rating']}")
#                         st.subheader("Recommended")
#                         st.table(pd.DataFrame(recs))
#                 except Exception as e:
#                     st.error(f"Recommendation failed: {e}")
#
#         # Search history
#         elif user_menu == "My Search History":
#             rows = get_user_history(st.session_state['user_id'])
#             if rows:
#                 dfh = pd.DataFrame(rows, columns=["movie_title","search_time"])
#                 st.dataframe(dfh)
#             else:
#                 st.info("No search history yet.")
#
#         # Profile / Logout
#         elif user_menu == "Profile / Logout":
#             st.write(f"Username: **{st.session_state.get('username')}**")
#             if st.button("Logout"):
#                 st.session_state.pop('user_id', None)
#                 st.session_state.pop('username', None)
#                 st.success("Logged out")
#
#     else:
#         st.info("Register or login to use search & recommendations.")
#
# # Footer sidebar info
# st.sidebar.markdown("---")
# st.sidebar.write("DB:", f"`{DATABASE}`")
# st.sidebar.write("Server:", SERVER)
# #
# #     # If logged in show user features
# #     if st.session_state.get('user_id'):
# #         st.markdown(f"### Welcome, **{st.session_state.get('username')}**")
#
# # import streamlit as st
# # import pandas as pd
# # import pyodbc
# # import hashlib
# # from datetime import datetime
# #
# # # ============================================
# # # DB CONNECTION
# # # ============================================
# # server = 'localhost'
# # database = 'MovieDb'
# # driver = '{ODBC Driver 17 for SQL Server}'
# #
# # def get_connection():
# #     return pyodbc.connect(
# #         f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
# #     )
# #
# # # ============================================
# # # PASSWORD HASH
# # # ============================================
# # def hash_password(password: str) -> str:
# #     return hashlib.sha256(password.encode()).hexdigest()
# #
# # # ============================================
# # # USER LOGIN FUNCTION
# # # ============================================
# # def login(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT user_id, password_hash FROM users WHERE username = ?", username)
# #     row = cursor.fetchone()
# #     conn.close()
# #
# #     if row and row[1] == hash_password(password):
# #         return row[0]  # return user_id
# #     return None
# #
# # # ============================================
# # # USER REGISTRATION
# # # ============================================
# # def register(username, password):
# #     try:
# #         conn = get_connection()
# #         cursor = conn.cursor()
# #         cursor.execute(
# #             "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #             (username, hash_password(password)),
# #         )
# #         conn.commit()
# #         conn.close()
# #         return True
# #     except:
# #         return False
# #
# # # ============================================
# # # INSERT MOVIE
# # # ============================================
# # def insert_movie(title, year, genre, director, rating, language, duration):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #
# #     cursor.execute("""
# #         INSERT INTO movies(title, release_year, genre, director, imdb_rating, language, duration_minutes)
# #         VALUES (?, ?, ?, ?, ?, ?, ?)
# #     """, (title, year, genre, director, rating, language, duration))
# #
# #     conn.commit()
# #     conn.close()
# #
# # # ============================================
# # # FETCH ALL MOVIES
# # # ============================================
# # def get_movies():
# #     conn = get_connection()
# #     query = "SELECT * FROM movies"
# #     df = pd.read_sql(query, conn)
# #     conn.close()
# #     return df
# #
# # # ============================================
# # # SIMPLE RECOMMENDATION (FILTER BASED)
# # # ============================================
# # def recommend_movies(genre):
# #     conn = get_connection()
# #     query = "SELECT TOP 10 * FROM movies WHERE genre LIKE ? ORDER BY imdb_rating DESC"
# #     df = pd.read_sql(query, conn, params=[f'%{genre}%'])
# #     conn.close()
# #     return df
# #
# # # ============================================
# # # STREAMLIT UI
# # # ============================================
# #
# # st.title("🎬 Movie Recommendation System")
# #
# # menu = ["Login", "Register", "Home"]
# # choice = st.sidebar.selectbox("Menu", menu)
# #
# # # ============================================
# # # LOGIN PAGE
# # # ============================================
# # if choice == "Login":
# #     st.subheader("Login")
# #
# #     username = st.text_input("Username")
# #     password = st.text_input("Password", type="password")
# #
# #     if st.button("Login"):
# #         user_id = login(username, password)
# #         if user_id:
# #             st.success(f"Logged in as {username}")
# #             st.session_state["user"] = username
# #             st.session_state["user_id"] = user_id
# #         else:
# #             st.error("Invalid username or password")
# #
# # # ============================================
# # # REGISTER PAGE
# # # ============================================
# # elif choice == "Register":
# #     st.subheader("Create Account")
# #
# #     username = st.text_input("New Username")
# #     password = st.text_input("New Password", type="password")
# #
# #     if st.button("Register"):
# #         if register(username, password):
# #             st.success("Account created successfully! Go to Login.")
# #         else:
# #             st.error("Username already exists.")
# #
# # # ============================================
# # # HOME PAGE
# # # ============================================
# # elif choice == "Home":
# #
# #     if "user" not in st.session_state:
# #         st.warning("Please login first.")
# #         st.stop()
# #
# #     st.success(f"Welcome {st.session_state['user']} 👋")
# #
# #     tab1, tab2, tab3 = st.tabs(["➕ Add Movie", "📚 View Movies", "🎯 Recommendations"])
# #
# #     # ADD MOVIE
# #     with tab1:
# #         st.header("Add Movie")
# #
# #         title = st.text_input("Movie Title")
# #         year = st.number_input("Release Year", min_value=1900, max_value=2100)
# #         genre = st.text_input("Genre")
# #         director = st.text_input("Director")
# #         rating = st.number_input("IMDB Rating", min_value=0.0, max_value=10.0, step=0.1)
# #         language = st.text_input("Language")
# #         duration = st.number_input("Duration (minutes)", min_value=1)
# #
# #         if st.button("Add Movie"):
# #             insert_movie(title, year, genre, director, rating, language, duration)
# #             st.success("Movie added successfully!")
# #
# #     # VIEW MOVIES
# #     with tab2:
# #         st.header("All Movies")
# #         movies = get_movies()
# #         st.dataframe(movies)
# #
# #     # RECOMMENDATIONS
# #     with tab3:
# #         st.header("Get Recommendations")
# #
# #         genre_filter = st.text_input("Enter Genre (Action, Comedy, etc.)")
# #
# #         if st.button("Recommend"):
# #             df = recommend_movies(genre_filter)
# #             if df.empty:
# #                 st.warning("No matching movies found.")
# #             else:
# #                 st.dataframe(df)
#
