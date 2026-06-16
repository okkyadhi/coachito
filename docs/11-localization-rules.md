# Localization Rules — EN ↔ ID

> What translates and what doesn't. Critical reference for engineering implementing the i18n layer.

## Purpose

PadelCoach ships in **English (EN)** and **Bahasa Indonesia (ID)** at MVP. The translation rule is **selective**, not blanket. Skills, categories, and Spanish padel terms stay in their original form across both locales. UI copy, descriptors, level labels, tier names, and motivational copy translate fully.

This isn't just preference — it's product correctness. International padel vocabulary (bandeja, víbora, chiquita) is the same across all clubs and trainees globally. Translating it would force every coach to re-learn vocabulary they already know.

## What stays in original (never translated)

### Skill categories

```
Technical
Tactical
Physical
Mental
```

Render the same in both EN and ID surfaces.

### Skill names (all 27)

```
Forehand drive
Backhand drive
Forehand volley
Backhand volley
Serve
Return of serve
Defensive lob
Bandeja
Víbora
Smash
Back wall exit
Side wall play
Chiquita / drop shot
Net positioning
Defensive positioning
Shot selection
Partner coordination
Transition play
Reading the game
Footwork & coverage
Split step & reaction
Endurance
Power & explosiveness
Focus & concentration
Composure under pressure
Decision-making speed
Resilience after errors
```

### Spanish padel technique terms (within skill names or copy)

```
Bandeja (no translation)
Víbora (no translation)
Chiquita (no translation)
```

These are international padel vocabulary. Indonesian players who learn padel learn these words *as Spanish*. Translating to "Bola pendek" or similar destroys cross-club, cross-language consistency.

## What translates to Indonesian

### Level labels

| EN | ID |
|----|----|
| 1 Learning | 1 Belajar |
| 2 Developing | 2 Berkembang |
| 3 Functional | 3 Fungsional |
| 4 Proficient | 4 Mampu |
| 5 Mastery | 5 Mahir |

### Tier names

MVP ships only the first three tiers (the coaching focus is beginner-to-bronze). The remaining four are documented for continuity but should not appear in any shipping UI surface until the curriculum expands.

**MVP tiers (active):**

| EN | ID |
|----|----|
| Beginner | Pemula |
| Lower Bronze | Perunggu Muda |
| Bronze | Perunggu |

**Deferred tiers (post-MVP — translations kept ready):**

| EN | ID |
|----|----|
| Silver | Perak |
| Gold | Emas |
| Platinum | Platinum (kept — borrowed) |
| Diamond | Berlian |

### Skill-specific descriptors (135 total — 27 skills × 5 levels)

All descriptors translate fully into natural Indonesian. See `padel-skill-framework-v0.md` § 4 for canonical EN descriptors. Indonesian translations should be done by a native speaker (ideally a coach advisor) to preserve technical accuracy and natural phrasing.

Example — `TECH_FH` Forehand drive:

| Level | EN | ID |
|-------|----|----|
| 1 | Inconsistent contact, ball flies erratically, no swing structure | Kontak tidak konsisten, bola melayang acak, tidak ada struktur ayunan |
| 2 | Makes contact ~6/10 in cooperative rally, no direction control, often into net | Bisa kontak ~6/10 di rally kooperatif, tidak ada kontrol arah, sering ke net |
| 3 | Consistent crosscourt rally at moderate pace, basic depth control | Rally crosscourt konsisten di tempo sedang, kontrol kedalaman dasar |
| 4 | Controls direction & depth in match play, attacks short balls aggressively | Kontrol arah & kedalaman di pertandingan, serang bola pendek dengan agresif |
| 5 | Weapon shot — varies pace, spin, depth, direction at will under pressure | Pukulan andalan — variasi tempo, spin, kedalaman, arah sesuai keinginan di bawah tekanan |

### UI labels and microcopy

All translate. Examples:

| EN | ID |
|----|----|
| Today | Hari ini |
| Trainees | Trainee |
| Sessions | Sesi |
| Reports | Laporan |
| Settings | Setelan |
| Save | Simpan |
| Cancel | Batal |
| Delete | Hapus |
| Optional | Opsional |
| Required | Wajib |
| Not rated | Belum dinilai |
| Score | Skor |
| Note | Catatan |
| Send | Kirim |
| Try again | Coba lagi |
| Refresh | Muat ulang |
| Continue | Lanjut |

### Section headers, prompts, placeholders

All translate. Examples:

| EN | ID |
|----|----|
| How did the session go overall? | Bagaimana sesi berjalan secara keseluruhan? |
| Visible to trainee and parent | Terlihat oleh trainee dan orang tua |
| Add your first trainee | Tambah trainee pertamamu |
| Your skills will appear here | Skill-mu akan muncul di sini |
| What happens next | Apa yang akan terjadi |

### Motivational / trainee-facing copy

Tone matters here. ID translations should feel encouraging, not literal. Examples:

| EN | ID |
|----|----|
| Closer than ever — keep this pace | Lebih dekat dari sebelumnya — pertahankan tempo ini |
| Wins this month | Pencapaian bulan ini |
| Your most consistent stretch yet | Periode paling konsisten sejauh ini |
| Tomorrow keeps the streak going | Besok lanjutkan ritme ini |
| Excited to see where Andi takes this in May | Tidak sabar lihat Andi berkembang di Mei |

### Coach narrative content

Coaches type session summaries and monthly notes in their own language. The text is **stored as-typed** and rendered to whoever reads it. There's no auto-translation.

This means:
- An Indonesian coach writes summary in ID; parent and trainee see it in ID
- An expat coach writes summary in EN; parent reads EN
- Cross-language situations (Indonesian coach with English-speaking parent, rare): coach writes bilingual summary manually, or uses a translation tool externally

### Session focus tags

| EN | ID |
|----|----|
| Drilling | Drill |
| Match play | Pertandingan |
| Conditioning | Kondisioning |
| Mental training | Mental training (kept — borrowed term in IDPC) |
| Technique focus | Fokus teknik |

**Backend storage:** language-neutral codes (`drilling`, `match_play`, `conditioning`, etc.) so display labels can change without breaking data.

### Pricing / plan names

Plan names like "Solo Coach", "Club Starter", "Club Pro" stay English in both locales — they're product brand terms.

Currency formatting:
- EN locale: "Rp 1,500,000 / month" or shorthand "Rp 1.5jt / month"
- ID locale: "Rp 1.500.000 / bulan" or shorthand "Rp 1,5jt / bulan"

Use `Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' })` for full formatting; shorthand "1.5jt / 1,5jt" is a manual override on price labels.

## Borrowed English words kept in ID context

Modern Indonesian sports vocabulary uses several English loanwords without translation. Per the framework localization map (`padel-skill-framework-v0.md` §11):

| Term | Used in ID as |
|------|---------------|
| Trainee | Trainee (alt: Murid; we standardize on "Trainee") |
| Coach | Coach (alt: Pelatih; we standardize on "Coach") |
| Footwork | Footwork (no good ID equivalent) |
| Power | Power (no good ID equivalent) |
| Fokus | Fokus (Indonesian spelling of Focus) |

## Implementation pattern

### Locale file structure

```
locales/
├── en.json
│   ├── ui.*           (all UI labels)
│   ├── levels.*       (level labels)
│   ├── tiers.*        (tier names)
│   ├── descriptors.*  (skill descriptors, keyed by skill_code + level)
│   └── empty.*        (empty state copy)
└── id.json
    └── (same structure)
```

### What is NOT in locale files

```
skills/skills.ts        ← single source of truth for skill names
skills/categories.ts    ← single source of truth for category names
```

These constants live outside the locale system. Components reference them directly:

```ts
import { SKILL_LABELS } from '@/skills/skills';

<Text>{SKILL_LABELS[skillCode]}</Text>  // always "Bandeja", regardless of locale
```

This prevents the trap where someone "translates" "Bandeja" to "Bandeja" in `id.json` and then later well-meaningly changes it to "Bola Layang" or similar.

### Locale switching

- **Default:** Workspace's primary language (set per-club in Settings; default `id` for Indonesia-registered workspaces, `en` for international)
- **Override:** Per-user, in Profile → Language
- **Coach narrative:** stored as-typed, no auto-translate

### Plurals and inflection

Indonesian doesn't pluralize like English. Many places where EN has "1 session / 2 sessions", ID just says "1 sesi / 2 sesi" — same form. Use `Intl.PluralRules('id-ID')` for explicit cases but expect simpler logic.

### Date and time formatting

Use `Intl.DateTimeFormat`:
- EN: `'Sunday, 10 May 2026'`, `'8:00 am'`
- ID: `'Minggu, 10 Mei 2026'`, `'08.00'` (24h, period separator)

Indonesia commonly uses 24h time. AM/PM is uncommon. Always use 24h in ID locale; offer either in EN.

## Common translation pitfalls

| Pitfall | What happens | Fix |
|---------|--------------|-----|
| Translating skill names | "Bandeja" → "Bola layang" — coach who knows bandeja gets confused | Lock skill names outside locale layer |
| Translating "Functional" inconsistently | Sometimes "Fungsional", sometimes "Berfungsi" | Single canonical mapping in `levels.json` |
| Auto-translating coach summaries | Lossy, awkward, breaks coach voice | Don't — store as-typed |
| Forcing tone-flat translation | EN "Closer than ever — keep this pace" → ID "Lebih dekat dari sebelumnya — terus pertahankan kecepatan" (clunky) | Translator should adapt tone, not be literal |
| Pluralizing ID like EN | "1 sesis" / "2 sesis" | Indonesian usually has no plural form |

## Voice in Indonesian

- **Coach app (instructional):** direct, professional, modern. Use "kamu" (informal you) for the coach, not "Anda" (formal). Coaches are mid-30s tech-savvy users, not government officials.
- **Trainee app (encouraging):** warm, supportive, slightly informal. Use "kamu". Avoid English exclamations ("Yes!" or "Awesome!").
- **PDF report (parent-facing):** more formal but not stilted. Use "Anda" sparingly when addressing parent directly; otherwise narrative third person.
- **Error/offline copy:** calm and clear, not apologetic in a Western sense. "Terjadi kesalahan" not "Maaf banget ya, error nih...".

## Localization checklist for engineering

When adding a new screen or feature:

- [ ] All UI labels read from locale file, not hardcoded
- [ ] Skill names imported from `skills.ts`, not from locale
- [ ] Category names imported from `categories.ts`, not from locale
- [ ] Date/time formatted via `Intl.DateTimeFormat` with locale
- [ ] Currency formatted via `Intl.NumberFormat` with `'IDR'`
- [ ] Pluralization uses `Intl.PluralRules` (or just trust ID single-form behavior)
- [ ] Tested in both `en` and `id` locales
- [ ] Translator reviewed copy for natural ID phrasing (not just literal)
- [ ] Long text strings tested at width — Indonesian translations are often 10–20% longer than English

## Future locales

V2 candidates (in rough priority order):

- Spanish (es-ES, es-MX) — global padel community
- Portuguese (pt-BR) — Brazilian padel boom
- Thai (th) — South-East Asia expansion
- Mandarin (zh-CN) — China padel growth

These will follow the same selective-translation pattern. Skill names + Spanish padel terms will stay in original even in es/pt locales.

## Related

- `padel-skill-framework-v0.md` § 11 — canonical EN/ID localization map for tier names, level labels, skill technical names
- `04-coach-assessment.md` — most copy-heavy screen with localization examples
- `08-pdf-report.md` — PDF localization considerations
