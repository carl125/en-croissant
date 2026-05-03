use std::{
    collections::{HashMap, VecDeque},
    fs::remove_file,
    path::{Path, PathBuf},
    sync::Mutex,
};

use diesel::{
    insert_into,
    dsl::sql,
    sql_types::{Bool, Integer, Text},
    Connection, ExpressionMethods, OptionalExtension, QueryDsl, RunQueryDsl,
};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use shakmaty::{fen::Fen, san::San, uci::UciMove, CastlingMode, Chess, EnPassantMode, Position};
use specta::Type;

use crate::{
    db::{puzzle_themes, puzzles, themes, Puzzle},
    error::Error,
};

const STARTING_FEN: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

#[derive(Debug)]
struct PuzzleCache {
    cache: VecDeque<Puzzle>,
    counter: usize,
    min_rating: u16,
    max_rating: u16,
    theme: Option<String>,
}

#[allow(dead_code)]
#[derive(diesel::QueryableByName)]
struct TableInfoRow {
    #[diesel(sql_type = Integer)]
    cid: i32,
    #[diesel(sql_type = Text)]
    name: String,
}

#[derive(diesel::QueryableByName)]
struct ForeignKeyRow {
    #[diesel(sql_type = Integer)]
    id: i32,
}

#[derive(Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CreateUserPuzzleResult {
    slug: String,
    puzzle_id: i32,
    db_path: String,
}

#[derive(Serialize, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CreateUserPuzzlePayload {
    line_text: String,
    start_move_number: i32,
    start_side: String,
    user_moves_first: bool,
    rating: i32,
    #[specta(optional)]
    rating_deviation: Option<i32>,
    #[specta(optional)]
    popularity: Option<i32>,
    #[specta(optional)]
    nb_plays: Option<i32>,
    themes: Vec<String>,
}

#[derive(diesel::Insertable)]
#[diesel(table_name = puzzles)]
struct NewPuzzleRecord<'a> {
    slug: Option<&'a str>,
    source_fen: Option<&'a str>,
    context_moves: Option<&'a str>,
    fen: &'a str,
    moves: &'a str,
    user_moves_first: bool,
    rating: i32,
    rating_deviation: i32,
    popularity: i32,
    nb_plays: i32,
}

#[derive(diesel::Insertable)]
#[diesel(table_name = themes)]
struct NewThemeRecord<'a> {
    name: &'a str,
}

#[derive(diesel::Insertable)]
#[diesel(table_name = puzzle_themes)]
struct NewPuzzleThemeRecord {
    puzzle_id: i32,
    theme_id: i32,
}

impl PuzzleCache {
    fn new() -> Self {
        Self {
            cache: VecDeque::new(),
            counter: 0,
            min_rating: 0,
            max_rating: 0,
            theme: None,
        }
    }

    fn get_puzzles(
        &mut self,
        file: &str,
        min_rating: u16,
        max_rating: u16,
        theme: &Option<String>,
    ) -> Result<(), Error> {
        if self.cache.is_empty()
            || self.min_rating != min_rating
            || self.max_rating != max_rating
            || self.theme != *theme
            || self.counter >= 20
        {
            self.cache.clear();
            self.counter = 0;

            let mut db = diesel::SqliteConnection::establish(file).expect("open database");
            ensure_puzzle_schema(&mut db)?;

            let new_puzzles: Vec<Puzzle> = if let Some(theme_name) = theme {
                puzzles::table
                    .inner_join(puzzle_themes::table.inner_join(themes::table))
                    .filter(themes::name.eq(theme_name))
                    .filter(puzzles::rating.le(max_rating as i32))
                    .filter(puzzles::rating.ge(min_rating as i32))
                    .select(puzzles::all_columns)
                    .order(sql::<Bool>("RANDOM()"))
                    .limit(20)
                    .load::<Puzzle>(&mut db)?
            } else {
                puzzles::table
                    .filter(puzzles::rating.le(max_rating as i32))
                    .filter(puzzles::rating.ge(min_rating as i32))
                    .order(sql::<Bool>("RANDOM()"))
                    .limit(20)
                    .load::<Puzzle>(&mut db)?
            };

            self.cache = new_puzzles.into_iter().collect();
            self.min_rating = min_rating;
            self.max_rating = max_rating;
            self.theme = theme.clone();
        }

        Ok(())
    }

    fn get_next_puzzle(&mut self) -> Option<Puzzle> {
        if let Some(puzzle) = self.cache.get(self.counter) {
            self.counter += 1;
            Some(puzzle.clone())
        } else {
            None
        }
    }
}

fn ensure_puzzle_schema(db: &mut diesel::SqliteConnection) -> Result<(), Error> {
    let columns: Vec<TableInfoRow> = diesel::sql_query("PRAGMA table_info(puzzles)").load(db)?;
    if columns.is_empty() {
        diesel::sql_query(
            "CREATE TABLE IF NOT EXISTS puzzles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                source_fen TEXT,
                context_moves TEXT,
                fen TEXT NOT NULL,
                moves TEXT NOT NULL,
                user_moves_first INTEGER NOT NULL DEFAULT 0,
                rating INTEGER NOT NULL DEFAULT 1500,
                rating_deviation INTEGER NOT NULL DEFAULT 0,
                popularity INTEGER NOT NULL DEFAULT 0,
                nb_plays INTEGER NOT NULL DEFAULT 0
            )",
        )
        .execute(db)?;
    }

    let columns: Vec<TableInfoRow> = diesel::sql_query("PRAGMA table_info(puzzles)").load(db)?;
    if columns.iter().all(|column| column.name != "user_moves_first") {
        diesel::sql_query(
            "ALTER TABLE puzzles ADD COLUMN user_moves_first INTEGER NOT NULL DEFAULT 0",
        )
        .execute(db)?;
    }
    if columns.iter().all(|column| column.name != "slug") {
        diesel::sql_query("ALTER TABLE puzzles ADD COLUMN slug TEXT").execute(db)?;
        diesel::sql_query("CREATE UNIQUE INDEX IF NOT EXISTS puzzles_slug_idx ON puzzles (slug)")
            .execute(db)?;
    }
    if columns.iter().all(|column| column.name != "source_fen") {
        diesel::sql_query("ALTER TABLE puzzles ADD COLUMN source_fen TEXT").execute(db)?;
    }
    if columns.iter().all(|column| column.name != "context_moves") {
        diesel::sql_query("ALTER TABLE puzzles ADD COLUMN context_moves TEXT").execute(db)?;
    }

    diesel::sql_query(
        "CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )",
    )
    .execute(db)?;
    diesel::sql_query(
        "CREATE TABLE IF NOT EXISTS puzzle_themes (
            puzzle_id INTEGER NOT NULL,
            theme_id INTEGER NOT NULL,
            PRIMARY KEY (puzzle_id, theme_id),
            FOREIGN KEY(puzzle_id) REFERENCES puzzles(id),
            FOREIGN KEY(theme_id) REFERENCES themes(id)
        )",
    )
    .execute(db)?;
    Ok(())
}

fn normalize_theme_name(theme: &str) -> Option<String> {
    let normalized = theme.trim().to_lowercase();
    if normalized.is_empty() {
        None
    } else {
        Some(normalized)
    }
}

fn generate_slug() -> String {
    let alphabet = b"abcdefghjkmnpqrstuvwxyz23456789";
    let mut rng = rand::thread_rng();
    let body: String = (0..8)
        .map(|_| {
            let idx = rand::Rng::gen_range(&mut rng, 0..alphabet.len());
            alphabet[idx] as char
        })
        .collect();
    format!("pz_{body}")
}

fn ensure_parent_dir_exists(path: &Path) -> Result<(), Error> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    Ok(())
}

fn get_or_create_theme_ids(
    db: &mut diesel::SqliteConnection,
    selected_themes: &[String],
) -> Result<Vec<i32>, Error> {
    let mut theme_ids = Vec::new();
    let mut seen = HashMap::<String, i32>::new();

    for raw_theme in selected_themes {
        let Some(theme_name) = normalize_theme_name(raw_theme) else {
            continue;
        };

        if let Some(theme_id) = seen.get(&theme_name) {
            theme_ids.push(*theme_id);
            continue;
        }

        let existing_id = themes::table
            .filter(themes::name.eq(&theme_name))
            .select(themes::id)
            .first::<i32>(db)
            .optional()?;

        let theme_id = if let Some(id) = existing_id {
            id
        } else {
            insert_into(themes::table)
                .values(NewThemeRecord { name: &theme_name })
                .execute(db)?;

            diesel::sql_query("SELECT last_insert_rowid() AS id")
                .get_result::<ForeignKeyRow>(db)?
                .id
        };

        seen.insert(theme_name, theme_id);
        theme_ids.push(theme_id);
    }

    theme_ids.sort_unstable();
    theme_ids.dedup();
    Ok(theme_ids)
}

fn parse_solution_tokens(solution_text: &str) -> Vec<String> {
    solution_text
        .split_whitespace()
        .map(|token| token.trim_matches(|c: char| c == ',' || c == ';'))
        .filter(|token| !token.is_empty())
        .filter(|token| {
            !matches!(*token, "*" | "1-0" | "0-1" | "1/2-1/2")
                && !token.chars().all(|c| c.is_ascii_digit() || c == '.')
        })
        .map(ToOwned::to_owned)
        .collect()
}

fn convert_solution_to_uci(fen: &str, solution_text: &str) -> Result<Vec<String>, Error> {
    let fen = Fen::from_ascii(fen.as_bytes())?;
    let castling_mode = CastlingMode::detect(fen.as_setup());
    let mut position: Chess = fen.into_position(castling_mode)?;
    let mut moves = Vec::new();

    for token in parse_solution_tokens(solution_text) {
        let mv = if let Ok(uci) = UciMove::from_ascii(token.as_bytes()) {
            let mv = uci.to_move(&position)?;
            moves.push(UciMove::from_move(&mv, castling_mode).to_string());
            mv
        } else {
            let san: San = token.parse()?;
            let mv = san.to_move(&position)?;
            moves.push(UciMove::from_move(&mv, castling_mode).to_string());
            mv
        };

        position.play_unchecked(&mv);
    }

    Ok(moves)
}

fn apply_uci_moves_to_fen(fen: &str, moves: &[String]) -> Result<String, Error> {
    let fen = Fen::from_ascii(fen.as_bytes())?;
    let castling_mode = CastlingMode::detect(fen.as_setup());
    let mut position: Chess = fen.into_position(castling_mode)?;

    for move_text in moves {
        let uci = UciMove::from_ascii(move_text.as_bytes())?;
        let mv = uci.to_move(&position)?;
        position.play_unchecked(&mv);
    }

    Ok(Fen::from_position(position, EnPassantMode::Legal).to_string())
}

fn compute_split_ply(
    source_fen: &str,
    start_move_number: i32,
    start_side: &str,
    total_plies: usize,
) -> Result<usize, Error> {
    let fen = Fen::from_ascii(source_fen.as_bytes())?;
    let setup = fen.as_setup();
    let mut move_number = i32::try_from(setup.fullmoves.get()).unwrap_or(i32::MAX);
    let mut side = if setup.turn == shakmaty::Color::White {
        "white"
    } else {
        "black"
    };

    for ply in 0..total_plies {
        if move_number == start_move_number && side == start_side {
            return Ok(ply);
        }

        if side == "white" {
            side = "black";
        } else {
            side = "white";
            move_number += 1;
        }
    }

    Err(Error::InvalidPuzzleStart(format!(
        "Could not match start {}-{} inside the provided line",
        start_move_number, start_side
    )))
}

#[tauri::command]
#[specta::specta]
pub fn get_puzzle(
    file: String,
    min_rating: u16,
    max_rating: u16,
    theme: Option<String>,
) -> Result<Puzzle, Error> {
    static PUZZLE_CACHE: Lazy<Mutex<PuzzleCache>> = Lazy::new(|| Mutex::new(PuzzleCache::new()));

    let mut cache = PUZZLE_CACHE.lock().unwrap();
    cache.get_puzzles(&file, min_rating, max_rating, &theme)?;
    cache.get_next_puzzle().ok_or(Error::NoPuzzles)
}

#[tauri::command]
#[specta::specta]
pub fn get_puzzle_by_slug(file: String, slug: String) -> Result<Puzzle, Error> {
    let mut db = diesel::SqliteConnection::establish(&file).expect("open database");
    ensure_puzzle_schema(&mut db)?;

    puzzles::table
        .filter(puzzles::slug.eq(Some(slug)))
        .first::<Puzzle>(&mut db)
        .map_err(Into::into)
}

#[derive(Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct PuzzleDatabaseInfo {
    title: String,
    description: String,
    puzzle_count: i32,
    storage_size: u64,
    path: String,
}

#[tauri::command]
#[specta::specta]
pub async fn get_puzzle_db_info(file: PathBuf) -> Result<PuzzleDatabaseInfo, Error> {
    let path = file;

    let mut db =
        diesel::SqliteConnection::establish(&path.to_string_lossy()).expect("open database");
    ensure_puzzle_schema(&mut db)?;

    let puzzle_count = puzzles::table.count().get_result::<i64>(&mut db)? as i32;

    let storage_size = path.metadata()?.len();
    let filename = path.file_name().expect("get filename").to_string_lossy();

    Ok(PuzzleDatabaseInfo {
        title: filename.to_string(),
        description: "".to_string(),
        puzzle_count,
        storage_size,
        path: path.to_string_lossy().to_string(),
    })
}

#[tauri::command]
#[specta::specta]
pub fn delete_puzzle_database(file: String) -> Result<(), Error> {
    remove_file(&file)?;
    Ok(())
}

#[tauri::command]
#[specta::specta]
pub fn get_puzzle_themes(file: String) -> Result<Vec<String>, Error> {
    let mut db = diesel::SqliteConnection::establish(&file).expect("open database");
    ensure_puzzle_schema(&mut db)?;
    let result: Vec<String> = themes::table
        .select(themes::name)
        .order(themes::name.asc())
        .load(&mut db)?;
    Ok(result)
}

#[tauri::command]
#[specta::specta]
pub fn get_themes_for_puzzle(file: String, puzzle_id: i32) -> Result<Vec<String>, Error> {
    let mut db = diesel::SqliteConnection::establish(&file).expect("open database");
    ensure_puzzle_schema(&mut db)?;
    let result: Vec<String> = themes::table
        .inner_join(puzzle_themes::table)
        .filter(puzzle_themes::puzzle_id.eq(puzzle_id))
        .select(themes::name)
        .order(themes::name.asc())
        .load(&mut db)?;
    Ok(result)
}

#[tauri::command]
#[specta::specta]
pub fn create_user_puzzle(
    file: String,
    payload: CreateUserPuzzlePayload,
) -> Result<CreateUserPuzzleResult, Error> {
    let path = PathBuf::from(&file);
    ensure_parent_dir_exists(&path)?;

    let mut db = diesel::SqliteConnection::establish(&path.to_string_lossy()).expect("open database");
    ensure_puzzle_schema(&mut db)?;

    let source_fen = STARTING_FEN.to_string();
    let full_uci_moves = convert_solution_to_uci(&source_fen, &payload.line_text)?;
    if full_uci_moves.is_empty() {
        return Err(Error::NoMovesFound);
    }

    let start_side = payload.start_side.trim().to_lowercase();
    if start_side != "white" && start_side != "black" {
        return Err(Error::InvalidPuzzleStart(format!(
            "Unsupported side '{}'",
            payload.start_side
        )));
    }
    let split_ply = compute_split_ply(
        &source_fen,
        payload.start_move_number,
        &start_side,
        full_uci_moves.len(),
    )?;
    let context_uci_moves = full_uci_moves[..split_ply].to_vec();
    let solution_uci_moves = full_uci_moves[split_ply..].to_vec();
    if solution_uci_moves.is_empty() {
        return Err(Error::NoMovesFound);
    }
    if !payload.user_moves_first && solution_uci_moves.len() < 2 {
        return Err(Error::NoMovesFound);
    }

    let puzzle_fen = apply_uci_moves_to_fen(&source_fen, &context_uci_moves)?;
    let moves = solution_uci_moves.join(" ");
    let context_moves = (!context_uci_moves.is_empty()).then(|| context_uci_moves.join(" "));
    let slug = loop {
        let candidate = generate_slug();
        let exists = puzzles::table
            .filter(puzzles::slug.eq(Some(candidate.clone())))
            .select(puzzles::id)
            .first::<i32>(&mut db)
            .optional()?;
        if exists.is_none() {
            break candidate;
        }
    };

    insert_into(puzzles::table)
        .values(NewPuzzleRecord {
            slug: Some(&slug),
            source_fen: Some(&source_fen),
            context_moves: context_moves.as_deref(),
            fen: &puzzle_fen,
            moves: &moves,
            user_moves_first: payload.user_moves_first,
            rating: payload.rating,
            rating_deviation: payload.rating_deviation.unwrap_or(0),
            popularity: payload.popularity.unwrap_or(0),
            nb_plays: payload.nb_plays.unwrap_or(0),
        })
        .execute(&mut db)?;

    let puzzle_id = diesel::sql_query("SELECT last_insert_rowid() AS id")
        .get_result::<ForeignKeyRow>(&mut db)?
        .id;

    let theme_ids = get_or_create_theme_ids(&mut db, &payload.themes)?;
    for theme_id in theme_ids {
        insert_into(puzzle_themes::table)
            .values(NewPuzzleThemeRecord { puzzle_id, theme_id })
            .execute(&mut db)?;
    }

    Ok(CreateUserPuzzleResult {
        slug,
        puzzle_id,
        db_path: path.to_string_lossy().to_string(),
    })
}
