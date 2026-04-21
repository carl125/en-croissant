# Repo Context

This document captures practical implementation notes for this fork so future work can move faster.

## Stack

- Desktop app built with Tauri 2
- Frontend in React + TypeScript under `src/`
- Backend/native commands in Rust under `src-tauri/src/`

## Local Build Notes

### Windows prerequisites

- Node.js
- `pnpm`
- Rust via `rustup`
- Visual Studio Build Tools with `Desktop development with C++`

Quick checks:

```powershell
node -v
pnpm -v
rustc -V
cargo -V
```

### Local commands

Run from repo root:

```powershell
pnpm install
pnpm dev
pnpm build
```

Notes:

- `pnpm dev` runs the desktop app from source and is the fastest way to verify app-logic changes.
- `pnpm build` rebuilds the desktop app and writes artifacts to `src-tauri/target/release`.

## Puzzle System

### Current behavior

- The puzzle UI does not fetch a live puzzle from Lichess for each attempt.
- The app reads puzzle data from local `.db3` SQLite files in the puzzles directory.
- The puzzle tab enumerates available `.db3` files and reads metadata from them.
- Default downloadable puzzle databases are fetched from `encroissant.org`, but the runtime puzzle engine itself only depends on local DB files.

Relevant files:
- `src/components/puzzles/Puzzles.tsx`
- `src/components/puzzles/AddPuzzle.tsx`
- `src/utils/puzzles.ts`
- `src/utils/db.ts`
- `src-tauri/src/puzzle.rs`
- `src-tauri/src/db/schema.rs`

### Minimal puzzle DB schema

Required table:

`puzzles`

Required columns:

- `id`
- `fen`
- `moves`
- `user_moves_first`
- `rating`
- `rating_deviation`
- `popularity`
- `nb_plays`

Notes:
- `moves` is stored as a space-separated UCI string.
- `user_moves_first` controls whether the player starts from the given FEN (`true`) or the app auto-plays the first move in `moves` (`false`).
- Theme support is optional.
- If the DB omits theme tables, the puzzle flow should still work, but theme filtering will not.

### Optional theme tables

- `themes`
- `puzzle_themes`

These are used by the Puzzle settings panel for filtering and for showing puzzle themes after completion.

## Practical implication for the built `.exe`

- A custom puzzle DB can be used without rebuilding the app, as long as the DB matches the schema the app expects.
- Rebuilding is only required when changing app code, UI, logic, or supported input formats.
- In practice:
  - DB-only changes affect the existing built app immediately.
  - Changes such as `user_moves_first` handling in `src/` or `src-tauri/` do not affect a prebuilt app until you run `pnpm dev` or rebuild with `pnpm build`.
