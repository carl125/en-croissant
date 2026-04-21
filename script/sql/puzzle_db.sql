CREATE TABLE puzzles (
  id INTEGER PRIMARY KEY,
  fen TEXT NOT NULL,
  moves TEXT NOT NULL,
  user_moves_first INTEGER NOT NULL DEFAULT 0,
  rating INTEGER NOT NULL,
  rating_deviation INTEGER NOT NULL,
  popularity INTEGER NOT NULL,
  nb_plays INTEGER NOT NULL
);

CREATE TABLE themes (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE puzzle_themes (
  puzzle_id INTEGER NOT NULL,
  theme_id INTEGER NOT NULL,
  PRIMARY KEY (puzzle_id, theme_id),
  FOREIGN KEY (puzzle_id) REFERENCES puzzles(id),
  FOREIGN KEY (theme_id) REFERENCES themes(id)
);

CREATE INDEX idx_puzzles_rating ON puzzles (rating);
CREATE INDEX idx_themes_name ON themes (name);
CREATE INDEX idx_puzzle_themes_theme_id ON puzzle_themes (theme_id);
