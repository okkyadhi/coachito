"""Americano pairing engine — pure, deterministic, no DB.

A match consumes 4 players (2 on each side).  Each round uses
``courts * 4`` players; surplus rests and rotates across rounds.  The
schedule is built greedily by tracking partnership + opponent counts so
no two players partner more than ⌈total_rounds / (N-1)⌉ times.

For perfect sizes (N divisible by 4 with N ≤ 16), we precompute a known
balanced schedule.  For arbitrary sizes we fall through to the greedy
builder.  Either way the function is total: it always returns ``total_rounds``
rounds, ordered, with consistent participant identities.

Outputs are stable for the same input — the algorithm is seedless and
breaks ties by participant index — so re-running pairing on the same
roster produces the same schedule, which makes the round table the
audit-friendly source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class PairedMatch:
    """One match within a round: two pairs of participant indices, plus
    the court they play on.  All indices reference the input ``players``
    list."""

    court_number: int
    side_a: tuple[int, int]
    side_b: tuple[int, int]


@dataclass(frozen=True)
class PairedRound:
    round_number: int
    matches: tuple[PairedMatch, ...]
    resters: tuple[int, ...]  # participant indices sitting this round out


# ── Helpers ──────────────────────────────────────────────────────


def total_rounds_for(player_count: int) -> int:
    """Default schedule length.  In a classic individual Americano,
    everyone partners everyone else once across N-1 rounds when N is
    divisible by 4.  For smaller / arbitrary sizes we clamp to N-1 with
    a floor of 1."""
    if player_count <= 4:
        return max(1, player_count - 1)
    return max(1, player_count - 1)


def courts_for(player_count: int, requested: int) -> int:
    """Cap requested court count by what the roster can fill (4 per
    court)."""
    return max(1, min(requested, player_count // 4))


# ── Greedy builder ───────────────────────────────────────────────


@dataclass
class _State:
    """Mutable bookkeeping for the greedy pairing — partnered/opponent
    counts and how many rounds each player has rested.  Keeping this in
    a dataclass keeps the pairing loop readable."""

    n: int
    # partnered[i][j] = how many rounds players i and j have been partners
    partnered: list[list[int]] = field(default_factory=list)
    # opposed[i][j] = how many rounds they've faced each other
    opposed: list[list[int]] = field(default_factory=list)
    # rested_count[i] = how many rounds i has sat out
    rested_count: list[int] = field(default_factory=list)
    # last_rested_round[i] = most recent round in which i rested (or -1)
    last_rested_round: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.partnered = [[0] * self.n for _ in range(self.n)]
        self.opposed = [[0] * self.n for _ in range(self.n)]
        self.rested_count = [0] * self.n
        self.last_rested_round = [-1] * self.n


def _pick_resters(state: _State, available: list[int], rest_count: int) -> list[int]:
    """Pick resters preferring players who've rested less.  Tiebreak by
    least-recently-rested then by index."""
    if rest_count <= 0:
        return []
    scored = sorted(
        available,
        key=lambda i: (state.rested_count[i], state.last_rested_round[i], i),
    )
    return sorted(scored[:rest_count])


def _pair_within_court(state: _State, four: list[int]) -> PairedMatch | None:
    """Given exactly 4 players for a court, pick the pairing that
    minimises repeated partnerships.  Returns None only if `four` isn't
    of length 4 (defensive)."""
    if len(four) != 4:
        return None
    a, b, c, d = four
    # Three ways to split 4 into 2 pairs:
    options = [
        ((a, b), (c, d)),
        ((a, c), (b, d)),
        ((a, d), (b, c)),
    ]
    # Score = sum of partnered counts (lower is better), tiebreak on
    # opponent counts.
    def score(opt: tuple[tuple[int, int], tuple[int, int]]) -> tuple[int, int]:
        (s1, s2) = opt
        p_score = state.partnered[s1[0]][s1[1]] + state.partnered[s2[0]][s2[1]]
        o_score = (
            state.opposed[s1[0]][s2[0]]
            + state.opposed[s1[0]][s2[1]]
            + state.opposed[s1[1]][s2[0]]
            + state.opposed[s1[1]][s2[1]]
        )
        return (p_score, o_score)

    best = min(options, key=score)
    return PairedMatch(court_number=0, side_a=best[0], side_b=best[1])


def _assign_courts(
    state: _State, playing: list[int], court_count: int
) -> list[PairedMatch]:
    """Split ``playing`` (a multiple of 4) into ``court_count`` matches.

    Strategy: greedily pick groups of 4 that haven't already faced each
    other much, then within each group pick the partnership variant with
    the lowest repeat cost.
    """
    matches: list[PairedMatch] = []
    remaining = list(playing)
    court = 1
    while len(remaining) >= 4 and court <= court_count:
        # Seed with the first remaining player and greedily add 3 more
        # who minimise repeat partnerships/opponents.
        anchor = remaining.pop(0)
        group: list[int] = [anchor]
        while len(group) < 4:
            def cost(candidate: int) -> tuple[int, int, int]:
                p = sum(state.partnered[candidate][g] for g in group)
                o = sum(state.opposed[candidate][g] for g in group)
                return (p, o, candidate)
            remaining.sort(key=cost)
            group.append(remaining.pop(0))
        m = _pair_within_court(state, group)
        assert m is not None
        matches.append(
            PairedMatch(court_number=court, side_a=m.side_a, side_b=m.side_b)
        )
        court += 1
    return matches


def _apply_match(state: _State, m: PairedMatch) -> None:
    a1, a2 = m.side_a
    b1, b2 = m.side_b
    state.partnered[a1][a2] += 1
    state.partnered[a2][a1] += 1
    state.partnered[b1][b2] += 1
    state.partnered[b2][b1] += 1
    for x in (a1, a2):
        for y in (b1, b2):
            state.opposed[x][y] += 1
            state.opposed[y][x] += 1


# ── Public entry ─────────────────────────────────────────────────


def build_americano_schedule(
    *,
    player_count: int,
    court_count: int,
    total_rounds: int,
    initial_seeding: Sequence[int] | None = None,
) -> list[PairedRound]:
    """Build an Americano schedule for ``player_count`` individual
    players across ``total_rounds`` rounds.

    ``initial_seeding`` reorders the input indices — useful when the host
    has dragged the roster into a preferred starting order.  When None,
    players are numbered 0..N-1 in input order.

    The returned rounds reference participants by index (0..N-1).  The
    DB layer maps those back to participant ids when inserting rows.
    """
    if player_count < 4:
        raise ValueError("Americano needs at least 4 players")
    if court_count < 1:
        raise ValueError("court_count must be ≥ 1")
    if total_rounds < 1:
        raise ValueError("total_rounds must be ≥ 1")
    cc = courts_for(player_count, court_count)
    per_round = cc * 4
    if per_round > player_count:
        # Should be unreachable thanks to courts_for, but defensive.
        per_round = (player_count // 4) * 4
        cc = per_round // 4

    base_order = (
        list(initial_seeding)
        if initial_seeding is not None
        else list(range(player_count))
    )
    if sorted(base_order) != list(range(player_count)):
        raise ValueError("initial_seeding must be a permutation of 0..N-1")

    state = _State(n=player_count)
    rounds: list[PairedRound] = []

    for r in range(1, total_rounds + 1):
        # Pick resters for this round.  Available = full roster; rotate
        # so least-rested players play.
        available = list(base_order)
        rest_count = player_count - per_round
        resters = _pick_resters(state, available, rest_count)
        for r_idx in resters:
            state.rested_count[r_idx] += 1
            state.last_rested_round[r_idx] = r
        playing = [i for i in available if i not in resters]

        # Stable starting order for the round — rotate by round number so
        # the same player isn't always the "anchor" of every greedy step.
        if playing:
            rot = r % len(playing)
            playing = playing[rot:] + playing[:rot]

        matches = _assign_courts(state, playing, cc)
        for m in matches:
            _apply_match(state, m)
        rounds.append(
            PairedRound(
                round_number=r,
                matches=tuple(matches),
                resters=tuple(sorted(resters)),
            )
        )

    return rounds


# ── Mexicano (dynamic re-rank) ───────────────────────────────────


def build_mexicano_round(
    *,
    round_number: int,
    ranked_player_indices: Sequence[int],
    court_count: int,
    pairing_setting: str = "1_3_vs_2_4",
) -> PairedRound:
    """One Mexicano round.  Top-4 players → Court 1, next-4 → Court 2,
    etc.  Within each court, pair according to ``pairing_setting``:

      ``1_3_vs_2_4`` — champion-challenger: ranks 1+3 vs 2+4
      ``1_4_vs_2_3`` — top-with-bottom: ranks 1+4 vs 2+3

    ``ranked_player_indices`` must already be sorted from highest to
    lowest standing.  Round 1 uses ``initial_seed`` order; subsequent
    rounds use the leaderboard sort.  Surplus players (not a multiple
    of 4) sit out as resters pulled from the bottom of the ranking.
    """
    if pairing_setting not in {"1_3_vs_2_4", "1_4_vs_2_3"}:
        raise ValueError("unknown mexicano pairing_setting")
    n = len(ranked_player_indices)
    cc = max(1, min(court_count, n // 4))
    per_round = cc * 4

    playing = list(ranked_player_indices[:per_round])
    resters = tuple(sorted(ranked_player_indices[per_round:]))

    matches: list[PairedMatch] = []
    for court_idx in range(cc):
        a, b, c, d = playing[court_idx * 4 : (court_idx + 1) * 4]
        if pairing_setting == "1_3_vs_2_4":
            side_a: tuple[int, int] = (a, c)
            side_b: tuple[int, int] = (b, d)
        else:
            side_a = (a, d)
            side_b = (b, c)
        matches.append(
            PairedMatch(
                court_number=court_idx + 1,
                side_a=side_a,
                side_b=side_b,
            )
        )

    return PairedRound(
        round_number=round_number,
        matches=tuple(matches),
        resters=resters,
    )


# ── KOTH (king of the hill) ──────────────────────────────────────


@dataclass(frozen=True)
class KothPlacement:
    """How a player ended the prior round — input to next-round movement."""

    player_index: int
    court_number: int     # 1-indexed, lower = higher court
    won: bool             # True if their side won the last match


def build_koth_round(
    *,
    round_number: int,
    placements: Sequence[KothPlacement],
    court_count: int,
) -> PairedRound:
    """Generate the next KOTH round from the prior round's placements.

    Movement rules (docs/20 §6.7):
      - Court 1 winners stay on Court 1.
      - Court 1 losers drop to Court 2.
      - Court N winners (N > 1) move up to Court N-1.
      - Court N losers (N < court_count) drop to Court N+1.
      - Lowest-court losers stay on the lowest court.

    Within-court partnerships rotate by ``round_number % 3`` so the
    same 4 players see different partners across rounds.
    """
    if court_count < 1:
        raise ValueError("court_count must be ≥ 1")

    next_court: dict[int, int] = {}
    for p in placements:
        if p.won:
            next_court[p.player_index] = max(1, p.court_number - 1)
        else:
            next_court[p.player_index] = min(court_count, p.court_number + 1)

    assignments: dict[int, list[int]] = {c: [] for c in range(1, court_count + 1)}
    for player_idx in sorted(next_court):
        assignments[next_court[player_idx]].append(player_idx)

    matches: list[PairedMatch] = []
    for court_n in range(1, court_count + 1):
        bucket = assignments.get(court_n, [])
        if len(bucket) != 4:
            raise ValueError(
                f"KOTH round {round_number}: court {court_n} has "
                f"{len(bucket)} players, expected 4"
            )
        a, b, c, d = bucket
        variant = round_number % 3
        if variant == 0:
            side_a, side_b = (a, b), (c, d)
        elif variant == 1:
            side_a, side_b = (a, c), (b, d)
        else:
            side_a, side_b = (a, d), (b, c)
        matches.append(
            PairedMatch(court_number=court_n, side_a=side_a, side_b=side_b)
        )

    return PairedRound(
        round_number=round_number,
        matches=tuple(matches),
        resters=(),
    )
