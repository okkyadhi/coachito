"""Build the monthly-report data dict + render the Jinja2 template + run
WeasyPrint to produce the final PDF bytes.

Lives outside the FastAPI request cycle — the worker calls this from an RQ
job.  Uses asyncpg directly (RLS-bypass) so we don't have to plumb auth or
sessions into the worker.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import asyncpg
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import CSS, HTML

from src.invites.og_landing import _superuser_dsn

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

_DEFAULT_ACCENT = "#C66B47"  # Coachito clay (was coachito blue #378ADD)
# Hard-coded radar geometry for the print-time SVG.  Smaller than the in-app
# version (140px) per docs/08 layout.
_RADAR_SIZE = 140
_RADAR_PAD = 20


# ── Public entry points ──────────────────────────────────────────


async def build_report_context(
    *,
    workspace_id: str,
    athlete_id: str,
    period_start: date,
    period_end: date,
    session_id: str | None = None,
) -> dict[str, Any]:
    """One asyncpg roundtrip per logical section.  Caller passes the result
    straight to ``render_report_pdf``.

    When ``session_id`` is set the report is scoped to that single session:
    sessions list contains only it, stats/gains use that session's date, and
    the cover swaps "Monthly progress" for "Session report"."""
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        ws = await _fetch_workspace(conn, workspace_id)
        athlete = await _fetch_athlete(conn, athlete_id)
        coach = await _fetch_lead_coach(conn, athlete_id, workspace_id)
        stats = await _fetch_period_stats(conn, athlete_id, period_start, period_end)
        tier = await _fetch_tier_progress(conn, athlete_id, workspace_id)
        category_averages = await _fetch_category_averages(conn, athlete_id, workspace_id)
        gains = await _fetch_recent_gains(conn, athlete_id, period_start, period_end)
        if session_id is not None:
            sessions = await _fetch_one_session(conn, athlete_id, session_id)
            stats = await _fetch_single_session_stats(conn, athlete_id, session_id)
            gains = await _fetch_session_gains(conn, athlete_id, session_id)
        else:
            sessions = await _fetch_sessions(conn, athlete_id, period_start, period_end)
        skill_detail = await _fetch_skill_detail(conn, athlete_id, workspace_id)
        coach_note = sessions[0]["summary"] if sessions and sessions[0]["summary"] else None
    finally:
        await conn.close()

    accent = (ws["brand_color"] or _DEFAULT_ACCENT).strip()
    is_session = session_id is not None
    if is_session and sessions:
        session_date = sessions[0]["raw_date"]
        period_block = {
            "label": session_date.strftime("%-d %B %Y"),
            "start": period_start,
            "end": period_end,
            "tagline": "Session report",
        }
    else:
        period_block = {
            "label": period_start.strftime("%B %Y"),
            "start": period_start,
            "end": period_end,
            "tagline": "Monthly progress",
        }

    # Split skill_detail into "fully unrated" (pending) vs "has at least one
    # rated skill" (rated_groups, the ones that print).  Mockup leads with
    # rated categories then namechecks the rest with a one-line "Not yet
    # assessed: ..." footnote — keeps the page editorial, not exhaustive.
    rated_groups: list[dict[str, Any]] = []
    pending_categories: list[str] = []
    for group in skill_detail:
        rated_skills = [s for s in group["skills"] if s.get("level")]
        if rated_skills:
            rated_groups.append({"category": group["category"], "skills": rated_skills})
        else:
            pending_categories.append(group["category"].capitalize())

    total_sessions = int(athlete["total_sessions"] or 0)
    if total_sessions == 0:
        total_sessions_label = "no sessions yet"
    elif total_sessions == 1:
        total_sessions_label = "first session"
    else:
        total_sessions_label = f"{total_sessions} sessions to date"

    # First session reads "Starting levels"; later reports read "Current
    # levels" — the same data, framed for where the trainee is in their arc.
    levels_heading = "Starting levels" if total_sessions <= 1 else "Current levels"

    return {
        "workspace": {
            "name": ws["workspace_name"],
            "logo_url": ws["logo_url"],
            "city": ws["city"],
            "sport_name": ws.get("sport_name"),
            "accent": accent,
            "accent_bg": _hex_with_alpha(accent, 0.12),
        },
        "period": period_block,
        "is_session_report": is_session,
        "trainee": {
            "display_name": athlete["display_name"],
            "joined_at_label": athlete["joined_at"].strftime("%B %Y"),
            "total_sessions": total_sessions,
            "total_sessions_label": total_sessions_label,
        },
        "coach": coach,
        "coach_note": coach_note,
        "tier_progress": tier,
        "stats": stats,
        "category_averages": category_averages,
        "recent_gains": gains,
        "sessions": sessions,
        "skill_detail": skill_detail,
        "rated_groups": rated_groups,
        "pending_categories": pending_categories,
        "levels_heading": levels_heading,
        "generated_at": datetime.utcnow().strftime("%-d %B %Y"),
    }


def render_report_pdf(context: dict[str, Any]) -> bytes:
    """Jinja2 → WeasyPrint."""
    html = _env.get_template("report.html").render(**context)
    css_path = _TEMPLATE_DIR / "report.css"
    return HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf(
        stylesheets=[CSS(filename=str(css_path))]
    )


# ── Helpers (data) ───────────────────────────────────────────────


async def _fetch_workspace(conn: asyncpg.Connection, workspace_id: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT w.name AS workspace_name, w.brand_color, w.logo_url, w.city,
               s.name_en AS sport_name
        FROM workspaces w
        LEFT JOIN sports s ON s.id = w.sport_id
        WHERE w.id = $1
        """,
        workspace_id,
    )
    if row is None:
        raise ValueError(f"workspace {workspace_id} not found")
    return dict(row)


async def _fetch_athlete(conn: asyncpg.Connection, athlete_id: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
            a.display_name,
            a.joined_at,
            (SELECT COUNT(*) FROM sessions WHERE athlete_id = a.id) AS total_sessions
        FROM athletes a WHERE a.id = $1
        """,
        athlete_id,
    )
    if row is None:
        raise ValueError(f"athlete {athlete_id} not found")
    return dict(row)


async def _fetch_lead_coach(
    conn: asyncpg.Connection, athlete_id: str, workspace_id: str
) -> dict[str, Any]:
    """Most recent session's coach for this athlete.  Falls back to the
    workspace owner so the byline always renders."""
    row = await conn.fetchrow(
        """
        SELECT u.display_name, u.email
        FROM sessions s JOIN users u ON u.id = s.coach_id
        WHERE s.athlete_id = $1
        ORDER BY s.scheduled_at DESC NULLS LAST LIMIT 1
        """,
        athlete_id,
    )
    if row is None:
        row = await conn.fetchrow(
            """
            SELECT u.display_name, u.email
            FROM workspaces w JOIN users u ON u.id = w.owner_user_id
            WHERE w.id = $1
            """,
            workspace_id,
        )
    return {
        "display_name": row["display_name"] if row else "Coach",
        "byline": "",
    }


async def _fetch_period_stats(
    conn: asyncpg.Connection, athlete_id: str, period_start: date, period_end: date
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM sessions
              WHERE athlete_id = $1
                AND scheduled_at::date BETWEEN $2 AND $3) AS sessions_count,
            (SELECT COALESCE(SUM(duration_min),0) FROM sessions
              WHERE athlete_id = $1
                AND scheduled_at::date BETWEEN $2 AND $3) AS minutes_total,
            (SELECT COUNT(DISTINCT sc.skill_id)
               FROM assessment_scores sc
               JOIN assessments a ON a.id = sc.assessment_id
              WHERE a.athlete_id = $1
                AND a.status IN ('published','edited')
                AND COALESCE(a.edited_at, a.published_at)::date BETWEEN $2 AND $3
            ) AS skills_assessed
        """,
        athlete_id,
        period_start,
        period_end,
    )
    sessions_count = int(row["sessions_count"]) if row else 0
    minutes_total = int(row["minutes_total"]) if row else 0
    return {
        "sessions": sessions_count,
        "hours_coached": round(minutes_total / 60, 1),
        "skills_assessed": int(row["skills_assessed"]) if row else 0,
        "attendance_pct": 100 if sessions_count > 0 else 0,
    }


async def _fetch_tier_progress(
    conn: asyncpg.Connection, athlete_id: str, workspace_id: str
) -> dict[str, Any]:
    """Walk tiers in display_order ascending; current tier = highest where
    all reqs met.  Mirrors src/assessments/service.recompute_tier but reads
    everything in one connection."""
    latest = await conn.fetch(
        """
        SELECT DISTINCT ON (sc.skill_id) sc.skill_id::text, sc.level
        FROM assessment_scores sc
        JOIN assessments a ON a.id = sc.assessment_id
        WHERE a.athlete_id = $1
          AND a.status IN ('published','edited')
        ORDER BY sc.skill_id,
                 COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                 sc.updated_at DESC
        """,
        athlete_id,
    )
    levels: dict[str, int] = {r["skill_id"]: int(r["level"]) for r in latest}

    rows = await conn.fetch(
        """
        SELECT t.id::text AS tier_id, t.code, t.display_order, t.name_game_en,
               tr.skill_id::text AS skill_id, tr.min_level
        FROM tiers t
        JOIN tier_requirements tr ON tr.tier_id = t.id
        WHERE t.sport_id = (SELECT sport_id FROM workspaces WHERE id = $1)
          AND (t.workspace_id = $1 OR t.workspace_id IS NULL)
        ORDER BY t.display_order ASC
        """,
        workspace_id,
    )
    by_tier: dict[str, dict[str, Any]] = {}
    for r in rows:
        b = by_tier.setdefault(
            r["tier_id"],
            {
                "code": r["code"],
                "name": r["name_game_en"],
                "display_order": r["display_order"],
                "reqs": [],
            },
        )
        b["reqs"].append((r["skill_id"], int(r["min_level"])))

    tiers = sorted(by_tier.values(), key=lambda t: t["display_order"])
    current = None
    next_tier = None
    met_count = 0
    total = 0
    for tier in tiers:
        m = sum(1 for sid, mn in tier["reqs"] if levels.get(sid, 0) >= mn)
        if m == len(tier["reqs"]) and tier["reqs"]:
            current = tier
        else:
            next_tier = tier
            met_count = m
            total = len(tier["reqs"])
            break

    pct = round((met_count / total) * 100) if total else 100
    return {
        "current_name": current["name"] if current else "Beginner",
        "next_name": next_tier["name"] if next_tier else None,
        "met_count": met_count,
        "total": total,
        "pct": pct,
        "is_top_tier": next_tier is None,
    }


async def _fetch_category_averages(
    conn: asyncpg.Connection, athlete_id: str, workspace_id: str
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        WITH latest AS (
            SELECT DISTINCT ON (sc.skill_id) sc.skill_id, sc.level
            FROM assessment_scores sc
            JOIN assessments a ON a.id = sc.assessment_id
            WHERE a.athlete_id = $1
              AND a.status IN ('published','edited')
            ORDER BY sc.skill_id,
                     COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                     sc.updated_at DESC
        )
        SELECT s.category::text AS category,
               COALESCE(AVG(l.level)::numeric(4,1), 0) AS avg,
               COUNT(l.skill_id) AS skills_rated
        FROM skills s
        LEFT JOIN latest l ON l.skill_id = s.id
        WHERE (s.workspace_id = $2 OR s.workspace_id IS NULL)
        GROUP BY s.category
        ORDER BY s.category
        """,
        athlete_id,
        workspace_id,
    )
    return [
        {
            "category": r["category"],
            "average": float(r["avg"]) if r["avg"] is not None else 0.0,
            "skills_rated": int(r["skills_rated"]),
        }
        for r in rows
    ]


async def _fetch_recent_gains(
    conn: asyncpg.Connection, athlete_id: str, period_start: date, period_end: date
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        WITH ranked AS (
            SELECT sc.skill_id, sc.level,
                   COALESCE(a.edited_at, a.published_at) AS recorded_at,
                   s.name_en,
                   ROW_NUMBER() OVER (
                     PARTITION BY sc.skill_id
                     ORDER BY COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                              sc.updated_at DESC
                   ) AS rn
            FROM assessment_scores sc
            JOIN assessments a ON a.id = sc.assessment_id
            JOIN skills s      ON s.id = sc.skill_id
            WHERE a.athlete_id = $1
              AND a.status IN ('published','edited')
              AND COALESCE(a.edited_at, a.published_at)::date BETWEEN $2 AND $3
        )
        SELECT r.skill_id, r.name_en,
               r.level AS to_level, r.recorded_at,
               p.level AS from_level
        FROM ranked r
        LEFT JOIN ranked p ON p.skill_id = r.skill_id AND p.rn = r.rn + 1
        WHERE r.rn = 1
          AND (p.level IS NULL OR r.level > p.level)
        ORDER BY r.recorded_at DESC LIMIT 5
        """,
        athlete_id,
        period_start,
        period_end,
    )
    return [
        {
            "skill_name": r["name_en"],
            "from_level": int(r["from_level"]) if r["from_level"] is not None else None,
            "to_level": int(r["to_level"]),
            "date_label": r["recorded_at"].strftime("%-d %b"),
        }
        for r in rows
    ]


async def _fetch_sessions(
    conn: asyncpg.Connection, athlete_id: str, period_start: date, period_end: date
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT scheduled_at, duration_min, focus::text AS focus, summary
        FROM sessions
        WHERE athlete_id = $1 AND scheduled_at::date BETWEEN $2 AND $3
        ORDER BY scheduled_at DESC LIMIT 8
        """,
        athlete_id,
        period_start,
        period_end,
    )
    return [
        {
            "raw_date": r["scheduled_at"].date(),
            "date_label": r["scheduled_at"].strftime("%-d %b · %H:%M"),
            "duration_min": int(r["duration_min"]) if r["duration_min"] else 60,
            "focus": (r["focus"] or "general").replace("_", " ").title(),
            "summary": r["summary"] or "",
        }
        for r in rows
    ]


async def _fetch_one_session(
    conn: asyncpg.Connection, athlete_id: str, session_id: str
) -> list[dict[str, Any]]:
    row = await conn.fetchrow(
        """
        SELECT scheduled_at, duration_min, focus::text AS focus, summary
        FROM sessions WHERE id = $1 AND athlete_id = $2
        """,
        session_id,
        athlete_id,
    )
    if row is None:
        return []
    return [
        {
            "raw_date": row["scheduled_at"].date(),
            "date_label": row["scheduled_at"].strftime("%-d %b · %H:%M"),
            "duration_min": int(row["duration_min"]) if row["duration_min"] else 60,
            "focus": (row["focus"] or "general").replace("_", " ").title(),
            "summary": row["summary"] or "",
        }
    ]


async def _fetch_single_session_stats(
    conn: asyncpg.Connection, athlete_id: str, session_id: str
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT duration_min,
               (SELECT COUNT(DISTINCT sc.skill_id)
                  FROM assessment_scores sc
                  JOIN assessments a ON a.id = sc.assessment_id
                 WHERE a.session_id = $1
                   AND a.status IN ('published','edited')
               ) AS skills_assessed
        FROM sessions WHERE id = $1 AND athlete_id = $2
        """,
        session_id,
        athlete_id,
    )
    minutes = int(row["duration_min"]) if row and row["duration_min"] else 0
    return {
        "sessions": 1,
        "hours_coached": round(minutes / 60, 1),
        "skills_assessed": int(row["skills_assessed"]) if row else 0,
        "attendance_pct": 100,
    }


async def _fetch_session_gains(
    conn: asyncpg.Connection, athlete_id: str, session_id: str
) -> list[dict[str, Any]]:
    """Gains *recorded in this session* — compares each assessment to the
    immediately-prior assessment of the same skill."""
    rows = await conn.fetch(
        """
        WITH this_session AS (
            SELECT sc.skill_id, sc.level,
                   COALESCE(a.edited_at, a.published_at) AS recorded_at,
                   s.name_en
            FROM assessment_scores sc
            JOIN assessments a ON a.id = sc.assessment_id
            JOIN skills s      ON s.id = sc.skill_id
            WHERE a.session_id = $1
              AND a.athlete_id = $2
              AND a.status IN ('published','edited')
        )
        SELECT ts.skill_id, ts.name_en, ts.level AS to_level, ts.recorded_at,
               (SELECT sc.level
                  FROM assessment_scores sc
                  JOIN assessments a ON a.id = sc.assessment_id
                 WHERE a.athlete_id = $2
                   AND sc.skill_id = ts.skill_id
                   AND a.status IN ('published','edited')
                   AND COALESCE(a.edited_at, a.published_at) < ts.recorded_at
                 ORDER BY COALESCE(a.edited_at, a.published_at) DESC LIMIT 1
               ) AS from_level
        FROM this_session ts
        ORDER BY ts.recorded_at DESC
        """,
        session_id,
        athlete_id,
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        from_lv = int(r["from_level"]) if r["from_level"] is not None else None
        to_lv = int(r["to_level"])
        if from_lv is not None and to_lv <= from_lv:
            continue  # not a gain
        out.append(
            {
                "skill_name": r["name_en"],
                "from_level": from_lv,
                "to_level": to_lv,
                "date_label": r["recorded_at"].strftime("%-d %b"),
            }
        )
    return out


async def _fetch_skill_detail(
    conn: asyncpg.Connection, athlete_id: str, workspace_id: str
) -> list[dict[str, Any]]:
    """Every platform skill grouped by category with the trainee's current
    level + when it was last rated.  Drives the new full skill-detail
    section of the PDF."""
    rows = await conn.fetch(
        """
        WITH latest AS (
            SELECT DISTINCT ON (sc.skill_id) sc.skill_id, sc.level,
                   COALESCE(a.edited_at, a.published_at) AS recorded_at
            FROM assessment_scores sc
            JOIN assessments a ON a.id = sc.assessment_id
            WHERE a.athlete_id = $1
              AND a.status IN ('published','edited')
            ORDER BY sc.skill_id,
                     COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                     sc.updated_at DESC
        )
        SELECT s.id::text AS id, s.code, s.name_en, s.category::text AS category,
               s.display_order, l.level, l.recorded_at
        FROM skills s
        LEFT JOIN latest l ON l.skill_id = s.id
        WHERE (s.workspace_id = $2 OR s.workspace_id IS NULL)
          AND s.is_enabled = TRUE
          AND s.sport_id = (SELECT sport_id FROM workspaces WHERE id = $2)
        ORDER BY s.category, s.display_order
        """,
        athlete_id,
        workspace_id,
    )

    # Group → list of {category, skills: [...]}.  Cardinal order matches the
    # radar so the layouts line up.
    order = ["technical", "tactical", "physical", "mental"]
    by_cat: dict[str, list[dict[str, Any]]] = {c: [] for c in order}
    for r in rows:
        level = int(r["level"]) if r["level"] is not None else None
        by_cat.setdefault(r["category"], []).append(
            {
                "name": r["name_en"],
                "level": level,
                "level_label": _LEVEL_LABELS[level] if level else None,
                "last_rated_label": (
                    r["recorded_at"].strftime("%-d %b") if r["recorded_at"] else None
                ),
            }
        )
    return [{"category": cat, "skills": by_cat[cat]} for cat in order if by_cat.get(cat)]


_LEVEL_LABELS = {
    1: "Learning",
    2: "Developing",
    3: "Functional",
    4: "Capable",
    5: "Proficient",
}


# ── Radar SVG ────────────────────────────────────────────────────


def _build_radar_svg(
    category_averages: list[dict[str, Any]], *, accent: str
) -> str:
    """Compact 140×140 four-axis radar.  Matches the in-app SkillRadar visual
    language so the PDF feels like an extension of the app."""
    size = _RADAR_SIZE + _RADAR_PAD * 2
    cx = cy = size / 2
    r_max = _RADAR_SIZE / 2 - 8
    # Cardinal order: Technical ↑, Tactical →, Physical ↓, Mental ←
    angles = [(-90, "technical"), (0, "tactical"), (90, "physical"), (180, "mental")]
    by_cat = {c["category"]: c["average"] for c in category_averages}

    import math

    def point(angle_deg: float, fraction: float) -> tuple[float, float]:
        rad = math.radians(angle_deg)
        r = fraction * r_max
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    # Concentric rings
    rings = []
    for level in (1, 2, 3, 4, 5):
        pts = [point(a, level / 5) for a, _ in angles]
        rings.append(" ".join(f"{x:.1f},{y:.1f}" for x, y in pts))

    # Axis lines + labels
    axis_lines = []
    labels = []
    for angle, cat in angles:
        ex, ey = point(angle, 1.0)
        axis_lines.append((cx, cy, ex, ey))
        lx, ly = point(angle, 1.18)
        anchor = "middle"
        if angle == 0:
            anchor = "start"
        elif angle == 180:
            anchor = "end"
        labels.append((lx, ly, anchor, cat.upper()))

    # Data polygon
    poly_pts = [
        point(a, max(by_cat.get(cat, 0.0), 0.05) / 5) for a, cat in angles
    ]
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in poly_pts)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
    ]
    for ring in rings:
        parts.append(
            f'<polygon points="{ring}" fill="none" stroke="rgba(0,0,0,0.08)" stroke-width="0.5"/>'
        )
    for x1, y1, x2, y2 in axis_lines:
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="rgba(0,0,0,0.08)" stroke-width="0.5"/>'
        )
    parts.append(
        f'<polygon points="{data_pts}" fill="{accent}" fill-opacity="0.18" '
        f'stroke="{accent}" stroke-width="1.2"/>'
    )
    for x, y in poly_pts:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{accent}"/>')
    for x, y, anchor, text in labels:
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-size="8" '
            f'font-family="DejaVu Sans, Liberation Sans, sans-serif" '
            f'fill="#666" letter-spacing="0.6">{text}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _hex_with_alpha(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(55,138,221,{alpha})"
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
    except ValueError:
        return f"rgba(55,138,221,{alpha})"
    return f"rgba({r},{g},{b},{alpha})"


# ``defaultdict`` is unused at runtime but referenced in earlier drafts;
# keep available for downstream callers who want to extend the context.
_ = defaultdict
