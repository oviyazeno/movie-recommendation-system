# # import streamlit as st
# # import pandas as pd
# # import pyodbc
# # from werkzeug.security import generate_password_hash, check_password_hash
# # from sklearn.feature_extraction.text import TfidfVectorizer
# # from sklearn.metrics.pairwise import linear_kernel
# #
# #
# # # ===========================================
# # # DATABASE CONNECTION
# # # ===========================================
# # def get_connection():
# #     server = 'localhost'                    # Change only if your SSMS server name is different
# #     database = 'MovieDb'
# #     driver = '{ODBC Driver 17 for SQL Server}'
# #     return pyodbc.connect(
# #         f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
# #     )
# #
# #
# # # ===========================================
# # # FETCH MOVIES
# # # ===========================================
# # def fetch_movies():
# #     conn = get_connection()
# #     df = pd.read_sql("SELECT * FROM movies", conn)
# #     conn.close()
# #     return df
# #
# #
# # # ===========================================
# # # USER AUTH FUNCTIONS
# # # ===========================================
# # def create_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     hashed = generate_password_hash(password)
# #
# #     cursor.execute(
# #         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #         (username, hashed),
# #     )
# #     conn.commit()
# #     conn.close()
# #
# #
# # def authenticate_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #
# #     cursor.execute("SELECT password_hash FROM users WHERE username=?", username)
# #     row = cursor.fetchone()
# #     conn.close()
# #
# #     if row:
# #         return check_password_hash(row[0], password)
# #     return False
# #
# #
# # # ===========================================
# # # STREAMLIT CONFIG
# # # ===========================================
# # st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# # st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# #
# #
# # # ===========================================
# # # LOGIN / SIGNUP
# # # ===========================================
# # menu = ["Login", "Signup", "Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations"]
# # choice = st.sidebar.selectbox("Menu", menu)
# #
# # # -------------------------------------------
# # # SIGNUP
# # # -------------------------------------------
# # if choice == "Signup":
# #     st.header("📝 Create New User Account")
# #
# #     new_user = st.text_input("Username")
# #     new_pass = st.text_input("Password", type="password")
# #
# #     if st.button("Signup"):
# #         create_user(new_user, new_pass)
# #         st.success("User created successfully!")
# #
# # # -------------------------------------------
# # # LOGIN
# # # -------------------------------------------
# # elif choice == "Login":
# #     st.header("🔐 User Login")
# #
# #     user = st.text_input("Username")
# #     pwd = st.text_input("Password", type="password")
# #
# #     if st.button("Login"):
# #         if authenticate_user(user, pwd):
# #             st.success(f"Welcome {user}! Login Successful")
# #         else:
# #             st.error("Invalid username or password")
# #
# #
# # # ===========================================
# # # HOME → SHOW ALL MOVIES
# # # ===========================================
# # elif choice == "Home":
# #     st.header("📌 All Movies")
# #     df = fetch_movies()
# #     st.dataframe(df, use_container_width=True)
# #
# #
# # # ===========================================
# # # ADD MOVIE
# # # ===========================================
# # elif choice == "Add Movie":
# #     st.header("➕ Add New Movie")
# #
# #     title = st.text_input("Movie Title")
# #     year = st.number_input("Release Year", min_value=1900, max_value=2100)
# #     genre = st.text_input("Genre")
# #     director = st.text_input("Director")
# #     rating = st.number_input("IMDB Rating", min_value=1.0, max_value=10.0, step=0.1)
# #     language = st.text_input("Language")
# #     duration = st.number_input("Duration (Minutes)", min_value=30, max_value=300)
# #
# #     if st.button("Add Movie"):
# #         conn = get_connection()
# #         cursor = conn.cursor()
# #
# #         cursor.execute("""
# #             INSERT INTO movies
# #             (title, release_year, genre, director, imdb_rating, language, duration_minutes)
# #             VALUES (?, ?, ?, ?, ?, ?, ?)
# #         """, (title, year, genre, director, rating, language, duration))
# #
# #         conn.commit()
# #         conn.close()
# #         st.success("Movie Added Successfully!")
# #
# #
# # # ===========================================
# # # UPDATE MOVIE
# # # ===========================================
# # elif choice == "Update Movie":
# #     st.header("✏️ Update Movie")
# #
# #     df = fetch_movies()
# #     movie_list = df['title'].tolist()
# #
# #     selected_movie = st.selectbox("Choose Movie", movie_list)
# #     movie_data = df[df['title'] == selected_movie].iloc[0]
# #
# #     new_title = st.text_input("Title", movie_data['title'])
# #     new_genre = st.text_input("Genre", movie_data['genre'])
# #     new_rating = st.number_input("Rating", value=float(movie_data['imdb_rating']), step=0.1)
# #
# #     if st.button("Update"):
# #         conn = get_connection()
# #         cursor = conn.cursor()
# #
# #         cursor.execute("""
# #             UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
# #         """, (new_title, new_genre, new_rating, movie_data['movie_id']))
# #
# #         conn.commit()
# #         conn.close()
# #         st.success("Movie Updated Successfully!")
# #
# #
# # # ===========================================
# # # DELETE MOVIE
# # # ===========================================
# # elif choice == "Delete Movie":
# #     st.header("🗑️ Delete Movie")
# #
# #     df = fetch_movies()
# #     movie_list = df['title'].tolist()
# #
# #     selected_movie = st.selectbox("Select Movie", movie_list)
# #     movie_id = df[df['title'] == selected_movie]['movie_id'].values[0]
# #
# #     if st.button("Delete"):
# #         conn = get_connection()
# #         cursor = conn.cursor()
# #         cursor.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
# #         conn.commit()
# #         conn.close()
# #         st.error("Movie Deleted!")
# #
# #
# # # ===========================================
# # # FILTER MOVIES
# # # ===========================================
# # elif choice == "Filter Movies":
# #     st.header("🔍 Filter Movies")
# #
# #     df = fetch_movies()
# #
# #     genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
# #     language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
# #     rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
# #
# #     filtered_df = df[
# #         ((df["genre"] == genre) | (genre == "All")) &
# #         ((df["language"] == language) | (language == "All")) &
# #         (df["imdb_rating"] >= rating)
# #     ]
# #
# #     st.dataframe(filtered_df, use_container_width=True)
# #
# #
# # # ===========================================
# # # RECOMMENDATION ENGINE
# # # ===========================================
# # elif choice == "Recommendations":
# #     st.header("🤖 Movie Recommendations")
# #
# #     df = fetch_movies()
# #
# #     # text features
# #     df['combined'] = df['genre'] + " " + df['director']
# #
# #     vec = TfidfVectorizer(stop_words='english')
# #     tfidf = vec.fit_transform(df['combined'])
# #
# #     cos_sim = linear_kernel(tfidf, tfidf)
# #
# #     movie_list = df['title'].tolist()
# #     movie = st.selectbox("Select a Movie", movie_list)
# #
# #     idx = df[df['title'] == movie].index[0]
# #     sim_scores = list(enumerate(cos_sim[idx]))
# #     sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
# #
# #     movie_indices = [i[0] for i in sim_scores]
# #
# #     st.success("Recommended Movies")
# #     st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
#
# #
# # import streamlit as st
# # import pandas as pd
# # import pyodbc
# # from werkzeug.security import generate_password_hash, check_password_hash
# # from sklearn.feature_extraction.text import TfidfVectorizer
# # from sklearn.metrics.pairwise import linear_kernel
# #
# # # ===========================================
# # # DATABASE CONNECTION
# # # ===========================================
# # def get_connection():
# #     server = 'localhost'  # Change if needed
# #     database = 'MovieDb'
# #     driver = '{ODBC Driver 17 for SQL Server}'
# #     return pyodbc.connect(f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;")
# #
# # # ===========================================
# # # FETCH MOVIES
# # # ===========================================
# # def fetch_movies():
# #     conn = get_connection()
# #     df = pd.read_sql("SELECT * FROM movies", conn)
# #     conn.close()
# #     return df
# #
# # # ===========================================
# # # USER AUTH FUNCTIONS (WITHOUT ROLE)
# # # ===========================================
# # def create_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     hashed = generate_password_hash(password)
# #
# #     cursor.execute(
# #         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #         (username, hashed)
# #     )
# #     conn.commit()
# #     conn.close()
# #
# # def authenticate_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
# #     row = cursor.fetchone()
# #     conn.close()
# #     if row and check_password_hash(row[0], password):
# #         return True
# #     return False
# #
# # # ===========================================
# # # STREAMLIT CONFIG
# # # ===========================================
# # st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# # st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# #
# # # ===========================================
# # # SESSION STATE
# # # ===========================================
# # if "logged_in" not in st.session_state:
# #     st.session_state.logged_in = False
# # if "username" not in st.session_state:
# #     st.session_state.username = None
# #
# # # ===========================================
# # # LOGIN / SIGNUP
# # # ===========================================
# # menu = ["Login", "Signup"]
# # if not st.session_state.logged_in:
# #     choice = st.sidebar.selectbox("Menu", menu)
# #
# #     if choice == "Signup":
# #         st.header("📝 Create New User Account")
# #         new_user = st.text_input("Username")
# #         new_pass = st.text_input("Password", type="password")
# #         if st.button("Signup"):
# #             create_user(new_user, new_pass)
# #             st.success(f"User account '{new_user}' created successfully!")
# #
# #     elif choice == "Login":
# #         st.header("🔐 User Login")
# #         user = st.text_input("Username")
# #         pwd = st.text_input("Password", type="password")
# #         if st.button("Login"):
# #             if authenticate_user(user, pwd):
# #                 st.session_state.logged_in = True
# #                 st.session_state.username = user
# #                 st.success(f"Welcome {user}! Login Successful")
# #             else:
# #                 st.error("Invalid username or password")
# #
# # # ===========================================
# # # AFTER LOGIN - USER PAGES
# # # ===========================================
# # if st.session_state.logged_in:
# #     st.sidebar.title(f"Welcome, {st.session_state.username}")
# #     user_menu = ["Home", "Filter Movies", "Recommendations", "Logout"]
# #     choice = st.sidebar.selectbox("User Menu", user_menu)
# #
# #     # -----------------------------
# #     # LOGOUT
# #     # -----------------------------
# #     if choice == "Logout":
# #         st.session_state.logged_in = False
# #         st.session_state.username = None
# #         st.experimental_rerun()
# #
# #     # -----------------------------
# #     # HOME → SHOW ALL MOVIES
# #     # -----------------------------
# #     elif choice == "Home":
# #         st.header("📌 All Movies")
# #         df = fetch_movies()
# #         st.dataframe(df, use_container_width=True)
# #
# #     # -----------------------------
# #     # FILTER MOVIES
# #     # -----------------------------
# #     elif choice == "Filter Movies":
# #         st.header("🔍 Filter Movies")
# #         df = fetch_movies()
# #         genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
# #         language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
# #         rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
# #
# #         filtered_df = df[
# #             ((df["genre"] == genre) | (genre == "All")) &
# #             ((df["language"] == language) | (language == "All")) &
# #             (df["imdb_rating"] >= rating)
# #         ]
# #         st.dataframe(filtered_df, use_container_width=True)
# #
# #     # -----------------------------
# #     # RECOMMENDATION ENGINE
# #     # -----------------------------
# #     elif choice == "Recommendations":
# #         st.header("🤖 Movie Recommendations")
# #         df = fetch_movies()
# #         df['combined'] = df['genre'] + " " + df['director']
# #
# #         vec = TfidfVectorizer(stop_words='english')
# #         tfidf = vec.fit_transform(df['combined'])
# #         cos_sim = linear_kernel(tfidf, tfidf)
# #
# #         movie_list = df['title'].tolist()
# #         movie = st.selectbox("Select a Movie", movie_list)
# #         idx = df[df['title'] == movie].index[0]
# #         sim_scores = list(enumerate(cos_sim[idx]))
# #         sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
# #         movie_indices = [i[0] for i in sim_scores]
# #
# #         st.success("Recommended Movies")
# #         st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
# # import streamlit as st
# # import pandas as pd
# # import pyodbc
# # from werkzeug.security import generate_password_hash, check_password_hash
# # from sklearn.feature_extraction.text import TfidfVectorizer
# # from sklearn.metrics.pairwise import linear_kernel
# #
# # # ===========================================
# # # DATABASE CONNECTION
# # # ===========================================
# # def get_connection():
# #     server = 'localhost'  # Change if needed
# #     database = 'MovieDb'
# #     driver = '{ODBC Driver 17 for SQL Server}'
# #     return pyodbc.connect(f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;")
# #
# # # ===========================================
# # # FETCH MOVIES
# # # ===========================================
# # def fetch_movies():
# #     conn = get_connection()
# #     df = pd.read_sql("SELECT * FROM movies", conn)
# #     conn.close()
# #     return df
# #
# # # ===========================================
# # # USER AUTH FUNCTIONS (WITHOUT ROLE)
# # # ===========================================
# # def create_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     hashed = generate_password_hash(password)
# #     cursor.execute(
# #         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #         (username, hashed)
# #     )
# #     conn.commit()
# #     conn.close()
# #
# # def authenticate_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
# #     row = cursor.fetchone()
# #     conn.close()
# #     if row and check_password_hash(row[0], password):
# #         return True
# #     return False
# #
# # # ===========================================
# # # STREAMLIT CONFIG
# # # ===========================================
# # st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# # st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# #
# # # ===========================================
# # # SESSION STATE
# # # ===========================================
# # if "logged_in" not in st.session_state:
# #     st.session_state.logged_in = False
# # if "username" not in st.session_state:
# #     st.session_state.username = None
# #
# # # ===========================================
# # # LOGIN / SIGNUP
# # # ===========================================
# # menu = ["Login", "Signup"]
# # if not st.session_state.logged_in:
# #     choice = st.sidebar.selectbox("Menu", menu)
# #
# #     if choice == "Signup":
# #         st.header("📝 Create New User Account")
# #         new_user = st.text_input("Username")
# #         new_pass = st.text_input("Password", type="password")
# #         if st.button("Signup"):
# #             create_user(new_user, new_pass)
# #             st.success(f"User account '{new_user}' created successfully!")
# #
# #     elif choice == "Login":
# #         st.header("🔐 User Login")
# #         user = st.text_input("Username")
# #         pwd = st.text_input("Password", type="password")
# #         if st.button("Login"):
# #             if authenticate_user(user, pwd):
# #                 st.session_state.logged_in = True
# #                 st.session_state.username = user
# #                 st.success(f"Welcome {user}! Login Successful")
# #             else:
# #                 st.error("Invalid username or password")
# #
# # # ===========================================
# # # AFTER LOGIN - USER / ADMIN PAGES
# # # ===========================================
# # if st.session_state.logged_in:
# #     username = st.session_state.username
# #     st.sidebar.title(f"Welcome, {username}")
# #
# #     # Hardcoded admin username
# #     is_admin = username.lower() == "admin"
# #
# #     if is_admin:
# #         menu_options = ["Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations", "Logout"]
# #     else:
# #         menu_options = ["Home", "Filter Movies", "Recommendations", "Logout"]
# #
# #     choice = st.sidebar.selectbox("Menu", menu_options)
# #
# #     # -----------------------------
# #     # LOGOUT
# #     # -----------------------------
# #     if choice == "Logout":
# #         st.session_state.logged_in = False
# #         st.session_state.username = None
# #         st.success("Logged out successfully!")
# #         st.stop()  # Stops current run and refreshes page
# #
# #     # -----------------------------
# #     # HOME → SHOW ALL MOVIES
# #     # -----------------------------
# #     elif choice == "Home":
# #         st.header("📌 All Movies")
# #         df = fetch_movies()
# #         st.dataframe(df, use_container_width=True)
# #
# #     # -----------------------------
# #     # ADD MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Add Movie" and is_admin:
# #         st.header("➕ Add New Movie")
# #         title = st.text_input("Movie Title")
# #         year = st.number_input("Release Year", min_value=1900, max_value=2100)
# #         genre = st.text_input("Genre")
# #         director = st.text_input("Director")
# #         rating = st.number_input("IMDB Rating", min_value=1.0, max_value=10.0, step=0.1)
# #         language = st.text_input("Language")
# #         duration = st.number_input("Duration (Minutes)", min_value=30, max_value=300)
# #
# #         if st.button("Add Movie"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
# #                 VALUES (?, ?, ?, ?, ?, ?, ?)
# #             """, (title, year, genre, director, rating, language, duration))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Added Successfully!")
# #
# #     # -----------------------------
# #     # UPDATE MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Update Movie" and is_admin:
# #         st.header("✏️ Update Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Choose Movie", movie_list)
# #         movie_data = df[df['title'] == selected_movie].iloc[0]
# #
# #         new_title = st.text_input("Title", movie_data['title'])
# #         new_genre = st.text_input("Genre", movie_data['genre'])
# #         new_rating = st.number_input("Rating", value=float(movie_data['imdb_rating']), step=0.1)
# #
# #         if st.button("Update"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
# #             """, (new_title, new_genre, new_rating, movie_data['movie_id']))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Updated Successfully!")
# #
# #     # -----------------------------
# #     # DELETE MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Delete Movie" and is_admin:
# #         st.header("🗑️ Delete Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Select Movie", movie_list)
# #         movie_id = df[df['title'] == selected_movie]['movie_id'].values[0]
# #
# #         if st.button("Delete"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
# #             conn.commit()
# #             conn.close()
# #             st.error("Movie Deleted!")
# #
# #     # -----------------------------
# #     # FILTER MOVIES (ALL USERS)
# #     # -----------------------------
# #     elif choice == "Filter Movies":
# #         st.header("🔍 Filter Movies")
# #         df = fetch_movies()
# #         genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
# #         language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
# #         rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
# #
# #         filtered_df = df[
# #             ((df["genre"] == genre) | (genre == "All")) &
# #             ((df["language"] == language) | (language == "All")) &
# #             (df["imdb_rating"] >= rating)
# #         ]
# #         st.dataframe(filtered_df, use_container_width=True)
# #
# #     # -----------------------------
# #     # RECOMMENDATION ENGINE (ALL USERS)
# #     # -----------------------------
# #     elif choice == "Recommendations":
# #         st.header("🤖 Movie Recommendations")
# #         df = fetch_movies()
# #         df['combined'] = df['genre'] + " " + df['director']
# #
# #         vec = TfidfVectorizer(stop_words='english')
# #         tfidf = vec.fit_transform(df['combined'])
# #         cos_sim = linear_kernel(tfidf, tfidf)
# #
# #         movie_list = df['title'].tolist()
# #         movie = st.selectbox("Select a Movie", movie_list)
# #         idx = df[df['title'] == movie].index[0]
# #         sim_scores = list(enumerate(cos_sim[idx]))
# #         sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
# #         movie_indices = [i[0] for i in sim_scores]
# #
# #         st.success("Recommended Movies")
# #         st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
#
#
# # import streamlit as st
# # import pandas as pd
# # import pyodbc
# # from werkzeug.security import generate_password_hash, check_password_hash
# # from sklearn.feature_extraction.text import TfidfVectorizer
# # from sklearn.metrics.pairwise import linear_kernel
# #
# # # ===========================================
# # # DATABASE CONNECTION
# # # ===========================================
# # def get_connection():
# #     server = 'localhost'  # Change if needed
# #     database = 'MovieDb'
# #     driver = '{ODBC Driver 17 for SQL Server}'
# #     return pyodbc.connect(f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;")
# #
# # # ===========================================
# # # CREATE DEFAULT ADMIN USER IF NOT EXISTS
# # # ===========================================
# # def ensure_admin_exists():
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT COUNT(*) FROM users")
# #     count = cursor.fetchone()[0]
# #     if count == 0:  # No users yet
# #         admin_password = generate_password_hash("admin123")  # Default admin password
# #         cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", admin_password))
# #         conn.commit()
# #         print("Default admin user created: username='admin', password='admin123'")
# #     conn.close()
# #
# # ensure_admin_exists()
# #
# # # ===========================================
# # # FETCH MOVIES
# # # ===========================================
# # def fetch_movies():
# #     conn = get_connection()
# #     df = pd.read_sql("SELECT * FROM movies", conn)
# #     conn.close()
# #     return df
# #
# # # ===========================================
# # # USER AUTH FUNCTIONS
# # # ===========================================
# # def create_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     hashed = generate_password_hash(password)
# #     cursor.execute(
# #         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #         (username, hashed)
# #     )
# #     conn.commit()
# #     conn.close()
# #
# # def authenticate_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
# #     row = cursor.fetchone()
# #     conn.close()
# #     if row and check_password_hash(row[0], password):
# #         return True
# #     return False
# #
# # # ===========================================
# # # STREAMLIT CONFIG
# # # ===========================================
# # st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# # st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# #
# # # ===========================================
# # # SESSION STATE
# # # ===========================================
# # if "logged_in" not in st.session_state:
# #     st.session_state.logged_in = False
# # if "username" not in st.session_state:
# #     st.session_state.username = None
# #
# # # ===========================================
# # # LOGIN / SIGNUP
# # # ===========================================
# # menu = ["Login", "Signup"]
# # if not st.session_state.logged_in:
# #     choice = st.sidebar.selectbox("Menu", menu)
# #
# #     if choice == "Signup":
# #         st.header("📝 Create New User Account")
# #         new_user = st.text_input("Username")
# #         new_pass = st.text_input("Password", type="password")
# #         if st.button("Signup"):
# #             create_user(new_user, new_pass)
# #             st.success(f"User account '{new_user}' created successfully!")
# #
# #     elif choice == "Login":
# #         st.header("🔐 User Login")
# #         user = st.text_input("Username")
# #         pwd = st.text_input("Password", type="password")
# #         if st.button("Login"):
# #             if authenticate_user(user, pwd):
# #                 st.session_state.logged_in = True
# #                 st.session_state.username = user
# #                 st.success(f"Welcome {user}! Login Successful")
# #             else:
# #                 st.error("Invalid username or password")
# #
# # # ===========================================
# # # AFTER LOGIN - USER / ADMIN PAGES
# # # ===========================================
# # if st.session_state.logged_in:
# #     username = st.session_state.username
# #     st.sidebar.title(f"Welcome, {username}")
# #
# #     # Admin detection
# #     is_admin = username.lower() == "admin"
# #
# #     if is_admin:
# #         menu_options = ["Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations", "Logout"]
# #     else:
# #         menu_options = ["Home", "Filter Movies", "Recommendations", "Logout"]
# #
# #     choice = st.sidebar.selectbox("Menu", menu_options)
# #
# #     # -----------------------------
# #     # LOGOUT
# #     # -----------------------------
# #     if choice == "Logout":
# #         st.session_state.logged_in = False
# #         st.session_state.username = None
# #         st.success("Logged out successfully!")
# #         st.stop()
# #
# #     # -----------------------------
# #     # HOME → SHOW ALL MOVIES
# #     # -----------------------------
# #     elif choice == "Home":
# #         st.header("📌 All Movies")
# #         df = fetch_movies()
# #         st.dataframe(df, use_container_width=True)
# #
# #     # -----------------------------
# #     # ADD MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Add Movie" and is_admin:
# #         st.header("➕ Add New Movie")
# #         title = st.text_input("Movie Title")
# #         year = st.number_input("Release Year", min_value=1900, max_value=2100)
# #         genre = st.text_input("Genre")
# #         director = st.text_input("Director")
# #         rating = st.number_input("IMDB Rating", min_value=1.0, max_value=10.0, step=0.1)
# #         language = st.text_input("Language")
# #         duration = st.number_input("Duration (Minutes)", min_value=30, max_value=300)
# #
# #         if st.button("Add Movie"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
# #                 VALUES (?, ?, ?, ?, ?, ?, ?)
# #             """, (title, year, genre, director, rating, language, duration))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Added Successfully!")
# #
# #     # -----------------------------
# #     # UPDATE MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Update Movie" and is_admin:
# #         st.header("✏️ Update Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Choose Movie", movie_list)
# #         movie_data = df[df['title'] == selected_movie].iloc[0]
# #
# #         new_title = st.text_input("Title", movie_data['title'])
# #         new_genre = st.text_input("Genre", movie_data['genre'])
# #         new_rating = st.number_input("Rating", value=float(movie_data['imdb_rating']), step=0.1)
# #
# #         if st.button("Update"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
# #             """, (new_title, new_genre, new_rating, movie_data['movie_id']))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Updated Successfully!")
# #
# #     # -----------------------------
# #     # DELETE MOVIE (ADMIN ONLY)
# #     # -----------------------------
# #     elif choice == "Delete Movie" and is_admin:
# #         st.header("🗑️ Delete Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Select Movie", movie_list)
# #         movie_id = df[df['title'] == selected_movie]['movie_id'].values[0]
# #
# #         if st.button("Delete"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
# #             conn.commit()
# #             conn.close()
# #             st.error("Movie Deleted!")
# #
# #     # -----------------------------
# #     # FILTER MOVIES (ALL USERS)
# #     # -----------------------------
# #     elif choice == "Filter Movies":
# #         st.header("🔍 Filter Movies")
# #         df = fetch_movies()
# #         genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
# #         language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
# #         rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
# #
# #         filtered_df = df[
# #             ((df["genre"] == genre) | (genre == "All")) &
# #             ((df["language"] == language) | (language == "All")) &
# #             (df["imdb_rating"] >= rating)
# #         ]
# #         st.dataframe(filtered_df, use_container_width=True)
# #
# #     # -----------------------------
# #     # RECOMMENDATION ENGINE (ALL USERS)
# #     # -----------------------------
# #     elif choice == "Recommendations":
# #         st.header("🤖 Movie Recommendations")
# #         df = fetch_movies()
# #         df['combined'] = df['genre'] + " " + df['director']
# #
# #         vec = TfidfVectorizer(stop_words='english')
# #         tfidf = vec.fit_transform(df['combined'])
# #         cos_sim = linear_kernel(tfidf, tfidf)
# #
# #         movie_list = df['title'].tolist()
# #         movie = st.selectbox("Select a Movie", movie_list)
# #         idx = df[df['title'] == movie].index[0]
# #         sim_scores = list(enumerate(cos_sim[idx]))
# #         sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
# #         movie_indices = [i[0] for i in sim_scores]
# #
# #         st.success("Recommended Movies")
# #         st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
# # ===========================================
# # AUTO-CREATE ADMIN USER IF USERS TABLE IS EMPTY
# # # ===========================================
# # import pyodbc
# # from werkzeug.security import generate_password_hash, check_password_hash
# # import streamlit as st
# # import pandas as pd
# # from sklearn.feature_extraction.text import TfidfVectorizer
# # from sklearn.metrics.pairwise import linear_kernel
# #
# # # ---------- DATABASE CONNECTION ----------
# # def get_connection():
# #     server = 'localhost'  # Change if needed
# #     database = 'MovieDb'
# #     driver = '{ODBC Driver 17 for SQL Server}'
# #     return pyodbc.connect(f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;")
# #
# # # ---------- ENSURE ADMIN EXISTS ----------
# # def ensure_admin_exists():
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     try:
# #         cursor.execute("SELECT COUNT(*) FROM users")
# #         count = cursor.fetchone()[0]
# #         if count == 0:  # No users yet
# #             admin_password = generate_password_hash("admin123")  # Default admin password
# #             cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", admin_password))
# #             conn.commit()
# #             print("Default admin user created: username='admin', password='admin123'")
# #     except Exception as e:
# #         print("Error checking/creating admin:", e)
# #     finally:
# #         conn.close()
# #
# # ensure_admin_exists()
# #
# # # ---------- FETCH MOVIES ----------
# # def fetch_movies():
# #     conn = get_connection()
# #     df = pd.read_sql("SELECT * FROM movies", conn)
# #     conn.close()
# #     return df
# #
# # # ---------- USER AUTH ----------
# # def create_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     hashed = generate_password_hash(password)
# #     cursor.execute(
# #         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
# #         (username, hashed)
# #     )
# #     conn.commit()
# #     conn.close()
# #
# # def authenticate_user(username, password):
# #     conn = get_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
# #     row = cursor.fetchone()
# #     conn.close()
# #     if row and check_password_hash(row[0], password):
# #         return True
# #     return False
# #
# # # ---------- STREAMLIT CONFIG ----------
# # st.set_page_config(page_title="Movie Recommendation System", layout="wide")
# # st.title("🎬 Movie Recommendation System (Python + SQL + Streamlit)")
# #
# # # ---------- SESSION STATE ----------
# # if "logged_in" not in st.session_state:
# #     st.session_state.logged_in = False
# # if "username" not in st.session_state:
# #     st.session_state.username = None
# #
# # # ---------- LOGIN / SIGNUP ----------
# # menu = ["Login", "Signup"]
# # if not st.session_state.logged_in:
# #     choice = st.sidebar.selectbox("Menu", menu)
# #
# #     if choice == "Signup":
# #         st.header("📝 Create New User Account")
# #         new_user = st.text_input("Username")
# #         new_pass = st.text_input("Password", type="password")
# #         if st.button("Signup"):
# #             create_user(new_user, new_pass)
# #             st.success(f"User account '{new_user}' created successfully!")
# #
# #     elif choice == "Login":
# #         st.header("🔐 User Login")
# #         user = st.text_input("Username")
# #         pwd = st.text_input("Password", type="password")
# #         if st.button("Login"):
# #             if authenticate_user(user, pwd):
# #                 st.session_state.logged_in = True
# #                 st.session_state.username = user
# #                 st.success(f"Welcome {user}! Login Successful")
# #             else:
# #                 st.error("Invalid username or password")
# #
# # # ---------- AFTER LOGIN ----------
# # if st.session_state.logged_in:
# #     username = st.session_state.username
# #
# #     # Admin detection
# #     is_admin = username.lower() == "admin"
# #
# #     # Menu options
# #     if is_admin:
# #         menu_options = ["Home", "Add Movie", "Update Movie", "Delete Movie", "Filter Movies", "Recommendations", "Logout"]
# #         choice = st.selectbox("Select Option", menu_options)  # Admin menu as main page dropdown
# #     else:
# #         menu_options = ["Home", "Filter Movies", "Recommendations", "Logout"]
# #         choice = st.sidebar.selectbox("Menu", menu_options)  # Normal user sidebar menu
# #
# #     # ---------- LOGOUT ----------
# #     if choice == "Logout":
# #         st.session_state.logged_in = False
# #         st.session_state.username = None
# #         st.success("Logged out successfully!")
# #         st.stop()
# #
# #     # ---------- HOME ----------
# #     elif choice == "Home":
# #         st.header("📌 All Movies")
# #         df = fetch_movies()
# #         st.dataframe(df, use_container_width=True)
# #
# #     # ---------- ADD MOVIE (ADMIN) ----------
# #     elif choice == "Add Movie" and is_admin:
# #         st.header("➕ Add New Movie")
# #         title = st.text_input("Movie Title")
# #         year = st.number_input("Release Year", min_value=1900, max_value=2100)
# #         genre = st.text_input("Genre")
# #         director = st.text_input("Director")
# #         rating = st.number_input("IMDB Rating", min_value=1.0, max_value=10.0, step=0.1)
# #         language = st.text_input("Language")
# #         duration = st.number_input("Duration (Minutes)", min_value=30, max_value=300)
# #
# #         if st.button("Add Movie"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
# #                 VALUES (?, ?, ?, ?, ?, ?, ?)
# #             """, (title, year, genre, director, rating, language, duration))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Added Successfully!")
# #
# #     # ---------- UPDATE MOVIE (ADMIN) ----------
# #     elif choice == "Update Movie" and is_admin:
# #         st.header("✏️ Update Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Choose Movie", movie_list)
# #         movie_data = df[df['title'] == selected_movie].iloc[0]
# #
# #         new_title = st.text_input("Title", movie_data['title'])
# #         new_genre = st.text_input("Genre", movie_data['genre'])
# #         new_rating = st.number_input("Rating", value=float(movie_data['imdb_rating']), step=0.1)
# #
# #         if st.button("Update"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
# #             """, (new_title, new_genre, new_rating, movie_data['movie_id']))
# #             conn.commit()
# #             conn.close()
# #             st.success("Movie Updated Successfully!")
# #
# #     # ---------- DELETE MOVIE (ADMIN) ----------
# #     elif choice == "Delete Movie" and is_admin:
# #         st.header("🗑️ Delete Movie")
# #         df = fetch_movies()
# #         movie_list = df['title'].tolist()
# #         selected_movie = st.selectbox("Select Movie", movie_list)
# #         movie_id = df[df['title'] == selected_movie]['movie_id'].values[0]
# #
# #         if st.button("Delete"):
# #             conn = get_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
# #             conn.commit()
# #             conn.close()
# #             st.error("Movie Deleted!")
# #
# #     # ---------- FILTER MOVIES ----------
# #     elif choice == "Filter Movies":
# #         st.header("🔍 Filter Movies")
# #         df = fetch_movies()
# #         genre = st.selectbox("Genre", ["All"] + df["genre"].dropna().unique().tolist())
# #         language = st.selectbox("Language", ["All"] + df["language"].dropna().unique().tolist())
# #         rating = st.slider("Minimum Rating", 1.0, 10.0, 5.0)
# #
# #         filtered_df = df[
# #             ((df["genre"] == genre) | (genre == "All")) &
# #             ((df["language"] == language) | (language == "All")) &
# #             (df["imdb_rating"] >= rating)
# #         ]
# #         st.dataframe(filtered_df, use_container_width=True)
# #
# #     # ---------- RECOMMENDATIONS ----------
# #     elif choice == "Recommendations":
# #         st.header("🤖 Movie Recommendations")
# #         df = fetch_movies()
# #         df['combined'] = df['genre'] + " " + df['director']
# #
# #         vec = TfidfVectorizer(stop_words='english')
# #         tfidf = vec.fit_transform(df['combined'])
# #         cos_sim = linear_kernel(tfidf, tfidf)
# #
# #         movie_list = df['title'].tolist()
# #         movie = st.selectbox("Select a Movie", movie_list)
# #         idx = df[df['title'] == movie].index[0]
# #         sim_scores = list(enumerate(cos_sim[idx]))
# #         sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
# #         movie_indices = [i[0] for i in sim_scores]
# #
# #         st.success("Recommended Movies")
# #         st.dataframe(df.iloc[movie_indices][['title', 'genre', 'imdb_rating']])
#
# import streamlit as st
# import pandas as pd
# import pyodbc
# from werkzeug.security import generate_password_hash, check_password_hash
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import linear_kernel
#
# # ============================================================
# # DB CONNECTION
# # ============================================================
# def get_conn():
#     return pyodbc.connect(
#         "DRIVER={ODBC Driver 17 for SQL Server};"
#         "SERVER=localhost;"
#         "DATABASE=MovieDb;"
#         "Trusted_Connection=yes;"
#         )
#
#
#
#     # # ============================================================
#     # # AUTO-CREATE ADMIN
#     # # ============================================================
#     # def ensure_admin():
#     #     conn = get_conn()
#     #     cursor = conn.cursor()
#     #     cursor.execute("SELECT * FROM users WHERE username='admin'")
#     #     row = cursor.fetchone()
#     #
#     #     if not row:
#     #         hashed = generate_password_hash("admin123")
#     #         cursor.execute(
#     #             "INSERT INTO users (username, password_hash) VALUES (?, ?)",
#     #             ("admin", hashed)
#     #         )
#     #         conn.commit()
#     #     conn.close()
#     #
#     # ensure_admin()
#
# # ============================================================
# # USER FUNCTIONS
# # ============================================================
#
# # -----------------------------------
# def admin_login(username, password):
#     return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
#
# # -----------------------------------
# # ADD MOVIE
# # -----------------------------------
# def add_movie():
#     st.subheader("Add Movie")
#
#     title = st.text_input("Movie Title")
#     year = st.number_input("Year", min_value=1900, max_value=2100)
#     genre = st.text_input("Genre")
#     director = st.text_input("Director")
#     rating = st.number_input("IMDB Rating", min_value=0.0, max_value=10.0)
#     language = st.text_input("Language")
#     duration = st.number_input("Duration (minutes)", min_value=1, max_value=500)
#
#     if st.button("Save Movie"):
#         try:
#             conn = get_connection()
#             cursor = conn.cursor()
#             cursor.execute("""
#                 INSERT INTO movies (title, year, genre, director, rating, language, duration)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, (title, year, genre, director, rating, language, duration))
#             conn.commit()
#
#             st.success("Movie added successfully")
#         except Exception as e:
#             st.error(f"Error: {e}")
#
# # -----------------------------------
# # VIEW MOVIES
# # -----------------------------------
# def get_connection():
#     return pyodbc.connect(
#         f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
#     )
#
# # -------------------------
# # ADMIN CREDENTIALS
# # -------------------------
# ADMIN_USERNAME = "Zeno"
# ADMIN_PASSWORD = "Zeno@123"
#
# def view_movies():
#     st.subheader("All Movies")
#
#     conn = get_connection()
#     df = pd.read_sql("SELECT * FROM movies", conn)
#
#     st.dataframe(df)
#
# # -----------------------------------
# # UPDATE MOVIE
# # -----------------------------------
# def update_movie():
#     st.subheader("Update Movie")
#
#     conn = get_connection()
#     df = pd.read_sql("SELECT * FROM movies", conn)
#
#     movie_list = df["title"].tolist()
#     movie = st.selectbox("Select Movie", movie_list)
#
#     new_title = st.text_input("New Title")
#     new_genre = st.text_input("New Genre")
#
#     if st.button("Update"):
#         try:
#             cursor = conn.cursor()
#             cursor.execute("""
#                 UPDATE movies SET title=?, genre=? WHERE title=?
#             """, (new_title, new_genre, movie))
#             conn.commit()
#             st.success("Movie updated successfully")
#         except Exception as e:
#             st.error(f"Error: {e}")
#
# # -----------------------------------
# # DELETE MOVIE
# # -----------------------------------
# def delete_movie():
#     st.subheader("Delete Movie")
#
#     conn = get_connection()
#     df = pd.read_sql("SELECT * FROM movies", conn)
#
#     movie_list = df["title"].tolist()
#     movie = st.selectbox("Select Movie to Delete", movie_list)
#
#     if st.button("Delete"):
#         try:
#             cursor = conn.cursor()
#             cursor.execute("DELETE FROM movies WHERE title=?", movie)
#             conn.commit()
#             st.success("Movie deleted successfully")
#         except Exception as e:
#             st.error(f"Error: {e}")
#
# # -----------------------------------
# # MAIN UI
# # -----------------------------------
# st.title("🎬 Movie Management System")
#
# menu = st.sidebar.selectbox(
#     "Menu",
#     ["Home", "Admin Login"]    # 👈 NOW ADMIN LOGIN WILL SHOW!
# )
#
# # Home Page
# if menu == "Home":
#     st.write("Welcome to the Movie App")
#
# # Admin Login Page
# elif menu == "Admin Login":
#     st.subheader("Admin Login")
#
#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")
#
#     if st.button("Login"):
#
#         if admin_login(username, password):
#             st.success("Login Successful")
#
#             # -------- Admin Panel Dropdown -------- #
#             admin_menu = st.sidebar.selectbox(
#                 "Admin Dashboard",
#                 ["Select Option", "Add Movie", "View Movies", "Update Movie", "Delete Movie", "Logout"]
#             )
#
#             if admin_menu == "Add Movie":
#                 add_movie()
#
#             elif admin_menu == "View Movies":
#                 view_movies()
#
#             elif admin_menu == "Update Movie":
#                 update_movie()
#
#             elif admin_menu == "Delete Movie":
#                 delete_movie()
#
#             elif admin_menu == "Logout":
#                 st.warning("Logged out")
#
#         else:
#             st.error("Invalid Credentials")
# def create_user(username, password):
#     conn = get_conn()
#     cursor = conn.cursor()
#     hashed = generate_password_hash(password)
#     cursor.execute(
#         "INSERT INTO users (username, password_hash) VALUES (?, ?)",
#         (username, hashed)
#     )
#     conn.commit()
#     conn.close()
#
# def authenticate(username, password):
#     conn = get_conn()
#     cursor = conn.cursor()
#     cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
#     row = cursor.fetchone()
#     conn.close()
#     return row and check_password_hash(row[0], password)
#
# # ============================================================
# # MOVIES FETCH
# # ============================================================
# def get_movies():
#     conn = get_conn()
#     df = pd.read_sql("SELECT * FROM movies", conn)
#     conn.close()
#     return df
#
# # ============================================================
# # STREAMLIT APP
# # ============================================================
# st.set_page_config(page_title="Movie App", layout="wide")
# st.title("🎬 Movie Recommendation App")
#
# if "login" not in st.session_state:
#     st.session_state.login = False
# if "user" not in st.session_state:
#     st.session_state.user = ""
#
# # ============================================================
# # LOGIN / SIGNUP PAGE
# # ============================================================
# if not st.session_state.login:
#
#     page = st.sidebar.selectbox("Menu", ["Login", "Signup"])
#
#     if page == "Signup":
#         st.subheader("Create New Account")
#         u = st.text_input("Username")
#         p = st.text_input("Password", type="password")
#
#         if st.button("Create Account"):
#             create_user(u, p)
#             st.success("Account Created!")
#
#     else:
#         st.subheader("Login")
#         u = st.text_input("Username")
#         p = st.text_input("Password", type="password")
#
#         if st.button("Login"):
#             if authenticate(u, p):
#                 st.session_state.login = True
#                 st.session_state.user = u
#                 st.success("Login Successful!")
#             else:
#                 st.error("Wrong username or password")
#
#     st.stop()
#
# # ============================================================
# # ADMIN DASHBOARD
# # ============================================================
# if st.session_state.user == "admin":
#
#     st.sidebar.title("🔐 Admin Dashboard")
#     admin_menu = st.sidebar.selectbox(
#         "Select Option",
#         [
#             "Home",
#             "Add Movie",
#             "Update Movie",
#             "Delete Movie",
#             "Filter Movies",
#             "Recommendations",
#             "Logout",
#         ]
#     )
#
#     # LOGOUT
#     if admin_menu == "Logout":
#         st.session_state.login = False
#         st.session_state.user = ""
#         st.success("Logged Out")
#         st.stop()
#
#     # HOME
#     if admin_menu == "Home":
#         st.header("📌 All Movies")
#         st.dataframe(get_movies(), use_container_width=True)
#
#     # ADD MOVIE
#     if admin_menu == "Add Movie":
#         st.header("➕ Add Movie")
#
#         title = st.text_input("Movie Title")
#         year = st.number_input("Year", 1900, 2100)
#         genre = st.text_input("Genre")
#         director = st.text_input("Director")
#         rating = st.number_input("Rating", 1.0, 10.0, step=0.1)
#         language = st.text_input("Language")
#         duration = st.number_input("Duration", 30, 300)
#
#         if st.button("Add"):
#             conn = get_conn()
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO movies (title, release_year, genre, director,
#                                     imdb_rating, language, duration_minutes)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, (title, year, genre, director, rating, language, duration))
#             conn.commit()
#             conn.close()
#             st.success("Movie Added!")
#
#     # UPDATE MOVIE
#     if admin_menu == "Update Movie":
#         st.header("✏️ Update Movie")
#         df = get_movies()
#         movie = st.selectbox("Select Movie", df["title"])
#         row = df[df["title"] == movie].iloc[0]
#
#         new_title = st.text_input("Title", row["title"])
#         new_genre = st.text_input("Genre", row["genre"])
#         new_rating = st.number_input("Rating", value=float(row["imdb_rating"]))
#
#         if st.button("Update"):
#             conn = get_conn()
#             cur = conn.cursor()
#             cur.execute("""
#                 UPDATE movies SET title=?, genre=?, imdb_rating=? WHERE movie_id=?
#             """, (new_title, new_genre, new_rating, row["movie_id"]))
#             conn.commit()
#             conn.close()
#             st.success("Updated Successfully!")
#
#     # DELETE MOVIE
#     if admin_menu == "Delete Movie":
#         st.header("🗑️ Delete Movie")
#         df = get_movies()
#         movie = st.selectbox("Pick Movie", df["title"])
#         movie_id = df[df["title"] == movie]["movie_id"].values[0]
#
#         if st.button("Delete"):
#             conn = get_conn()
#             cur = conn.cursor()
#             cur.execute("DELETE FROM movies WHERE movie_id=?", movie_id)
#             conn.commit()
#             conn.close()
#             st.warning("Movie Deleted!")
#
#     # FILTER MOVIES
#     if admin_menu == "Filter Movies":
#         st.header("🔍 Filter Movies")
#         df = get_movies()
#
#         g = st.selectbox("Genre", ["All"] + list(df["genre"].unique()))
#         l = st.selectbox("Language", ["All"] + list(df["language"].unique()))
#         r = st.slider("Min Rating", 1.0, 10.0, 5.0)
#
#         result = df[
#             ((df["genre"] == g) | (g == "All")) &
#             ((df["language"] == l) | (l == "All")) &
#             (df["imdb_rating"] >= r)
#         ]
#         st.dataframe(result, use_container_width=True)
#
#     # RECOMMENDATIONS
#     if admin_menu == "Recommendations":
#         st.header("🤖 AI Recommendations")
#         df = get_movies()
#         df["combined"] = df["genre"] + " " + df["director"]
#
#         tfidf = TfidfVectorizer(stop_words="english")
#         mat = tfidf.fit_transform(df["combined"])
#         sim = linear_kernel(mat, mat)
#
#         movie = st.selectbox("Choose Movie", df["title"])
#         idx = df[df["title"] == movie].index[0]
#
#         scores = list(enumerate(sim[idx]))
#         scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:6]
#         idxs = [i[0] for i in scores]
#
#         st.dataframe(df.iloc[idxs][["title", "genre", "imdb_rating"]])
#
#     st.stop()
#
# # ============================================================
# # USER DASHBOARD
# # ============================================================
# st.sidebar.title("👤 User Dashboard")
# user_menu = st.sidebar.selectbox(
#     "Select Option",
#     ["Home", "Filter Movies", "Recommendations", "Logout"]
# )
#
# if user_menu == "Logout":
#     st.session_state.login = False
#     st.session_state.user = ""
#     st.success("Logged Out")
#     st.stop()
#
# if user_menu == "Home":
#     st.header("📌 All Movies")
#     st.dataframe(get_movies())
#
# if user_menu == "Filter Movies":
#     st.header("🔍 Filter Movies")
#     df = get_movies()
#
#     g = st.selectbox("Genre", ["All"] + list(df["genre"].unique()))
#     l = st.selectbox("Language", ["All"] + list(df["language"].unique()))
#     r = st.slider("Min Rating", 1.0, 10.0, 5.0)
#
#     result = df[
#         ((df["genre"] == g) | (g == "All")) &
#         ((df["language"] == l) | (l == "All")) &
#         (df["imdb_rating"] >= r)
#     ]
#     st.dataframe(result)
#
# if user_menu == "Recommendations":
#     st.header("🤖 AI Recommendations")
#     df = get_movies()
#     df["combined"] = df["genre"] + " " + df["director"]
#
#     tfidf = TfidfVectorizer(stop_words="english")
#     mat = tfidf.fit_transform(df["combined"])
#     sim = linear_kernel(mat, mat)
#
#     movie = st.selectbox("Choose Movie", df["title"])
#     idx = df[df["title"] == movie].index[0]
#
#     scores = list(enumerate(sim[idx]))
#     scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:6]
#     idxs = [i[0] for i in scores]
#
#     st.dataframe(df.iloc[idxs][["title", "genre", "imdb_rating"]])
