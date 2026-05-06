# User-Created Puzzles

This document describes the minimal local-only feature for user-created puzzles
 in this fork.

## Goal

Allow a player to:

- create a puzzle inside the app
- save it locally without any server dependency
- receive a stable puzzle identifier such as a slug
- store that slug in an external learning or review workflow
- later load the exact same puzzle again from that slug
- optionally review the same puzzle set through the existing puzzle DB UI

This is intentionally a personal workflow, not a sharing system.

## Product Scope

The feature is local-only:

- no backend
- no sync
- no public sharing
- no cross-device guarantee

A puzzle exists only on the current machine unless the user manually copies the
 database file elsewhere.

## High-Level Approach

Use a dedicated local SQLite puzzle database, for example:

- `user-puzzles.db3`

Store that file in the same puzzles directory already used by the app for other
 puzzle databases.

This keeps the feature aligned with the existing runtime:

- the app already scans the puzzles directory for `.db3` files
- a valid `.db3` in that directory appears in the puzzle DB selector
- the existing random puzzle flow can reuse that DB without a separate storage
  path

## Required Capabilities

The feature needs two different access patterns.

### 1. Review as a normal puzzle DB

The user should be able to:

- select the personal puzzle DB in the existing puzzle DB dropdown
- generate random puzzles from it
- filter by rating range
- filter by theme when theme tables exist

This behavior comes from storing a valid `.db3` in the puzzles directory.

### 2. Load a specific puzzle by slug

The user should also be able to:

- create a puzzle
- receive a stable slug such as `pz_9f3k2m7a`
- later provide that slug again
- reopen the exact same puzzle rather than a random one

This requires an explicit lookup command. The current puzzle runtime only loads
 random puzzles from a selected DB.

## Database Model

The personal DB should remain compatible with the current puzzle schema so the
 existing puzzle UI can use it directly.

### Core tables

- `puzzles`
- `themes`
- `puzzle_themes`

### Existing puzzle fields

The `puzzles` table already needs:

- `id`
- `fen`
- `moves`
- `user_moves_first`
- `rating`
- `rating_deviation`
- `popularity`
- `nb_plays`

### Additional field for stable lookup

Add a stable unique identifier for personal lookup:

- `slug`

This can be added either:

- directly on `puzzles`
- or via a separate mapping table

For the minimal version, a `slug` column on `puzzles` is the simplest choice.

## Theme Handling

Theme support should be preserved for the personal DB so the existing puzzle
 settings panel can filter by theme.

Recommended create flow:

- read existing themes from the target DB
- show them in a creatable multi-select
- allow the user to choose existing themes
- allow the user to type new themes
- insert missing themes into `themes`
- insert puzzle-theme relations into `puzzle_themes`

This keeps the DB usable both for direct slug lookup and for ordinary puzzle DB
 review.

## Minimal User Flow

### Create

1. User fills in puzzle data such as `fen`, `moves`, and whether the user moves
first.
2. App shows existing themes from the personal DB.
3. User selects existing themes or enters new ones.
4. App writes the puzzle into `user-puzzles.db3`.
5. App generates and returns a stable slug.

### Review through learning app

1. The user stores the slug in an external app or note system.
2. Later the user provides that slug back to en-croissant.
3. En-croissant loads the matching puzzle from the personal DB.
4. The puzzle opens directly instead of going through random DB selection.

### Review through the puzzle DB UI

1. The user selects `user-puzzles.db3` in the puzzle panel.
2. The user reviews puzzles from that DB just like any other puzzle database.
3. Theme filtering works if `themes` and `puzzle_themes` are populated.

## Suggested Commands

The current codebase already supports reading puzzle DB metadata, listing
 themes, and fetching random puzzles. The personal puzzle feature needs write
 and lookup commands in addition to those.

Minimal additions:

- `ensure_user_puzzle_db()`
- `create_user_puzzle(...) -> { slug }`
- `get_user_puzzle_by_slug(slug) -> Puzzle`

Optional but useful:

- `get_or_create_theme(...)`
- `list_user_puzzle_themes()`

## Why Slug Instead Of Numeric ID

A slug is preferable to a raw numeric row id because it is:

- easier to copy
- stable for external notes or learning apps
- independent from row ordering assumptions

The slug does not need to be globally meaningful. It only needs to uniquely
 identify a puzzle in the local personal DB.

## MVP Boundaries

The minimal version should avoid feature creep.

In scope:

- local persistence
- theme assignment
- slug generation
- reload by slug
- visibility as a normal puzzle DB

Out of scope:

- cloud sync
- team sharing
- export links for other machines
- full puzzle-management UI such as bulk edit, rename themes, or merge themes

## Implementation Notes

This feature fits the existing architecture well:

- frontend puzzle DB selection already reads `.db3` files from the puzzles
  directory
- theme reading commands already exist
- puzzle runtime already understands the app's puzzle schema

The only missing pieces are:

- creating puzzle rows
- writing theme relations
- looking up a puzzle by slug instead of random selection

## Summary

The simplest viable design is:

- keep a dedicated `user-puzzles.db3`
- store it in the normal puzzles directory
- keep the standard puzzle schema so the current puzzle UI can use it
- add a `slug` for direct personal lookup
- support creatable themes so the DB remains reviewable through the existing
  theme filter UI

## Context History

This section documents the context-aware extension used for review workflows.

### Current limitation

The current puzzle runtime only understands:

- the starting `fen`
- the solution `moves`
- whether `user_moves_first` is enabled

That means:

- the app can replay the solution line
- the app can optionally auto-play the first solution move
- the app cannot show the move history that led to the puzzle position unless
  that history is also part of the solution line

This is enough for pure tactics review, but it is weaker than a Lichess-style
 puzzle review when the user needs to understand how the position arose.

### Problem statement

For some puzzles, the user needs context:

- opening traps
- positional tactics
- defensive resources
- quiet tactical sequences
- puzzles where the key idea only makes sense after seeing the lead-in moves

Without context, the user sees a single position and a solution, but not the
 path that created the position.

### Desired behavior

The app should still open the puzzle at the puzzle start position, but also let
 the user step backward through a limited context history before the first
 puzzle move.

The runtime should distinguish:

- context moves that happened before the puzzle begins
- solution moves that are part of the puzzle itself

### Schema change

Extend `puzzles` with optional context columns.

Suggested format:

- `context_moves TEXT NULL`
- `source_fen TEXT NULL`

Format should match the existing `moves` convention:

- a space-separated UCI string

Meaning:

- `source_fen`: the starting position for the full line
- `context_moves`: moves that lead into the stored puzzle start position
- `moves`: the actual puzzle solution line from the stored start position

This is the smallest schema change that preserves compatibility with the
 current puzzle runtime.

### Why not replace `fen`

The `fen` field should keep its current meaning:

- it is the position where the puzzle begins

This avoids breaking the existing runtime and keeps old puzzle databases valid.

### Runtime changes needed

To support context history, puzzle loading must change.

Current behavior:

- set board to `fen`
- if `user_moves_first` is `false`, auto-play the first move in `moves`

Desired behavior:

- build a move tree or line that includes `context_moves`
- position the board at the end of `context_moves`
- start puzzle solving from there
- allow navigation backward into `context_moves`
- keep puzzle checking and hint logic scoped to `moves`, not `context_moves`

Important rule:

- context is for navigation and understanding
- solution validation still begins at the puzzle boundary

### Frontend implications

The frontend needs a clear internal distinction between:

- context length
- solution start
- current position inside or after context

Likely changes:

- add `context_moves` to frontend puzzle types
- build puzzle state from both context and solution
- place the initial cursor at the end of the context segment
- update hint logic so hints only apply once the user is at or after the puzzle
  start
- update completion checking so it ignores navigation within context history

### Backend implications

The backend needs to:

- migrate the schema to include `context_moves`
- expose `context_moves` through puzzle load commands
- accept `context_moves` when creating personal puzzles
- normalize context input to UCI using the same SAN or UCI conversion rules used
  for solution input

### Create flow

The implemented default creation flow is:

- paste a whole line of moves
- choose the move number where the puzzle starts
- choose whether the first puzzle move is White or Black

The user provides:

- a full move line
- the move number where the puzzle begins
- the side that plays the first puzzle move

Backend then:

- assumes the line starts from the standard chess initial position
- parses the full line
- computes the split point from the initial position, move number, and side
- splits the line into `context_moves` and `moves`
- computes the puzzle `fen` at the split point
- stores both segments separately

This is the preferred UX because it matches how users usually think about
 review puzzles:

- they know the whole sequence
- they know where the tactical question begins
- they usually think in notation like `8-1` or `8-2`, not raw ply counts

### Why the default flow does not ask for FEN

For the normal review workflow, the user already provides the full line. In
 that case, asking for a starting FEN adds technical friction without adding
 meaningful information.

So the default flow should not ask for FEN at all.

The app should assume:

- the line starts from the standard initial position

Only if future requirements need partial lines or composed positions should a
 custom starting FEN be exposed again.

### Compatibility strategy

Puzzle databases without `context_moves` must keep working unchanged.

Rules:

- if `context_moves` is absent or empty, use the current runtime behavior
- only puzzles that provide context should expose pre-puzzle history

This keeps old DBs valid and avoids forcing a one-time migration of all puzzle
 data sources.

### Summary

The puzzle runtime now supports optional review context through `source_fen` and
 `context_moves`, while preserving compatibility with older snapshot-style
 puzzle DBs that only provide `fen` and `moves`.

## Editing Personal Puzzles

The app now supports editing personal puzzles in-place by `slug`, but only for
 puzzles created after edit metadata was added.

### Why edit support is gated

The creation UI is built around:

- `whole line`
- `start move number`
- `start side`

Older personal puzzles only store normalized runtime fields such as:

- `source_fen`
- `context_moves`
- `fen`
- `moves`

That is enough to review the puzzle, but not enough to reconstruct the exact
 create-form inputs without adding brittle reverse-conversion logic.

### Metadata stored for editable puzzles

Newly created or updated personal puzzles also store:

- `line_text`
- `start_move_number`
- `start_side`

These fields are not needed by the runtime itself. They exist so the app can
 reopen the same puzzle in the create form, prefill the original inputs, and
 save edits back to the same `slug`.

### Legacy compatibility strategy

Personal puzzles created before this metadata exists remain valid for:

- slug lookup
- random review through `user-puzzles.db3`
- context-aware replay and navigation

But they are treated as legacy records for editing:

- they can still be loaded and solved
- they do not support form-mode edit

The UI should disable edit for those puzzles instead of trying to reconstruct a
 possibly incorrect form state.

### Update flow

Edit mode reuses the same modal as create mode.

The flow is:

1. Load a personal puzzle by slug or open one from the user puzzle DB.
2. If the puzzle has edit metadata, open the modal in edit mode.
3. Prefill `whole line`, `start move number`, `start side`, `user moves first`,
   `rating`, and themes.
4. Save through `update_user_puzzle(...)`.
5. Keep the same `slug`.
6. Reload the updated puzzle into the active review session.

### Why slug stays stable

The external learning workflow references puzzles by `slug`, so edit support
 must update the same row in place instead of creating a replacement row with a
 new identifier.

## Clipboard Export

After creating or updating a personal puzzle, the app copies a review-friendly
 identifier string to the clipboard automatically.

Preferred format:

- `Opening Name<TAB>slug`

Example:

- `Italian Game: Classical Variation<TAB>pz_ab12cd34`

The opening name is derived from the puzzle's starting context using the
 existing opening lookup already available in the app. If no opening can be
 resolved, the clipboard falls back to the raw slug.

This avoids the extra manual step of focusing the slug field and copying it by
 hand before pasting it into an external review or learning workflow.
