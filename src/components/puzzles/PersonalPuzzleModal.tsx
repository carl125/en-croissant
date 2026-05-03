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
import { parseFen } from "chessops/fen";
import { IconCheck, IconX } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands, type Puzzle as BoundPuzzle, type PuzzleDatabaseInfo } from "@/bindings";
import { positionFromFen } from "@/utils/chessops";
import { getPuzzleDatabases, getUserPuzzleDbPath } from "@/utils/puzzles";
import { unwrap } from "@/utils/unwrap";

type CreateResult = {
  dbs: PuzzleDatabaseInfo[];
  dbPath: string;
  puzzle: BoundPuzzle;
  slug: string;
};

function estimatePlyCount(lineText: string): number {
  return lineText
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .filter((token) => !token.match(/^[\d.]+$/))
    .filter((token) => !["*", "1-0", "0-1", "1/2-1/2"].includes(token)).length;
}

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function getFenMoveStart(sourceFen: string): { moveNumber: number; side: "white" | "black" } | null {
  try {
    const setup = parseFen(sourceFen).unwrap();
    return {
      moveNumber: setup.fullmoves,
      side: setup.turn,
    };
  } catch {
    return null;
  }
}

function computeSplitPly(
  sourceFen: string,
  startMoveNumber: number,
  startSide: "white" | "black",
  totalPlies: number,
): number | null {
  const fenStart = getFenMoveStart(sourceFen);
  if (!fenStart) {
    return null;
  }

  let moveNumber = fenStart.moveNumber;
  let side: "white" | "black" = fenStart.side;
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
  const [pos, error] = positionFromFen(STARTING_FEN);
  if (error || !pos) {
    return "Invalid source FEN.";
  }

  if (!lineText.trim()) {
    return "A full move line is required.";
  }

  const totalPlies = estimatePlyCount(lineText);
  if (totalPlies === 0) {
    return "The move line did not contain any playable moves.";
  }

  const splitPly = computeSplitPly(STARTING_FEN, startMoveNumber, startSide, totalPlies);
  if (splitPly === null) {
    return "Start move could not be matched inside the provided line.";
  }

  const solutionPlies = totalPlies - splitPly;
  if (!userMovesFirst && solutionPlies < 2) {
    return "At least two solution plies are required when the user does not move first.";
  }

  return null;
}

export default function PersonalPuzzleModal({
  opened,
  setOpened,
  onCreated,
}: {
  opened: boolean;
  setOpened: (opened: boolean) => void;
  onCreated: (result: CreateResult) => void;
}) {
  const { t } = useTranslation();
  const [lineText, setLineText] = useState("");
  const [startMoveNumber, setStartMoveNumber] = useState(1);
  const [startSide, setStartSide] = useState<"white" | "black">("white");
  const [userMovesFirst, setUserMovesFirst] = useState(true);
  const [rating, setRating] = useState(1500);
  const [themes, setThemes] = useState<string[]>([]);
  const [availableThemes, setAvailableThemes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!opened) return;

    setError(null);
    getUserPuzzleDbPath().then((dbPath) => {
      commands.getPuzzleThemes(dbPath).then((result) => {
        if (result.status === "ok") {
          setAvailableThemes(result.data);
        } else {
          setAvailableThemes([]);
        }
      });
    });
  }, [opened]);

  const estimatedPlyCount = estimatePlyCount(lineText);
  const computedSplitPly = computeSplitPly(
    STARTING_FEN,
    startMoveNumber,
    startSide,
    estimatedPlyCount,
  );
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
      const dbPath = await getUserPuzzleDbPath();
      const createResult = unwrap(
        await commands.createUserPuzzle(dbPath, {
          lineText: lineText.trim(),
          startMoveNumber,
          startSide,
          userMovesFirst,
          rating,
          ratingDeviation: 0,
          popularity: 0,
          nbPlays: 0,
          themes,
        }),
      );
      const puzzle = unwrap(await commands.getPuzzleBySlug(createResult.dbPath, createResult.slug));
      const dbs = await getPuzzleDatabases();

      notifications.show({
        title: "Personal puzzle saved",
        message: `Slug: ${createResult.slug}`,
        color: "green",
        icon: <IconCheck />,
      });

      onCreated({
        dbs,
        dbPath: createResult.dbPath,
        puzzle,
        slug: createResult.slug,
      });

      setLineText("");
      setStartMoveNumber(1);
      setStartSide("white");
      setUserMovesFirst(true);
      setRating(1500);
      setThemes([]);
      setOpened(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create puzzle.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal opened={opened} onClose={() => setOpened(false)} title="Create Personal Puzzle" size="lg">
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
            onChange={(value) => setRating(typeof value === "number" ? value : 1500)}
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
          Save Puzzle
        </Button>
      </Stack>
    </Modal>
  );
}
