# PadelCoach — Default Skill Framework (v0)

A foundational framework for skill assessment, progression tracking, and curriculum structure. This is the **platform default** that every workspace (club or solo coach) inherits on signup. Clubs can override tier names, thresholds, and descriptors later — but the skill ontology and 1–5 scale stay locked across the platform.

> **Status:** v0 draft, built from public coaching knowledge. Refine with a certified APPA L1 or PadelMBA coach advisor before locking into production. Budget ~1–2 weeks of advisor time to validate descriptors and tier thresholds.

---

## How to use this document

1. **Database schema** — skill codes (e.g. `TECH_BANDEJA`) are stable IDs. Wire them into your DB.
2. **UI/UX design** — paste sections into your Claude Project when designing assessment screens, progress dashboards, tier badges.
3. **Coach advisor** — share with them, ask them to (a) refine each descriptor, (b) validate tier thresholds, (c) flag missing skills, (d) propose drills per skill.
4. **Pilot clubs** — show them only the user-facing labels (Indonesian + English). Hide the codes.

---

## 1. Categories

| Code | English | Indonesian |
|------|---------|------------|
| TECH | Technical | Teknik |
| TACT | Tactical | Taktik |
| PHYS | Physical | Fisik |
| MENT | Mental | Mental |

---

## 2. Skill List (27 skills total)

### A. Technical — 13 skills

| Code | Skill | Indonesian Label | Notes |
|------|-------|------------------|-------|
| TECH_FH | Forehand Drive | Forehand | Groundstroke from baseline |
| TECH_BH | Backhand Drive | Backhand | Groundstroke from baseline |
| TECH_FH_VOLLEY | Forehand Volley | Voli Forehand | At net, no bounce |
| TECH_BH_VOLLEY | Backhand Volley | Voli Backhand | At net, no bounce |
| TECH_SERVE | Serve | Servis | Underarm into service box |
| TECH_RETURN | Return of Serve | Pengembalian Servis | First contact after opponent's serve |
| TECH_LOB | Defensive Lob (Globo) | Lob Bertahan | High ball over volleyer |
| TECH_BANDEJA | Bandeja | Bandeja | Defensive overhead, holds net |
| TECH_VIBORA | Víbora | Víbora | Aggressive overhead with side spin |
| TECH_SMASH | Smash (Remate) | Smash | Finishing overhead |
| TECH_WALL_BACK | Back Wall Exit | Pukulan dari Dinding Belakang | Playing ball off back glass |
| TECH_WALL_SIDE | Side Wall Play | Pukulan dari Dinding Samping | Playing ball off side glass |
| TECH_DROP | Chiquita / Drop Shot | Chiquita / Bola Pendek | Low short ball to opponent's feet |

### B. Tactical — 6 skills

| Code | Skill | Indonesian Label | Notes |
|------|-------|------------------|-------|
| TACT_NET_POS | Net Positioning (Offensive) | Posisi Menyerang di Net | Holding & dominating the net |
| TACT_DEF_POS | Defensive Positioning | Posisi Bertahan | Court coverage when behind |
| TACT_SHOT_SEL | Shot Selection | Pemilihan Pukulan | Choosing right shot for situation |
| TACT_PARTNER | Partner Coordination | Kerjasama Pasangan | Communication, switching, covering |
| TACT_TRANSITION | Transition Play | Transisi Bertahan ke Menyerang | Moving from defense to offense |
| TACT_READING | Reading the Game | Membaca Permainan | Anticipating opponent's intent |

### C. Physical — 4 skills

| Code | Skill | Indonesian Label | Notes |
|------|-------|------------------|-------|
| PHYS_FOOTWORK | Footwork & Court Coverage | Footwork & Cakupan Lapangan | Movement quality & efficiency |
| PHYS_SPLIT | Split Step & Reaction | Split Step & Reaksi | Timing of ready position |
| PHYS_ENDURANCE | Endurance | Stamina | Sustaining quality over long matches |
| PHYS_POWER | Power & Explosiveness | Power & Eksplosivitas | Generating speed on shots & sprints |

### D. Mental — 4 skills

| Code | Skill | Indonesian Label | Notes |
|------|-------|------------------|-------|
| MENT_FOCUS | Focus & Concentration | Fokus & Konsentrasi | Staying present point-by-point |
| MENT_COMPOSURE | Composure Under Pressure | Ketenangan di Bawah Tekanan | Big points, behind in score |
| MENT_DECISION | Decision-Making Speed | Kecepatan Keputusan | Fast choices under pressure |
| MENT_RESILIENCE | Resilience After Errors | Bangkit dari Kesalahan | Bouncing back from mistakes |

---

## 3. Universal Level Scale (1–5)

Every skill uses the same 1–5 scale. Locked across the platform — clubs can rewrite descriptors but cannot change the scale.

| Level | Label (EN) | Label (ID) | General meaning |
|-------|-----------|-----------|-----------------|
| 1 | Learning | Belajar | Just being introduced. Inconsistent, breaks down under pressure. |
| 2 | Developing | Berkembang | Some success in slow drills. Falls apart in match play. |
| 3 | Functional | Fungsional | Reliable in controlled situations. Works in friendly matches. |
| 4 | Proficient | Mampu | Consistent in match play. Effective vs equal-level opponents. |
| 5 | Mastery | Mahir | Elite execution. Tournament-ready. Reliable under pressure. |

---

## 4. Skill-Specific Level Descriptors

Concrete behavioral descriptors per skill. These are what the coach reads during assessment to score 1–5. Refine wording with advisor; structure stays.

### TECH_FH — Forehand Drive
1. Inconsistent contact, ball flies erratically, no swing structure
2. Makes contact ~6/10 in cooperative rally, no direction control, often into net
3. Consistent crosscourt rally at moderate pace, basic depth control
4. Controls direction & depth in match play, attacks short balls aggressively
5. Weapon shot — varies pace, spin, depth, direction at will under pressure

### TECH_BH — Backhand Drive
1. Uses forehand grip, weak block contact, can't drive
2. Switches grip but inconsistent contact, often hits with frame
3. Consistent block backhand crosscourt, limited topspin
4. Reliable in match play, drives backhand with depth, basic topspin
5. Aggressive backhand with topspin, attacks down the line under pressure

### TECH_FH_VOLLEY — Forehand Volley
1. Swings at the ball, frame contacts common, often pops up
2. Makes contact but no placement, short of net or floats
3. Consistent block volley, keeps ball low, basic placement
4. Controls direction with cut, can attack or defend based on situation
5. Penetrating volley with cut & placement, dictates points from net

### TECH_BH_VOLLEY — Backhand Volley
1. Misses contact frequently, no grip change
2. Block contact but ball lacks pace, pops up
3. Consistent block backhand volley, keeps ball low
4. Controls direction, absorbs pace and redirects
5. Aggressive backhand volley with cut, attacks confidently

### TECH_SERVE — Serve
1. Inconsistent toss, double faults common, no direction control
2. Gets serve in ~6/10, no placement, slow pace
3. Consistent serve in service box, can target T or wide occasionally
4. Reliable placement, varies pace, uses slice
5. Strategic serve — varies placement, pace, spin to set up next shot

### TECH_RETURN — Return of Serve
1. Often misses, gets aced or returns short to opponent's volley
2. Returns over net but no placement, often goes to opponent's volley
3. Consistent return cross-court, keeps ball low, neutralizes serve
4. Returns with intent — can lob, chip, or drive based on serve quality
5. Uses return as offensive weapon, attacks weak serves consistently

### TECH_LOB — Defensive Lob (Globo)
1. Lobs too short or too long, often gets smashed
2. Inconsistent height & depth, gets smashed or hits out
3. Consistent depth & height, neutralizes opponent's net pressure
4. Tactical lobs — varies depth & spin, sets up own counter-attack
5. Lob is a weapon — perfect height & depth, mixes in offensive lobs

### TECH_BANDEJA — Bandeja
1. Doesn't recognize when to use it; uses smash or lets ball drop
2. Recognizes opportunity but inconsistent contact, often into net
3. Consistent contact with control, keeps ball deep, but loses net position often
4. Controls direction & depth, maintains net position, slows opponents down
5. Tactical bandeja — varies pace, spin, direction; offensive when needed

### TECH_VIBORA — Víbora
1. Confuses with bandeja, inconsistent contact, often goes long
2. Recognizes when to use but contact inconsistent
3. Consistent contact with side spin, keeps ball in
4. Controls direction & spin, ball jumps out of court (good víbora)
5. Devastating víbora — angles, spin, pace; finishes points consistently

### TECH_SMASH — Smash (Remate)
1. Times poorly, often misses, hits net or out
2. Inconsistent timing, lacks power, opponent defends easily
3. Consistent smash on easy balls, basic power & direction
4. Powerful smash with placement, attacks defensive lobs effectively
5. Devastating smash — uses kick, flat, angles; finishes points off any lob

### TECH_WALL_BACK — Back Wall Exit
1. Doesn't read ball off back wall, late or rushed
2. Reads ball but contact inconsistent, often hits weak return
3. Reads back wall well, returns ball to neutral position
4. Uses back wall to attack — sets up offensive shots from defense
5. Master of back wall — can chiquita, lob, or drive based on opportunity

### TECH_WALL_SIDE — Side Wall Play
1. Confused by side wall, often misses ball or contacts late
2. Reads side wall but rushed, returns weakly
3. Reads side wall consistently, returns ball to neutral
4. Uses side wall to attack — sets up counter from corner shots
5. Comfortable with all wall combinations (back + side), creates winners

### TECH_DROP — Chiquita / Drop Shot
1. Drops too high or no spin, easy attack for opponent
2. Inconsistent drop — sometimes too short, often too high
3. Consistent low drop, opponent has to move forward to retrieve
4. Tactical use — recognizes good moments, varies placement
5. Drop is a weapon — surprises opponents, sets up traps

### TACT_NET_POS — Net Positioning (Offensive)
1. Stands behind service line, gets lobbed easily, no awareness
2. Stays at net but loses position after first volley, doesn't recover
3. Holds net in steady rallies, loses position under sustained pressure
4. Maintains aggressive net position, recovers after bandeja, partners coordinate
5. Dominates net consistently, dictates points, perfect positioning vs all opponents

### TACT_DEF_POS — Defensive Positioning
1. Stays at baseline reactively, no court coverage awareness
2. Knows to retreat when lobbed but slow recovery, gaps with partner
3. Defends consistently, covers most of court with partner
4. Active defense — sets up counter-attack, communicates with partner
5. Defensive maestro — turns defense to offense reliably, never out of position

### TACT_SHOT_SEL — Shot Selection
1. Hits whatever shot first comes to mind, often wrong choice
2. Recognizes "easy" shots but unsure on tough decisions
3. Reasonable shot choices in routine situations
4. Smart shot selection — chooses based on opponent position, score, momentum
5. Strategic mastermind — every shot has purpose, sets up patterns 2–3 shots ahead

### TACT_PARTNER — Partner Coordination
1. No communication, plays as if alone on court
2. Basic communication ("mine!", "out!") but no strategic talk
3. Communicates routinely, switches when needed
4. Coordinates strategy, plans points together, supports partner emotionally
5. Synchronized play — telepathic positioning, consistent partnership

### TACT_TRANSITION — Transition Play
1. Stays at baseline even when chance to attack, or rushes net poorly
2. Recognizes when to come up but timing poor, gets caught in transition
3. Comes to net at appropriate times, basic transition execution
4. Smooth transition — uses bandeja/lob to set up net, recovers if pushed back
5. Master of transition — flips defense to offense seamlessly, controls tempo

### TACT_READING — Reading the Game
1. Reactive only, doesn't anticipate opponent's shots
2. Reads obvious patterns but slow to adapt
3. Anticipates routine situations, makes decent guesses
4. Reads opponent well, anticipates shots based on position & body language
5. Elite anticipation — reads serve placement, set-ups, knows next shot before opponent hits

### PHYS_FOOTWORK — Footwork & Court Coverage
1. Slow, flat-footed, often arrives too late or off-balance
2. Improving movement but inefficient, takes wrong steps
3. Consistent split step & basic court coverage, occasional inefficiency
4. Efficient movement, cross-step & shuffle, balanced contact
5. Elite footwork — anticipates, recovers fast, always in balance

### PHYS_SPLIT — Split Step & Reaction
1. No split step, flat-footed, late reactions
2. Inconsistent split step, sometimes too early or late
3. Consistent split step on opponent's contact, decent reactions
4. Reliable split + first-step explosiveness in match play
5. Elite reactions — perfect timing, explosive first step, dominates short balls

### PHYS_ENDURANCE — Endurance
1. Tired after 30 minutes, can't sustain quality in long rallies
2. Lasts a set but quality drops in second set
3. Plays 2 full sets at same level, tires in third
4. Sustains quality across 3 sets, occasional fatigue late
5. Tournament-ready endurance, maintains intensity in long matches & multi-day events

### PHYS_POWER — Power & Explosiveness
1. Lacks pace on shots, slow movement
2. Decent power on easy balls, breaks down under pressure
3. Solid power on groundstrokes, average on overheads
4. Powerful shots & explosive movement, can finish points
5. Elite power — generates pace from any position, dominates physically

### MENT_FOCUS — Focus & Concentration
1. Loses focus quickly, distracted easily, mistakes after errors
2. Focused in spurts but drops off when behind or tired
3. Maintains focus in routine matches, struggles in long sessions
4. Stays focused in close matches, recovers quickly after distractions
5. Laser focus — present every point, locked in for entire match

### MENT_COMPOSURE — Composure Under Pressure
1. Visibly affected by errors, body language drops, plays worse when behind
2. Recovers slowly after mistakes, plays safer when behind
3. Maintains form in routine pressure, struggles in tight scores
4. Performs well in close sets, makes smart choices at 5–5
5. Thrives in pressure — raises level when match is on the line

### MENT_DECISION — Decision-Making Speed
1. Slow decisions, hesitates, often hits wrong shot
2. Improving but still slow on tough decisions
3. Reasonable decisions in routine situations
4. Quick & accurate decisions in match play, rarely wrong shot
5. Lightning decisions — pattern recognition, intuitive shot selection

### MENT_RESILIENCE — Resilience After Errors
1. Errors compound — one mistake leads to several more
2. Slow to recover from errors, lingering frustration
3. Recovers within 1–2 points after mistakes
4. Bounces back immediately, uses errors as feedback
5. Unshakeable — plays better after adversity, mental warrior

---

## 5. Curriculum Tiers (7 progression levels)

Game-style metal tiers — easy to communicate, motivating, recognizable across cultures. **Tier is auto-calculated** from a player's skill scores (not assigned manually by coach).

| # | Tier (EN) | Tier (ID) | Player Profile | Typical sessions to reach |
|---|-----------|-----------|----------------|---------------------------|
| 1 | Beginner | Pemula | Just started, learning rules & contact | 0 (entry point) |
| 2 | Lower Bronze | Perunggu Muda | Can rally, knows scoring | 6–12 |
| 3 | Bronze | Perunggu | Plays casual matches, all shots functional | 25–40 |
| 4 | Silver | Perak | Competent club player | 50–80 |
| 5 | Gold | Emas | Strong club player, tactical understanding | 100–150 |
| 6 | Platinum | Platinum | Tournament-level player | 200+ |
| 7 | Diamond | Berlian | Elite, near-pro competition | 400+ |

> Session counts are rough — tier is determined by skill thresholds, not time invested.

---

## 6. Tier Graduation Thresholds

To graduate to a tier, **all** the listed skills must meet the minimum level. If any skill is below threshold, player stays at previous tier with that skill flagged as "blocking progression."

### Beginner → Lower Bronze
| Skill | Min Level |
|-------|-----------|
| TECH_FH | 2 |
| TECH_BH | 2 |
| TECH_SERVE | 1 |
| TECH_RETURN | 1 |
| Plus: knows scoring & basic rules (rule check, not skill score) |

### Lower Bronze → Bronze
| Skill | Min Level |
|-------|-----------|
| TECH_FH | 3 |
| TECH_BH | 3 |
| TECH_SERVE | 2 |
| TECH_RETURN | 2 |
| TECH_FH_VOLLEY | 2 |
| TECH_BH_VOLLEY | 2 |
| TECH_LOB | 2 |
| TECH_SMASH | 2 |
| TECH_WALL_BACK | 1 |
| TACT_NET_POS | 2 |
| TACT_DEF_POS | 2 |
| PHYS_FOOTWORK | 2 |

### Bronze → Silver
| Skill | Min Level |
|-------|-----------|
| TECH_FH | 3 |
| TECH_BH | 3 |
| TECH_SERVE | 3 |
| TECH_RETURN | 3 |
| TECH_FH_VOLLEY | 3 |
| TECH_BH_VOLLEY | 3 |
| TECH_LOB | 3 |
| TECH_SMASH | 3 |
| TECH_BANDEJA | 2 |
| TECH_WALL_BACK | 3 |
| TECH_WALL_SIDE | 2 |
| TACT_NET_POS | 3 |
| TACT_DEF_POS | 3 |
| TACT_SHOT_SEL | 2 |
| TACT_PARTNER | 3 |
| PHYS_FOOTWORK | 3 |
| PHYS_SPLIT | 2 |
| MENT_FOCUS | 3 |

### Silver → Gold
| Skill | Min Level |
|-------|-----------|
| TECH_FH | 4 |
| TECH_BH | 4 |
| TECH_SERVE | 4 |
| TECH_RETURN | 4 |
| TECH_FH_VOLLEY | 4 |
| TECH_BH_VOLLEY | 4 |
| TECH_LOB | 4 |
| TECH_SMASH | 4 |
| TECH_BANDEJA | 4 |
| TECH_VIBORA | 3 |
| TECH_DROP | 3 |
| TECH_WALL_BACK | 4 |
| TECH_WALL_SIDE | 3 |
| TACT_NET_POS | 4 |
| TACT_DEF_POS | 4 |
| TACT_SHOT_SEL | 3 |
| TACT_PARTNER | 4 |
| TACT_TRANSITION | 3 |
| TACT_READING | 3 |
| PHYS_FOOTWORK | 4 |
| PHYS_SPLIT | 3 |
| PHYS_ENDURANCE | 3 |
| PHYS_POWER | 3 |
| MENT_FOCUS | 3 |
| MENT_COMPOSURE | 3 |
| MENT_DECISION | 3 |
| MENT_RESILIENCE | 3 |

### Gold → Platinum
| Skill | Min Level |
|-------|-----------|
| All technical skills | 4 |
| TECH_VIBORA | 4 |
| At least one of (TECH_BANDEJA, TECH_VIBORA, TECH_SMASH) | 5 (signature shot) |
| All tactical skills | 4 |
| All physical skills | 4 |
| All mental skills | 4 |

### Platinum → Diamond
| Skill | Min Level |
|-------|-----------|
| All technical skills | 5 (most), 4 minimum |
| At least 5 skills total | 5 (mastery breadth) |
| All tactical skills | 5 |
| All physical skills | 4 |
| All mental skills | 4 |
| Tournament participation | Yes (competition record check) |

---

## 7. Tier Focus Areas (curriculum content per tier)

What the coach prioritizes at each tier — to keep training relevant and not overwhelming.

| Tier transition | Focus on | Leave out for now |
|-----------------|----------|-------------------|
| Beginner → Lower Bronze | Contact consistency, rules, basic FH/BH, intro serve | Bandeja, víbora, advanced wall play, tactics |
| Lower Bronze → Bronze | All groundstrokes, intro volleys, intro lob/smash, basic positioning | Víbora, complex tactics, sidewall combinations |
| Bronze → Silver | Bandeja introduction, wall play, basic tactical patterns, partner coordination | Víbora mastery, advanced reading, signature shots |
| Silver → Gold | Bandeja mastery, víbora intro, drop shot, tactical decision-making, mental skills | Specialized power shots, elite reading |
| Gold → Platinum | Signature shot development, advanced tactics, match management, mental game | — (everything tracked now) |
| Platinum → Diamond | Refinement of all skills, match-specific prep, weakness elimination, competition prep | — |

---

## 8. Skill Introduction Matrix

Quick reference — at which tier each skill is **first taught** (level 1+) and when it's expected to be **mastered** (level 4–5).

| Skill | Introduced at | Expected proficient at |
|-------|---------------|------------------------|
| TECH_FH | Beginner | Silver |
| TECH_BH | Beginner | Silver |
| TECH_SERVE | Beginner | Silver |
| TECH_RETURN | Beginner | Silver |
| TECH_FH_VOLLEY | Lower Bronze | Silver |
| TECH_BH_VOLLEY | Lower Bronze | Silver |
| TECH_LOB | Lower Bronze | Silver |
| TECH_SMASH | Lower Bronze | Silver |
| TECH_WALL_BACK | Bronze | Gold |
| TECH_WALL_SIDE | Bronze | Gold |
| TECH_BANDEJA | Bronze | Gold |
| TECH_VIBORA | Silver | Platinum |
| TECH_DROP | Silver | Gold |
| TACT_NET_POS | Lower Bronze | Gold |
| TACT_DEF_POS | Lower Bronze | Gold |
| TACT_SHOT_SEL | Bronze | Gold |
| TACT_PARTNER | Bronze | Gold |
| TACT_TRANSITION | Silver | Platinum |
| TACT_READING | Silver | Platinum |
| PHYS_FOOTWORK | Beginner | Gold |
| PHYS_SPLIT | Bronze | Gold |
| PHYS_ENDURANCE | Bronze | Gold |
| PHYS_POWER | Bronze | Gold |
| MENT_FOCUS | Bronze | Gold |
| MENT_COMPOSURE | Silver | Platinum |
| MENT_DECISION | Silver | Platinum |
| MENT_RESILIENCE | Silver | Platinum |

---

## 9. Database Schema Hints

Recommended tables for storing this framework:

```sql
-- Locked at platform level
CREATE TABLE skills (
  id UUID PRIMARY KEY,
  code VARCHAR(50) UNIQUE NOT NULL,        -- e.g. 'TECH_BANDEJA'
  category VARCHAR(10) NOT NULL,           -- 'TECH', 'TACT', 'PHYS', 'MENT'
  name_en VARCHAR(100) NOT NULL,
  name_id VARCHAR(100) NOT NULL,
  display_order INTEGER NOT NULL,
  is_platform_default BOOLEAN DEFAULT TRUE,
  workspace_id UUID NULL                   -- NULL = platform skill, else custom
);

CREATE TABLE skill_level_descriptors (
  id UUID PRIMARY KEY,
  skill_id UUID REFERENCES skills(id),
  workspace_id UUID NULL,                  -- NULL = platform default
  level INTEGER CHECK (level BETWEEN 1 AND 5),
  description_en TEXT NOT NULL,
  description_id TEXT NOT NULL,
  UNIQUE (skill_id, workspace_id, level)
);

CREATE TABLE tiers (
  id UUID PRIMARY KEY,
  workspace_id UUID NULL,                  -- NULL = platform default
  code VARCHAR(20) NOT NULL,               -- 'BRONZE', 'SILVER', etc.
  name_en VARCHAR(50) NOT NULL,
  name_id VARCHAR(50) NOT NULL,
  display_order INTEGER NOT NULL,
  color_hex VARCHAR(7),
  icon_name VARCHAR(50)
);

CREATE TABLE tier_requirements (
  id UUID PRIMARY KEY,
  tier_id UUID REFERENCES tiers(id),
  skill_id UUID REFERENCES skills(id),
  min_level INTEGER CHECK (min_level BETWEEN 1 AND 5),
  UNIQUE (tier_id, skill_id)
);

-- Per-trainee assessment
CREATE TABLE assessments (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL,              -- RLS column
  athlete_id UUID NOT NULL,
  coach_id UUID NOT NULL,
  skill_id UUID NOT NULL,
  level INTEGER CHECK (level BETWEEN 1 AND 5),
  note TEXT,
  session_id UUID NULL,                    -- optional link to session log
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  -- enable RLS on workspace_id
  INDEX (athlete_id, skill_id, recorded_at DESC)
);
```

### Tier calculation pseudocode

```python
def calculate_tier(athlete_id: UUID, workspace_id: UUID) -> Tier:
    latest_scores = get_latest_scores_per_skill(athlete_id)
    tiers = get_tiers(workspace_id, ordered_desc_by_rank=True)
    
    for tier in tiers:  # Diamond down to Beginner
        if meets_all_requirements(latest_scores, tier.requirements):
            return tier
    return BEGINNER

def progress_to_next_tier(athlete_id, workspace_id):
    current = calculate_tier(athlete_id, workspace_id)
    next_tier = get_next_tier(current)
    if not next_tier:
        return {"status": "at max tier"}
    
    requirements = next_tier.requirements
    met = [r for r in requirements if scores[r.skill] >= r.min_level]
    blocking = [r for r in requirements if scores[r.skill] < r.min_level]
    
    return {
        "current_tier": current,
        "next_tier": next_tier,
        "progress_pct": len(met) / len(requirements) * 100,
        "blocking_skills": [
            {
                "skill": r.skill.name_id,
                "current": scores[r.skill],
                "required": r.min_level,
                "gap": r.min_level - scores[r.skill]
            }
            for r in blocking
        ]
    }
```

---

## 10. UI/UX Implications

### Assessment screen
- Group skills by category (Teknik, Taktik, Fisik, Mental) with collapsible sections
- For each skill: show skill name + last score + last assessed date
- Tap skill → bottom sheet with 1–5 buttons + descriptor for each level + optional note
- Default view: only skills assessed in last 30 days expanded; others collapsed
- Quick-action: "Assess only skills worked on today" filter

### Trainee progress dashboard
- **Hero:** current tier badge + progress bar to next tier (e.g. "75% to Silver")
- **Skill radar chart:** average score per category (Teknik 3.4, Taktik 2.8, Fisik 3.1, Mental 2.5)
- **Blocking skills card:** "To reach Silver, focus on: BH Volley (you're at 2, need 3), Bandeja (you're at 1, need 2)"
- **Recent gains card:** "🎉 You leveled up Forehand from 2 to 3 last week!"
- **History chart:** line graph of average score over time

### Coach trainee profile
- Same radar chart as trainee
- Plus: skill grid (all 27 skills with current scores, color-coded by level)
- Tap any skill → assessment history + add new assessment
- Quick stats: hours coached, sessions count, last session date
- Notes feed (chronological coach observations)

### Club admin dashboard
- Trainees by tier (donut chart: 5 Beginner, 12 Lower Bronze, 8 Bronze, 3 Silver, etc.)
- Average tier progression speed (sessions to graduate Bronze: avg 32 in this club)
- Coach activity grid (assessments logged per coach this week)

---

## 11. Localization Map (EN ↔ ID)

For UI translation. Skill technical names (bandeja, víbora, chiquita) **stay in Spanish** — universal padel convention; do NOT translate to Indonesian.

| English | Indonesian |
|---------|-----------|
| Skill Assessment | Penilaian Skill |
| Progress | Progres |
| Level | Level |
| Tier | Tier |
| Beginner | Pemula |
| Lower Bronze | Perunggu Muda |
| Bronze | Perunggu |
| Silver | Perak |
| Gold | Emas |
| Platinum | Platinum |
| Diamond | Berlian |
| Learning | Belajar |
| Developing | Berkembang |
| Functional | Fungsional |
| Proficient | Mampu |
| Mastery | Mahir |
| Forehand | Forehand |
| Backhand | Backhand |
| Volley | Voli |
| Serve | Servis |
| Return | Pengembalian |
| Lob | Lob |
| Smash | Smash |
| Bandeja | Bandeja (no translation) |
| Víbora | Víbora (no translation) |
| Chiquita | Chiquita (no translation) |
| Wall play | Pukulan dari dinding |
| Net positioning | Posisi di net |
| Defensive positioning | Posisi bertahan |
| Shot selection | Pemilihan pukulan |
| Footwork | Footwork (no translation) |
| Endurance | Stamina |
| Power | Power (no translation) |
| Focus | Fokus |
| Composure | Ketenangan |
| Resilience | Ketangguhan mental |
| Coach | Pelatih / Coach |
| Trainee | Murid / Trainee |
| Session | Sesi |
| Assessment | Penilaian |

---

## 12. Validation Checklist Before Production

Before locking this framework into production DB:

- [ ] Hire 1 certified coach advisor (APPA L1 or PadelMBA grad), budget Rp 5–15jt for 2–4 weeks
- [ ] Advisor reviews every skill: are the right ones included? any missing?
- [ ] Advisor rewrites all 135 descriptors in their own words
- [ ] Advisor validates tier thresholds — are they realistic for Indonesian players?
- [ ] Pilot test with 2–3 real coaches and 10–20 trainees for 4–6 weeks
- [ ] Collect feedback: skills coaches want to merge/split, tier progression speed feedback
- [ ] Iterate to v1 before opening to first paying clubs
- [ ] Lock v1 in DB; future changes require migration plan

---

## 13. What's NOT in this framework (intentionally)

To keep MVP scope tight:

- **Drill library** — what specific drills work each skill. Separate "Drills" feature, post-MVP.
- **Match performance metrics** — win rates, head-to-head. Separate "Matches" feature.
- **Junior-specific track** — same framework, slower expected progression. Add age-adjusted tier names later if needed.
- **Custom skills per club** — V2. MVP only allows enable/disable platform skills.
- **Multiple curriculum tracks per club** — V2. MVP = one curriculum per club.
- **Time-based progression** — tier is by skill level, NOT by sessions completed.
- **Coach-specific descriptors** — coaches see club's descriptors. V2 feature.
- **Trainee self-assessment** — trainees can't score themselves. V2 feature.

---

## 14. Open Questions for Advisor

Things to flag for the certified coach advisor to validate or decide:

1. Is 13 technical skills too many? Should TECH_WALL_BACK + TECH_WALL_SIDE be merged?
2. Should TECH_DROP (chiquita) be a Bronze-tier skill instead of Silver?
3. For Indonesian junior players (most start at 8–12 yo), is the Beginner→Lower Bronze gap realistic?
4. Should mental skills be tracked from Beginner, or only Bronze+ (less subjective at higher levels)?
5. Is "tournament participation" a valid Diamond requirement, or should it be skill-only?
6. Are there shots common in modern padel (e.g. "rulo" or trick shots) we should add?
7. For tier graduation: is "all skills meet minimum" too strict? Should we allow 1–2 skill exceptions?
8. Should serve quality be split into TECH_SERVE + TECH_SERVE_PLACEMENT, or is one enough?

---

## Version

- **v0** (current) — initial framework, built from public coaching knowledge
- **v1** — after advisor refinement (target: before pilot launch)
- **v2** — after pilot feedback (target: 2–3 months post-launch)

---

*Document maintained as the canonical platform default. Workspaces (clubs) inherit this on signup and may override tier names, thresholds, and descriptors. Skill ontology and 1–5 scale are platform-locked.*
