# Workspace Settings

> Where the workspace branding, tier naming, curriculum, plan, and members are configured. Two variants: club (full) and personal (simplified).

## Purpose

The screen that **converts a paying workspace** — it's where the SaaS positioning becomes tangible. Admins set up brand identity, choose tier semantics, configure curriculum, and manage members. Live preview at the top shows changes propagating across the app surface.

For solo coaches, this same screen exists in a simplified form (no Members section, "Display name" instead of "Club name", Solo Coach plan).

## Audience

- **Role:** Club Admin or Head Coach (club workspace), or the Solo Coach themselves (personal workspace)
- **Workspace types:** Both, with structural differences
- **Context:** First-time setup right after signup, occasional adjustments later

## Layout — Club variant (top to bottom)

1. **Top nav bar**
   - Center title: "Workspace"
   - Right: "Saved" pill (auto-save indicator with check icon)
2. **Live preview card** (accent-bg fill)
   - Tag (small caps): "LIVE PREVIEW"
   - Logo square (initials or uploaded image)
   - Club name + meta ("Club Pro · 12 coaches · 84 trainees")
   - 3 sample tier pills (using current tier naming — at MVP these are Beginner / Lower Bronze / Bronze)
   - Sample primary button ("Generate report")
   - Foot caption: "This is what coaches, trainees, and parents see across the app and reports."
3. **Branding section**
   - Club name (inline-editable input, right-aligned)
   - Accent color (4 swatch buttons + 1 custom button)
   - Logo row: 50×50 square + "Club logo" / "Square, at least 200×200 px" + "Change" button
4. **Tiers & curriculum section**
   - Tier naming (3-way segmented: Game / Skill / Custom)
   - Default curriculum (row, opens picker)
   - Allow coach overrides (row, toggle Off)
5. **Plan & billing section**
   - Plan icon + "Club Pro" + "Rp 1.5jt / month · Renews 15 May" + "Manage" link
6. **Members section**
   - Coaches (row with count + chevron)
   - Trainees (row with count + chevron)
7. **Danger zone section**
   - "Delete workspace" row in danger color, opens confirmation
8. **Bottom tab bar** — Settings active

## Layout — Personal variant (differences from Club)

1. Nav title: "**My workspace**" (not "Workspace")
2. Live preview shows:
   - Round avatar (not square logo)
   - Coach display name (not club name)
   - Meta: "Solo coach · 18 trainees" (no coach count)
3. Branding section becomes:
   - **Display name** (not "Club name")
   - **City** (new field — solo coach has no club address)
   - Accent color (same)
   - **Profile photo** row: round 50×50 + "Profile photo" / "Optional. Trainees see this in the app." + "Add" button
4. Tiers & curriculum: same (skill rubric is shared platform-wide)
5. Plan & billing: **"Solo Coach" · Rp 100k / month**
6. Above Members section, add **"Upgrade to Club" upsell card** (accent-bg fill): "Coaching with a team? Upgrade to a Club workspace to invite other coaches, share trainees, and manage them together."
7. Members section becomes just:
   - **Active trainees** (single row, no Coaches row)
8. Danger zone: same

## Components used

- Live preview card (accent-bg fill, multiple sub-elements)
- Logo / photo frame (square for club, circle for personal)
- Color swatch row (4 presets + 1 custom button)
- 3-way segmented control (Tier naming)
- Settings rows with chevron / value / inline input variants
- Plan card with icon + name + meta + link
- Upsell card (personal only, accent-bg)
- Saved pill in nav
- Tabler icons: `ti-check`, `ti-color-picker`, `ti-stars`, `ti-user-star`, `ti-building`, `ti-arrow-right`, `ti-chevron-right`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Workspace name | `workspaces.name` | Editable |
| Workspace type | `workspaces.type` | 'club' or 'personal' |
| Brand color | `workspaces.brand_color` (hex) | Default null → uses #378ADD |
| Logo / photo URL | `workspaces.logo_url` | Optional |
| Tier naming style | `workspaces.tier_style` | 'game' / 'skill' / 'custom' |
| Default curriculum ID | `workspaces.curriculum_id` | FK |
| Plan tier | `workspaces.plan` | 'solo_coach' / 'club_starter' / 'club_pro' |
| Renewal date | `subscriptions.renews_at` | |
| Coach count (club only) | `COUNT(memberships WHERE workspace_id=X AND role IN coach roles)` | |
| Trainee count | `COUNT(memberships WHERE role='trainee')` | |
| City (personal only) | `workspaces.city` | Or `users.city` if stored on user |

## Interactions

| Action | Result |
|--------|--------|
| Type in name input | Auto-save after debounce. Live preview updates. Logo initials auto-derive from new name. |
| Tap accent swatch | Set brand color. Update CSS variable. Live preview updates. Persist immediately. |
| Tap custom color button | Open color picker (V1.5 — for MVP, system color picker or hex input modal) |
| Tap Change/Add logo | Native file picker. Upload to storage. Persist URL. |
| Tap tier naming segment | Set tier style. Update preview pills. Persist immediately. |
| Tap Default curriculum row | Open curriculum picker screen |
| Tap Manage on Plan | Navigate to billing portal (external — Stripe Customer Portal or similar) |
| Tap Coaches row (club) | Navigate to Coaches list screen |
| Tap Trainees row | Navigate to Trainees tab |
| Tap Upgrade to Club (personal) | Navigate to plan-comparison and upgrade flow |
| Tap Delete workspace | Confirmation modal: "This deletes all trainees, sessions, assessments, and reports. Type {workspace name} to confirm." |

## States

### Default
Settings populated from workspace data. Auto-save indicator shows "Saved" with check.

### Saving (transient)
Saved pill briefly switches to "Saving..." with spinner, then back to "Saved".

### Failed save
Pill changes to "Failed · Retry" in danger color. Preserve user changes locally.

### Loading (first open)
Skeleton: nav + skeleton preview card + skeleton sections.

### Offline
Banner. Auto-save queues changes. Pill shows "Saved offline" until reconnected.

## Workspace type adaptations

Already covered — this whole screen is the primary place where club vs personal diverges. See above.

The conditional rendering happens at:
- Nav title text
- Preview card sub-elements (logo shape, count line)
- Branding section field labels and additions
- Plan icon and tier
- Upsell card (personal only)
- Members section structure

Backend just toggles on `workspace.type === 'personal'`.

## Localization

| EN | ID |
|----|----|
| Workspace (nav title, club) | Workspace (kept English — borrowed term) |
| My workspace (nav title, personal) | Workspace saya |
| Saved | Tersimpan |
| Saving... | Menyimpan... |
| Live preview | Pratinjau langsung |
| This is what coaches, trainees, and parents see... | Beginilah tampilan yang dilihat coach, trainee, dan orang tua... |
| Branding | Branding (kept English) |
| Club name | Nama klub |
| Display name | Nama tampilan |
| City | Kota |
| Accent color | Warna aksen |
| Club logo | Logo klub |
| Profile photo | Foto profil |
| Square, at least 200×200 px | Persegi, minimal 200×200 px |
| Optional. Trainees see this in the app. | Opsional. Trainee akan melihat ini di app. |
| Change | Ganti |
| Add | Tambah |
| Tiers & curriculum | Tier & kurikulum |
| Tier naming | Penamaan tier |
| Game / Skill / Custom | Game / Skill / Kustom |
| Default curriculum | Kurikulum default |
| Allow coach overrides | Izinkan override coach |
| Plan & billing | Paket & tagihan |
| Club Pro | Club Pro (kept — product name) |
| Solo Coach | Solo Coach (kept — product name) |
| Rp 1.5jt / month | Rp 1.5jt / bulan |
| Renews 15 May | Diperpanjang 15 Mei |
| Manage | Kelola |
| Members | Anggota |
| Coaches | Coach |
| Trainees | Trainee |
| Active trainees | Trainee aktif |
| Coaching with a team? | Coaching dengan tim? |
| Upgrade to Club | Upgrade ke Club |
| Danger zone | Zona berbahaya |
| Delete workspace | Hapus workspace |

Tier-naming preview pills use the chosen mode's labels. At MVP only the first three tiers ship, so "Game" mode preview pills appear as Beginner / Lower Bronze / Bronze (Pemula / Perunggu Muda / Perunggu in ID). Silver / Gold / Platinum / Diamond are documented in the framework but should not render anywhere at MVP.

## Design rationale

**Why auto-save instead of an explicit Save button.** Settings should never have unsaved state. Linear, Notion, Figma all auto-save. The "Saved" pill is calm and informational — no fanfare needed. Anxious "✓ Auto-saved" toasts feel insecure.

**Why the live preview card sits above all the controls.** It's the "magic moment" of the screen — admins see the effect of their changes immediately. Putting it at the top means scrolling down to settings doesn't lose the preview from view (preview persists thanks to scroll, but it's loaded first impression).

**Why initials auto-derive from the workspace name.** Most clubs won't bother uploading a logo on day one. The auto-derived monogram (first 2 word initials, accent color) is a credible fallback that looks intentional, not placeholder.

**Why 4 preset color swatches plus custom.** 4 covers the most common brand directions (blue, terracotta/coral, teal, purple/pink) without overwhelming. Custom is the escape hatch for clubs with strict brand colors. Don't use a full color wheel as the default — most clubs don't have a defined brand color and need help choosing.

**Why tier naming is segmented (3-way), not a row picker.** The 3 options are mutually exclusive and the labels short — segmented is faster to choose and more visible (admin can see all options without tapping into a sub-screen).

**Why the personal variant uses a circular profile photo, club uses a square logo.** Cultural convention: people get circle frames, brands get square frames. A solo coach's identity is *them*, so circle. A club's identity is the brand mark, so square.

**Why "City" exists for personal but not club.** Clubs have a fixed location, often referenced by name. Solo coaches without a club affiliation need a way to express location for trainees and reports. Adding "City" as one input is cheaper than building a full address form.

**Why the upsell card sits above Members in the personal variant.** A solo coach scrolling through settings reaches the upsell card right after Plan — when they're already in commercial mode. Putting it on Today or Trainees screens is noise; settings is the right context.

**Why "Delete workspace" requires typing the workspace name.** Standard destructive-action protection (GitHub, Vercel, Stripe all do this). Tap-confirm is too easy to accidentally trigger; typed-confirm prevents accidents.

## Out of MVP scope

- Multi-color brand palette beyond single accent (V2 — keep restraint)
- Custom CSS for advanced clubs (V2)
- Coach permissions matrix (Head Coach vs Coach roles) (V1.5)
- Trainee groups / cohorts (V1.5)
- Custom field definitions on trainees (V2)
- Custom skill enable/disable (V1.5)
- Custom rubric per club (V2 — clubs only override descriptors at MVP)
- Workspace handover / transfer ownership (V1.5)
- Multi-tenant / sub-workspaces (V2+)
- Analytics export (V2)

## Open questions

1. Can a club have multiple brand colors (e.g., for sub-academies)? **Recommendation:** no at MVP — single accent only.
2. What happens to existing trainees if a club changes tier naming from Game → Skill? Their existing data is preserved (tier IDs are stable codes, only display labels change), but trainees might be confused. **Recommendation:** show a confirmation modal explaining the impact.
3. Logo image dimensions — enforce squareness? **Recommendation:** soft enforce (warning if non-square) but accept any image, render with object-fit: contain.
4. Solo → Club workspace upgrade: data migration semantics? **Recommendation:** workspace.type updates in-place; existing trainees and assessments persist; new "Coaches" management UI becomes available.

## Related screens

- `01-design-principles.md` — theming model (single accent variable)
- `08-pdf-report.md` — where the brand color and logo most visibly appear externally
- `07-invite-and-onboarding.md` — landing page also reads the workspace branding
