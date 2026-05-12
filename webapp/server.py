"""FastAPI app for the poker bot tournament demo."""

from __future__ import annotations

import ast
import contextlib
import io
import os
import sys
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from poker_tournament import Tournament, load_bot  # noqa: E402
from poker_tournament.tournament import MAX_BOTS  # noqa: E402

BOTS_DIR = os.path.join(ROOT_DIR, "bots")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class BotInfo(BaseModel):
    name: str
    filename: str
    tier: str
    description: str
    source: str


class BotListResponse(BaseModel):
    bots: List[BotInfo]


class TournamentRequest(BaseModel):
    bots: List[str] = Field(..., min_length=2, max_length=MAX_BOTS)
    mode: str = Field("fixed")
    starting_chips: int = Field(1000, ge=2, le=1_000_000)
    small_blind: int = Field(10, ge=1, le=1_000_000)
    big_blind: int = Field(20, ge=2, le=1_000_000)
    num_hands: int = Field(25, ge=1, le=500)
    seed: Optional[int] = Field(None, ge=0, le=2_147_483_647)
    verbose: bool = Field(False)

    @field_validator("mode")
    @classmethod
    def check_mode(cls, value: str) -> str:
        if value not in {"fixed", "elimination"}:
            raise ValueError("mode must be 'fixed' or 'elimination'")
        return value

    @field_validator("bots")
    @classmethod
    def check_bot_filenames(cls, value: List[str]) -> List[str]:
        for filename in value:
            if (
                "/" in filename
                or "\\" in filename
                or filename.startswith(".")
                or not filename.endswith(".py")
            ):
                raise ValueError(f"Invalid bot filename: {filename!r}")
        return value


class StandingEntry(BaseModel):
    rank: int
    name: str
    chips: int
    hands_played: int
    status: str


class TournamentResponse(BaseModel):
    standings: List[StandingEntry]
    hands: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    hands_played: int
    duration_ms: int
    config: Dict[str, Any]
    log: str


class BatchRequest(TournamentRequest):
    runs: int = Field(50, ge=1, le=250)


class BatchStandingEntry(BaseModel):
    rank: int
    name: str
    wins: int
    win_rate: float
    average_rank: float
    average_chips: float


class BatchResponse(BaseModel):
    results: List[BatchStandingEntry]
    runs: int
    duration_ms: int
    config: Dict[str, Any]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Poker Bot Tournament",
        description="Workshop-friendly Texas Hold'em bot tournament.",
        version="1.0.0",
    )

    @app.get("/api/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/bots", response_model=BotListResponse)
    def list_bots() -> BotListResponse:
        return BotListResponse(bots=_list_bot_files())

    @app.post("/api/tournament", response_model=TournamentResponse)
    def run_tournament(request: TournamentRequest) -> TournamentResponse:
        _validate_blinds(request)

        bots = _load_selected_bots(request.bots)
        tournament = Tournament(
            bots=bots,
            starting_chips=request.starting_chips,
            small_blind=request.small_blind,
            big_blind=request.big_blind,
            mode=request.mode,
            num_hands=request.num_hands,
            verbose=request.verbose,
            seed=request.seed,
        )

        captured = io.StringIO()
        start = time.perf_counter()
        with contextlib.redirect_stdout(captured):
            standings = tournament.run()
        duration_ms = int((time.perf_counter() - start) * 1000)
        payload = tournament.to_payload()

        return TournamentResponse(
            standings=[StandingEntry(**row) for row in standings],
            hands=payload["hands"],
            events=payload["events"],
            hands_played=payload["hands_played"],
            duration_ms=duration_ms,
            config=payload["config"],
            log=captured.getvalue(),
        )

    @app.post("/api/batch", response_model=BatchResponse)
    def run_batch(request: BatchRequest) -> BatchResponse:
        _validate_blinds(request)

        bots = _load_selected_bots(request.bots)
        wins: Dict[str, int] = defaultdict(int)
        rank_totals: Dict[str, int] = defaultdict(int)
        chip_totals: Dict[str, int] = defaultdict(int)

        start = time.perf_counter()
        for index in range(request.runs):
            seed = None if request.seed is None else request.seed + index
            tournament = Tournament(
                bots=bots,
                starting_chips=request.starting_chips,
                small_blind=request.small_blind,
                big_blind=request.big_blind,
                mode=request.mode,
                num_hands=request.num_hands,
                verbose=False,
                seed=seed,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                standings = tournament.run()

            if standings:
                wins[standings[0]["name"]] += 1
            for row in standings:
                rank_totals[row["name"]] += row["rank"]
                chip_totals[row["name"]] += row["chips"]

        duration_ms = int((time.perf_counter() - start) * 1000)
        names = [name for name, _ in Tournament(bots, verbose=False)._unique_bots()]
        results = [
            BatchStandingEntry(
                rank=0,
                name=name,
                wins=wins[name],
                win_rate=round(wins[name] / request.runs, 4),
                average_rank=round(rank_totals[name] / request.runs, 2),
                average_chips=round(chip_totals[name] / request.runs, 2),
            )
            for name in names
        ]
        results.sort(key=lambda row: (-row.wins, row.average_rank, -row.average_chips, row.name))
        for rank, row in enumerate(results, start=1):
            row.rank = rank

        return BatchResponse(
            results=results,
            runs=request.runs,
            duration_ms=duration_ms,
            config={
                "mode": request.mode,
                "starting_chips": request.starting_chips,
                "small_blind": request.small_blind,
                "big_blind": request.big_blind,
                "num_hands": request.num_hands,
                "seed": request.seed,
                "bots": request.bots,
            },
        )

    if os.path.isdir(STATIC_DIR):
        app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    return app


def _validate_blinds(request: TournamentRequest) -> None:
    if request.small_blind >= request.big_blind:
        raise HTTPException(
            status_code=400,
            detail="small_blind must be smaller than big_blind.",
        )


def _list_bot_files() -> List[BotInfo]:
    if not os.path.isdir(BOTS_DIR):
        return []

    bots: List[BotInfo] = []
    for filename in sorted(os.listdir(BOTS_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        path = os.path.join(BOTS_DIR, filename)
        try:
            name, _ = load_bot(path)
        except Exception:
            continue
        source = _read_text(path)
        bots.append(
            BotInfo(
                name=name,
                filename=filename,
                tier=_string_constant_from_source(source, "TIER", "basic"),
                description=_description_from_source(source),
                source=source,
            )
        )
    return bots


def _load_selected_bots(filenames: List[str]) -> List[Tuple[str, Callable]]:
    loaded = []
    for filename in filenames:
        path = os.path.join(BOTS_DIR, filename)
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"Bot file not found: {filename}")
        try:
            loaded.append(load_bot(path))
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not load {filename}: {exc}",
            ) from exc
    return loaded


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip() + "\n"


def _description_from_source(source: str) -> str:
    description = _string_constant_from_source(source, "DESCRIPTION", "")
    if description:
        return description

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""

    docstring = ast.get_docstring(tree) or ""
    return docstring.splitlines()[0] if docstring else ""


def _string_constant_from_source(source: str, name: str, default: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return default

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return default


app = create_app()
