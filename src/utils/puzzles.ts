import { parseUci } from "chessops";
import { makeFen } from "chessops/fen";
import { makeSan } from "chessops/san";
import { resolve } from "@tauri-apps/api/path";
import { readDir } from "@tauri-apps/plugin-fs";
import { commands, type PuzzleDatabaseInfo } from "@/bindings";
import { positionFromFen } from "@/utils/chessops";
import { getPuzzlesDir } from "@/utils/directories";
import { createNode, defaultTree, type TreeState } from "./treeReducer";
import { unwrap } from "./unwrap";

export type Completion = "correct" | "incorrect" | "incomplete";

export interface Puzzle {
    id: number;
    slug?: string | null;
    source_fen?: string | null;
    context_moves?: string[];
    line_text?: string | null;
    start_move_number?: number | null;
    start_side?: string | null;
    fen: string;
    moves: string[];
    user_moves_first: boolean;
    rating: number;
    rating_deviation: number;
    popularity: number;
    nb_plays: number;
    completion: Completion;
    timeSpent?: number;
    themes?: string[];
}

export interface CreateUserPuzzlePayload {
    lineText: string;
    startMoveNumber: number;
    startSide: string;
    userMovesFirst: boolean;
    rating: number;
    ratingDeviation?: number | null;
    popularity?: number | null;
    nbPlays?: number | null;
    themes: string[];
}

async function getPuzzleDatabase(name: string): Promise<PuzzleDatabaseInfo> {
    const puzzlesDir = await getPuzzlesDir();
    const path = await resolve(puzzlesDir, name);
    return unwrap(await commands.getPuzzleDbInfo(path));
}

export async function getPuzzleDatabases(): Promise<PuzzleDatabaseInfo[]> {
    const puzzlesDir = await getPuzzlesDir();
    const files = await readDir(puzzlesDir);
    const dbs = files.filter((file) => file.name?.endsWith(".db3"));
    return (await Promise.allSettled(dbs.map((db) => getPuzzleDatabase(db.name))))
        .filter((r) => r.status === "fulfilled")
        .map((r) => (r as PromiseFulfilledResult<PuzzleDatabaseInfo>).value);
}

export async function getUserPuzzleDbPath(): Promise<string> {
    const puzzlesDir = await getPuzzlesDir();
    return resolve(puzzlesDir, "user-puzzles.db3");
}

export function buildPuzzleTreeState(puzzle: Puzzle): TreeState {
    const sourceFen = puzzle.source_fen || puzzle.fen;
    const contextMoves = puzzle.context_moves ?? [];
    const allMoves = [...contextMoves, ...puzzle.moves];
    const tree = defaultTree(sourceFen);
    const [pos] = positionFromFen(sourceFen);

    if (!pos) {
        return tree;
    }

    let parent = tree.root;
    for (const moveText of allMoves) {
        const move = parseUci(moveText);
        if (!move) {
            break;
        }
        const san = makeSan(pos, move);
        pos.play(move);
        const nextNode = createNode({
            fen: makeFen(pos.toSetup()),
            move,
            san,
            halfMoves: parent.halfMoves + 1,
        });
        parent.children = [nextNode];
        parent = nextNode;
    }

    const contextLength = contextMoves.length;
    const visibleStart = contextLength + (puzzle.user_moves_first ? 0 : Math.min(1, puzzle.moves.length));
    const startPath = Array.from({ length: visibleStart }, () => 0);
    tree.position = startPath;
    tree.headers.start = startPath;
    tree.headers.reveal = startPath;
    return tree;
}
