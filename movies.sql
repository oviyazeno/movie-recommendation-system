CREATE TABLE movies (
    movie_id INT IDENTITY(1,1) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_year INT NULL,
    genre VARCHAR(100) NULL,
    director VARCHAR(255) NULL,
    imdb_rating DECIMAL(3,1) NULL,
    language VARCHAR(100) NULL,
    duration_minutes INT NULL,
    created_at DATETIME DEFAULT GETDATE()
);

INSERT INTO movies (title, release_year, genre, director, imdb_rating, language, duration_minutes)
VALUES
('Inception', 2010, 'Sci-Fi', 'Christopher Nolan', 8.8, 'English', 148),
('Interstellar', 2014, 'Sci-Fi', 'Christopher Nolan', 8.6, 'English', 169),
('The Dark Knight', 2008, 'Action', 'Christopher Nolan', 9.0, 'English', 152),
('KGF Chapter 1', 2018, 'Action', 'Prashanth Neel', 8.2, 'Kannada', 155),
('Vikram', 2022, 'Action Thriller', 'Lokesh Kanagaraj', 8.3, 'Tamil', 175),
('Baahubali', 2015, 'Epic', 'S. S. Rajamouli', 8.0, 'Telugu', 159);

select * from movies
