import {
  Alert,
  Button,
  Group,
  List,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconX } from "@tabler/icons-react";
import { parseUci } from "chessops";
import { makeFen } from "chessops/fen";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands, type Puzzle as BoundPuzzle, type PuzzleDatabaseInfo } from "@/bindings";
import { positionFromFen } from "@/utils/chessops";
import { getPuzzleDatabases, getUserPuzzleDbPath, type Puzzle as FrontendPuzzle } from "@/utils/puzzles";
import { unwrap } from "@/utils/unwrap";

type CreateResult = {
  dbs: PuzzleDatabaseInfo[];
  dbPath: string;
  puzzle: BoundPuzzle;
  slug: string;
};

type EditablePersonalPuzzle = FrontendPuzzle;

function estimatePlyCount(lineText: string): number {
  return lineText
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .filter((token) => !token.match(/^[\d.]+$/))
    .filter((token) => !["*", "1-0", "0-1", "1/2-1/2"].includes(token)).length;
}

function computeSplitPly(
  startMoveNumber: number,
  startSide: "white" | "black",
  totalPlies: number,
): number | null {
  let moveNumber = 1;
  let side: "white" | "black" = "white";
  for (let ply = 0; ply < totalPlies; ply++) {
    if (moveNumber === startMoveNumber && side === startSide) {
      return ply;
    }
    if (side === "white") {
      side = "black";
    } else {
      side = "white";
      moveNumber += 1;
    }
  }

  return null;
}

function validatePuzzleDefinition(
  lineText: string,
  startMoveNumber: number,
  startSide: "white" | "black",
  userMovesFirst: boolean,
): string | null {
  if (!lineText.trim()) {
    return "A full move line is required.";
  }

  const totalPlies = estimatePlyCount(lineText);
  if (totalPlies === 0) {
    return "The move line did not contain any playable moves.";
  }

  const splitPly = computeSplitPly(startMoveNumber, startSide, totalPlies);
  if (splitPly === null) {
    return "Start move could not be matched inside the provided line.";
  }

  const solutionPlies = totalPlies - splitPly;
  if (!userMovesFirst && solutionPlies < 2) {
    return "At least two solution plies are required when the user does not move first.";
  }

  return null;
}

async function getClipboardLabel(puzzle: BoundPuzzle, slug: string): Promise<string> {
  const sourceFen = puzzle.source_fen ?? puzzle.fen;
  const contextMoves = puzzle.context_moves?.split(" ").filter(Boolean) ?? [];
  const solutionMoves = puzzle.moves.split(" ").filter(Boolean);
  const allMoves = [...contextMoves, ...solutionMoves];
  const fens = [sourceFen];
  const [pos] = positionFromFen(sourceFen);

  if (pos) {
    for (const moveText of allMoves) {
      const move = parseUci(moveText);
      if (!move) {
        break;
      }
      pos.play(move);
      fens.push(makeFen(pos.toSetup()));
    }
  }

  const openingResult = await commands.getOpeningFromFens(fens);
  if (openingResult.status === "ok" && openingResult.data.trim()) {
    return `${openingResult.data}\t${slug}`;
  }

  return slug;
}

export default function PersonalPuzzleModal({
  opened,
  setOpened,
  mode,
  initialPuzzle,
  dbPath,
  onSaved,
}: {
  opened: boolean;
  setOpened: (opened: boolean) => void;
  mode: "create" | "edit";
  initialPuzzle?: EditablePersonalPuzzle | null;
  dbPath?: string | null;
  onSaved: (result: CreateResult) => void;
}) {
  const { t } = useTranslation();
  const [lineText, setLineText] = useState("");
  const [startMoveNumber, setStartMoveNumber] = useState(1);
  const [startSide, setStartSide] = useState<"white" | "black">("white");
  const [userMovesFirst, setUserMovesFirst] = useState(true);
  const [rating, setRating] = useState(600);
  const [themes, setThemes] = useState<string[]>([]);
  const [availableThemes, setAvailableThemes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isEdit = mode === "edit";

  useEffect(() => {
    if (!opened) return;

    setError(null);
    const resolvedDbPathPromise = dbPath ? Promise.resolve(dbPath) : getUserPuzzleDbPath();
    resolvedDbPathPromise.then((resolvedDbPath) => {
      commands.getPuzzleThemes(resolvedDbPath).then((result) => {
        if (result.status === "ok") {
          setAvailableThemes(result.data);
        } else {
          setAvailableThemes([]);
        }
      });

      if (isEdit && initialPuzzle?.id) {
        if (initialPuzzle.themes?.length) {
          setThemes(initialPuzzle.themes);
        } else {
          commands.getThemesForPuzzle(resolvedDbPath, initialPuzzle.id).then((result) => {
            if (result.status === "ok") {
              setThemes(result.data);
            }
          });
        }
      }
    });

    if (isEdit && initialPuzzle) {
      setLineText(initialPuzzle.line_text ?? "");
      setStartMoveNumber(initialPuzzle.start_move_number ?? 1);
      setStartSide((initialPuzzle.start_side as "white" | "black") ?? "white");
      setUserMovesFirst(initialPuzzle.user_moves_first);
      setRating(initialPuzzle.rating);
      if (initialPuzzle.themes?.length) {
        setThemes(initialPuzzle.themes);
      } else {
        setThemes([]);
      }
      return;
    }

    setLineText("");
    setStartMoveNumber(1);
    setStartSide("white");
    setUserMovesFirst(true);
    setRating(600);
    setThemes([]);
  }, [opened, dbPath, initialPuzzle, isEdit]);

  const estimatedPlyCount = estimatePlyCount(lineText);
  const computedSplitPly = computeSplitPly(startMoveNumber, startSide, estimatedPlyCount);
  const estimatedSolutionPlies =
    computedSplitPly === null ? 0 : Math.max(0, estimatedPlyCount - computedSplitPly);

  async function handleSubmit() {
    const validationError = validatePuzzleDefinition(
      lineText,
      startMoveNumber,
      startSide,
      userMovesFirst,
    );
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const resolvedDbPath = dbPath ?? (await getUserPuzzleDbPath());
      const payload = {
          lineText: lineText.trim(),
          startMoveNumber,
          startSide,
          userMovesFirst,
          rating,
          ratingDeviation: 0,
          popularity: 0,
          nbPlays: 0,
          themes,
        };
      const saveResult = unwrap(
        isEdit && initialPuzzle?.slug
          ? await commands.updateUserPuzzle(resolvedDbPath, initialPuzzle.slug, payload)
          : await commands.createUserPuzzle(resolvedDbPath, payload),
      );
      const puzzle = unwrap(await commands.getPuzzleBySlug(saveResult.dbPath, saveResult.slug));
      const dbs = await getPuzzleDatabases();
      const clipboardText = await getClipboardLabel(puzzle, saveResult.slug);
      const copiedToClipboard = await navigator.clipboard
        ?.writeText(clipboardText)
        .then(() => true)
        .catch(() => false);

      notifications.show({
        title: isEdit ? "Personal puzzle updated" : "Personal puzzle saved",
        message: copiedToClipboard
          ? `Copied to clipboard: ${clipboardText}`
          : `Slug: ${saveResult.slug}`,
        color: "green",
        icon: <IconCheck />,
      });

      onSaved({
        dbs,
        dbPath: saveResult.dbPath,
        puzzle,
        slug: saveResult.slug,
      });

      setLineText("");
      setStartMoveNumber(1);
      setStartSide("white");
      setUserMovesFirst(true);
        setRating(600);
      setThemes([]);
      setOpened(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${isEdit ? "update" : "create"} puzzle.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={() => setOpened(false)}
      title={isEdit ? "Edit Personal Puzzle" : "Create Personal Puzzle"}
      size="lg"
    >
      <Stack>
        {error && (
          <Alert color="red" icon={<IconX size={16} />}>
            {error}
          </Alert>
        )}
        <Textarea
          label="Whole Line"
          description="Paste the full line from the normal starting position, then choose where the puzzle starts."
          placeholder="1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5"
          minRows={3}
          autosize
          value={lineText}
          onChange={(event) => setLineText(event.currentTarget.value)}
        />
        <Group grow align="flex-start">
          <NumberInput
            label="Start Move Number"
            description="Move number where the puzzle begins."
            min={1}
            value={startMoveNumber}
            onChange={(value) => setStartMoveNumber(typeof value === "number" ? value : 1)}
          />
          <Select
            label="Start Side"
            description="Which side plays the first puzzle move."
            data={[
              { label: "White", value: "white" },
              { label: "Black", value: "black" },
            ]}
            value={startSide}
            allowDeselect={false}
            onChange={(value) => setStartSide((value as "white" | "black") || "white")}
          />
          <NumberInput
            label={t("Puzzle.Rating")}
            min={0}
            max={4000}
            value={rating}
              onChange={(value) => setRating(typeof value === "number" ? value : 600)}
            />
          <Switch
            mt={30}
            label="User moves first"
            checked={userMovesFirst}
            onChange={(event) => setUserMovesFirst(event.currentTarget.checked)}
          />
        </Group>
        <Alert color="blue">
          <List size="sm">
            <List.Item>{`Estimated total plies: ${estimatedPlyCount}`}</List.Item>
            <List.Item>{`Estimated solution plies: ${estimatedSolutionPlies}`}</List.Item>
            <List.Item>{`Puzzle starts at: ${startMoveNumber}-${startSide === "white" ? "1" : "2"}`}</List.Item>
            {computedSplitPly !== null && (
              <List.Item>{`Computed split ply: ${computedSplitPly}`}</List.Item>
            )}
          </List>
        </Alert>
        <div>
          <Text size="sm" fw={500} mb={6}>
            Theme
          </Text>
          <TagsInput
            placeholder="fork mate"
            data={availableThemes}
            value={themes}
            onChange={setThemes}
            clearable
          />
        </div>
        <Button onClick={handleSubmit} loading={submitting}>
          {isEdit ? "Save Changes" : "Save Puzzle"}
        </Button>
      </Stack>
    </Modal>
  );
}
