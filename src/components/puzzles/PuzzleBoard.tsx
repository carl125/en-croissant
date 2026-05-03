import { Box } from "@mantine/core";
import { useElementSize, useForceUpdate } from "@mantine/hooks";
import { type Move, makeUci, type NormalMove, parseSquare } from "chessops";
import { chessgroundDests, chessgroundMove } from "chessops/compat";
import { parseFen } from "chessops/fen";
import equal from "fast-deep-equal";
import { useAtom, useAtomValue } from "jotai";
import { useContext, useEffect, useRef, useState } from "react";
import { useStore } from "zustand";
import { Chessground } from "@/chessground/Chessground";
import { jumpToNextPuzzleAtom, moveHighlightAtom, showCoordinatesAtom } from "@/state/atoms";
import classes from "@/styles/Chessboard.module.css";
import { positionFromFen } from "@/utils/chessops";
import type { Completion, Puzzle } from "@/utils/puzzles";
import { getNodeAtPath } from "@/utils/treeReducer";
import PromotionModal from "../boards/PromotionModal";
import { TreeStateContext } from "../common/TreeStateContext";

const PUZZLE_REPLY_DELAY_MS = 400;
const PUZZLE_INCORRECT_REVERT_DELAY_MS = 500;

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function PuzzleBoard({
  puzzles,
  currentPuzzle,
  changeCompletion,
  generatePuzzle,
  db,
}: {
  puzzles: Puzzle[];
  currentPuzzle: number;
  changeCompletion: (completion: Completion) => Promise<void>;
  generatePuzzle: (db: string) => Promise<void>;
  db: string | null;
}) {
  const store = useContext(TreeStateContext)!;
  const root = useStore(store, (s) => s.root);
  const position = useStore(store, (s) => s.position);
  const moveHighlight = useAtomValue(moveHighlightAtom);
  const boardShapes = useStore(store, (s) => s.currentNode().shapes);
  const makeMove = useStore(store, (s) => s.makeMove);
  const makeMoves = useStore(store, (s) => s.makeMoves);
  const goToPrevious = useStore(store, (s) => s.goToPrevious);
  const reset = useForceUpdate();
  const [jumpToNextPuzzleImmediately] = useAtom(jumpToNextPuzzleAtom);

  const currentNode = getNodeAtPath(root, position);

  let puzzle: Puzzle | null = null;
  if (puzzles.length > 0) {
    puzzle = puzzles[currentPuzzle];
  }
  const [ended, setEnded] = useState(false);
  const replySequenceRef = useRef(0);

  useEffect(() => {
    replySequenceRef.current += 1;
  }, [currentPuzzle]);

  useEffect(() => {
    return () => {
      replySequenceRef.current += 1;
    };
  }, []);

  const [pos] = positionFromFen(currentNode.fen);

  const contextLength = puzzle?.context_moves?.length ?? 0;
  const currentMove = puzzle ? Math.max(0, position.length - contextLength) : 0;
  const orientation = puzzle?.fen
    ? parseFen(puzzle.fen).unwrap().turn === "white"
      ? "white"
      : "black"
    : "white";
  const [pendingMove, setPendingMove] = useState<NormalMove | null>(null);

  const dests = pos ? chessgroundDests(pos) : new Map();
  const turn = pos?.turn || "white";
  const showCoordinates = useAtomValue(showCoordinatesAtom);

  async function checkMove(move: Move) {
    if (!pos) return;
    if (!puzzle) return;

    const newPos = pos.clone();
    const uci = makeUci(move);
    newPos.play(move);

    if (puzzle.moves[currentMove] === uci || newPos.isCheckmate()) {
      const replySequence = ++replySequenceRef.current;
      makeMoves({
        payload: [uci],
        mainline: true,
        changeHeaders: false,
      });
      reset();

      if (currentMove === puzzle.moves.length - 1) {
        if (puzzle.completion !== "incorrect") {
          await changeCompletion("correct");
        }
        setEnded(false);

        if (db && jumpToNextPuzzleImmediately) {
          await generatePuzzle(db);
          reset();
          return;
        }
        return;
      }

      const replyUci = puzzle.moves[currentMove + 1];
      if (replyUci) {
        await delay(PUZZLE_REPLY_DELAY_MS);
        if (replySequence !== replySequenceRef.current) {
          return;
        }
        makeMoves({
          payload: [replyUci],
          mainline: true,
          changeHeaders: false,
        });
      }
    } else {
      const replySequence = ++replySequenceRef.current;
      makeMove({
        payload: move,
        changeHeaders: false,
      });
      reset();
      if (!ended) {
        await changeCompletion("incorrect");
      }
      setEnded(true);
      await delay(PUZZLE_INCORRECT_REVERT_DELAY_MS);
      if (replySequence !== replySequenceRef.current) {
        return;
      }
      goToPrevious();
      reset();
    }
  }

  const { ref: parentRef, height: parentHeight } = useElementSize();

  return (
    <Box w="100%" h="100%" ref={parentRef}>
      <Box
        className={classes.chessboard}
        style={{
          maxWidth: parentHeight,
        }}
      >
        <PromotionModal
          pendingMove={pendingMove}
          cancelMove={() => setPendingMove(null)}
          confirmMove={async (p) => {
            if (pendingMove) {
              await checkMove({ ...pendingMove, promotion: p });
              setPendingMove(null);
            }
          }}
          turn={turn}
          orientation={orientation}
        />
        <Chessground
          animation={{
            enabled: true,
          }}
          coordinates={showCoordinates !== "no"}
          coordinatesOnSquares={showCoordinates === "all"}
          orientation={orientation}
          drawable={{
            enabled: true,
            visible: true,
            autoShapes: boardShapes,
          }}
          movable={{
            free: false,
            color:
              puzzle &&
              equal(position, Array.from({ length: currentMove + contextLength }, () => 0)) &&
              (puzzle.completion === "incomplete" || puzzle.completion === "incorrect")
                ? turn
                : undefined,
            dests: dests,
            events: {
              after: (orig, dest) => {
                const from = parseSquare(orig)!;
                const to = parseSquare(dest)!;
                const move: NormalMove = { from, to };
                if (
                  pos?.board.get(from)?.role === "pawn" &&
                  ((dest[1] === "8" && turn === "white") || (dest[1] === "1" && turn === "black"))
                ) {
                  setPendingMove(move);
                } else {
                  checkMove(move);
                }
              },
            },
          }}
          lastMove={
            moveHighlight && currentNode.move ? chessgroundMove(currentNode.move) : undefined
          }
          turnColor={turn}
          fen={currentNode.fen}
          check={moveHighlight && pos?.isCheck()}
        />
      </Box>
    </Box>
  );
}

export default PuzzleBoard;
