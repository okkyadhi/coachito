# Invite & Onboarding Flow

> The 4-step journey from coach adding a trainee to the trainee landing in the app, plus the public web landing page that catches link clicks before app install.

## Purpose

Convert a coach's intent ("add this trainee") into an installed-app user as quickly as possible. The flow has to feel professional enough that clubs are comfortable forwarding the invite to their members, simple enough for trainees who've never used a coaching app, and resilient to the WhatsApp-link-clicked-before-install scenario.

## The flow at a glance

```
Step 1  →  Coach taps "Add trainee" (in-app form)
Step 2  →  Coach taps "Send WhatsApp invite" — opens wa.me link with templated message
Step 3  →  Trainee receives WhatsApp message with invite link + branded link unfurl
Step 4a →  If app installed: deep link opens trainee in welcome screen → Sign in → first-run home
Step 4b →  If app NOT installed: link opens public web landing page → install CTA → continue
```

## Audience

- **Step 1–2:** Coach
- **Step 3+:** Trainee (often a parent forwarding to a child for junior players)

## Step 1 — Add trainee form (in-app)

### Layout

1. **Top nav bar**
   - Left: "Cancel" (X icon)
   - Center: "Add trainee" (title)
2. **Trainee details section**
   - Name (text input, required)
   - WhatsApp (text input, required, prefilled "+62 ")
   - Date of birth (text input, optional)
3. **Parent or guardian section**
   - Parent WhatsApp (text input, optional)
4. **Coaching section**
   - Starting tier (row picker, default "Beginner"; MVP options: Beginner / Lower Bronze / Bronze only)
   - Lead coach (row picker, default current user)
5. **Action buttons**
   - Primary: "Send WhatsApp invite" (with WhatsApp icon)
   - Secondary: "Save without invite"
6. **Bottom tab bar** — Trainees active

### Why so few required fields

Only **Name and WhatsApp number** are required. Everything else is optional. Coach Novia adding 30 trainees to a new club shouldn't fill 8 fields per trainee. The trainee fills out the rest themselves after sign-in.

### Save without invite

Important for in-person scenarios: coach sitting with the trainee, just wants to start tracking. Or shared family phones where the parent number gets the invite later, not now.

## Step 2 — WhatsApp message

When coach taps "Send WhatsApp invite":

```
window.open(
  `https://wa.me/${phoneNumber}?text=${encodeURIComponent(messageTemplate)}`,
  '_blank'
);
```

Templated message (EN):

```
Hi {trainee_first_name}! Coach {coach_name} from {workspace_name} here. You've been
invited to track your padel progress with us.

Tap the link below to join — takes about 30 seconds:
https://padelcoach.app/i/{invite_token}
```

Templated message (ID):

```
Halo {trainee_first_name}! Coach {coach_name} dari {workspace_name} di sini. Kamu
diundang untuk track progres padel-mu bersama kami.

Tap link di bawah untuk gabung — sekitar 30 detik:
https://padelcoach.app/i/{invite_token}
```

The invite token is short and meaningful (`sp-andi-9k3f` = workspace `sp` + trainee handle + random suffix). Tokens are one-time-use, expire in 7 days.

## Step 3 — Trainee's WhatsApp view

Trainee opens WhatsApp, sees the message from Coach. The link **unfurls** with club-branded preview:

```
[White chat bubble]
"Hi Andi! Coach Novia from Senayan Padel Club here..."

[Embedded preview with accent-color left border]
Senayan Padel Club
Track your skills, see your progress, climb the tiers.
padelcoach.app
```

### Why the unfurl matters

The preview card is **the moment** the trainee judges the product before tapping. Generic preview ("padelcoach.app — Track your padel progress") looks like spam. Club-branded preview looks like a real institution. Implemented via dynamic OG meta tags on the landing page — the page renders different `og:title`, `og:description`, and `og:image` based on the `workspace_id` in the invite token.

### Server-side requirement

The `/i/{token}` endpoint must:
1. Look up the workspace from the token
2. Render HTML with workspace-specific `<meta property="og:*">` tags
3. Cache aggressively (24h) since unfurls are CDN-fetched

## Step 4a — Welcome screen (in-app, if installed)

If the trainee has the app installed, the universal link opens directly into the welcome screen (skipping the web landing page):

### Layout

1. **Status bar**
2. **Welcome body** (centered, vertical):
   - Large logo square (72×72, accent fill, club initials)
   - Title: "You're invited"
   - Subtitle: "Coach Novia has invited you to track your padel progress with Senayan Padel Club."
   - Invite card (white, hairline border): club mark + name + "Invited by Coach Novia · Jakarta" + check icon
   - Spacer (flex)
3. **Buttons stack** (bottom):
   - Primary: "Continue with Google" (Google icon)
   - Secondary: "Continue with email"
   - Foot text: "By continuing you agree to PadelCoach's Terms and Privacy Policy."

### Sign-in

Google Sign-In is the recommended path. Email is fallback for users without Google accounts. Phone OTP is **deferred** to V1.5 per MVP scope.

### After sign-in

Server matches the invite token to the workspace, creates trainee membership, navigates to first-run home (Step 5).

## Step 4b — Public web landing page (if NOT installed)

When the WhatsApp link opens in the browser before app install:

### Layout (mobile-first, also responsive for desktop)

1. **Browser bar** (rendered by browser; faux'd in mockups)
2. **Page header**
   - Club mark (28×28 accent fill)
   - Club name
   - Help button (right)
3. **Hero block** (centered)
   - Large icon (72×72, accent fill)
   - Title: "Hi Andi — you're invited"
   - Description: "Track your padel progress with Senayan Padel Club. See your skills, follow your tier journey, and read your coach's notes after every session."
4. **Coach card**
   - Coach avatar + "Coach Novia" + "Head coach · Jakarta" + "Invited you" pill
5. **OS-detect callout** (optional)
   - "We detected you're on Android — here's the easy way" (or iOS variant)
6. **CTA stack**
   - Primary: "Get the app on Google Play" (or App Store, OS-dependent)
   - Secondary: "Or download for iPhone" (or Android)
   - Tertiary link: "Continue in browser →"
7. **"What happens next" explainer**
   - 3 numbered steps in light-gray section
8. **Meta block**
   - "This invite expires in 7 days"
   - "Not Andi? This isn't for me" link
9. **Footer**
   - "Powered by PadelCoach · About · Privacy · Terms"

### OS detection

Server reads `User-Agent` header, swaps the primary CTA accordingly:
- Android UA → Primary = Google Play
- iOS UA → Primary = App Store
- Desktop UA → Both badges shown equally

### "Continue in browser"

Fallback path: opens the web app at `/login?invite_token={token}` for users who don't want to install.

## Step 5 — First-run home (in-app, after sign-in)

The trainee's home screen on day-zero. See `05-trainee-home.md` "First-run" state.

### Layout differences from default home

- Greeting: "Welcome, Andi" + "Let's get you started" (one-time copy)
- "Your first session" card highlighted (accent-bg fill)
- Empty state in the radar slot: "Your skills will appear here" with `ti-chart-radar` icon
- "What happens next" 3-step list:
  1. Show up to your session at Court 2
  2. Coach Novia rates your skills during the session
  3. Open the app after to see your progress and tier
- Bottom tab bar same as default

After first assessment, this empty-first-run layout is replaced by the standard home (achievement card, tier progress, etc.).

## Components used across the flow

- Form inputs (text, picker rows)
- Primary / secondary / link buttons
- WhatsApp-styled chat bubble + link unfurl card
- Welcome screen with logo + invite card + sign-in buttons
- Public-page hero with branded mark
- OS-detect callout banner
- 3-step numbered explainer list
- Tabler icons: `ti-x`, `ti-brand-whatsapp`, `ti-chevron-left`, `ti-brand-google`, `ti-mail`, `ti-circle-check`, `ti-brand-google-play`, `ti-brand-apple`, `ti-device-mobile`, `ti-clock`, `ti-lock`, `ti-calendar-event`, `ti-chart-radar`, `ti-bell`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Coach display name | `users.display_name` | Shown in WhatsApp message and welcome screen |
| Workspace name | `workspaces.name` | |
| Workspace brand color | `workspaces.brand_color` | Drives accent across welcome/landing |
| Workspace logo | `workspaces.logo_url` | Falls back to initials |
| Invite token | `invites.token` | Format: `{workspace_slug}-{trainee_handle}-{random}` |
| Token expiry | `invites.expires_at` | 7 days default |
| Trainee first name | `trainees.name` | First word, used in greeting |
| Detected OS | `User-Agent` parsing on landing page | |

## Invite token model

```sql
CREATE TABLE invites (
  id UUID PRIMARY KEY,
  token VARCHAR(50) UNIQUE NOT NULL,
  workspace_id UUID NOT NULL REFERENCES workspaces(id),
  trainee_id UUID NOT NULL REFERENCES trainees(id),
  invited_by UUID NOT NULL REFERENCES users(id),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

When trainee signs in via the invite link:
1. Verify token is not expired and not consumed
2. Match trainee_id to the user's authenticated identity (or create membership)
3. Set `consumed_at = NOW()` (one-shot)
4. Create `memberships` row connecting user to workspace as role=trainee

## States

### Invite token expired
Web landing page shows: "This invite has expired. Ask Coach Novia to send a new one." with link to coach contact (WhatsApp).

### Invite token consumed (already used)
"You've already joined Senayan Padel Club. Open in app." with deep link.

### Wrong identity (e.g., signed in as different user)
"This invite is for {trainee_first_name}. Switch accounts or ask your coach for a new invite."

### App installed but no internet during welcome
Local welcome screen still renders (cached). Sign-in fails gracefully with retry.

## Localization

| EN | ID |
|----|----|
| Cancel | Batal |
| Add trainee | Tambah trainee |
| Trainee details | Data trainee |
| Name | Nama |
| WhatsApp | WhatsApp |
| Date of birth | Tanggal lahir |
| Optional | Opsional |
| Parent or guardian | Orang tua atau wali |
| Parent WhatsApp | WhatsApp orang tua |
| Coaching | Coaching |
| Starting tier | Tier awal |
| Lead coach | Coach utama |
| Send WhatsApp invite | Kirim undangan WhatsApp |
| Save without invite | Simpan tanpa undangan |
| You're invited | Kamu diundang |
| Coach Novia has invited you to track your padel progress... | Coach Novia mengundangmu untuk track progres padel... |
| Invited by Coach Novia · Jakarta | Diundang oleh Coach Novia · Jakarta |
| Continue with Google | Lanjut dengan Google |
| Continue with email | Lanjut dengan email |
| By continuing you agree to PadelCoach's Terms and Privacy Policy. | Dengan melanjutkan kamu menyetujui Syarat & Kebijakan Privasi PadelCoach. |
| Hi Andi — you're invited | Halo Andi — kamu diundang |
| Track your padel progress with Senayan Padel Club... | Track progres padel-mu bersama Senayan Padel Club... |
| Help | Bantuan |
| You're on Android — here's the easy way | Kamu pakai Android — ini cara paling mudah |
| Get the app on Google Play | Dapatkan app di Google Play |
| Or download for iPhone | Atau download untuk iPhone |
| Continue in browser → | Lanjut di browser → |
| What happens next | Apa yang akan terjadi |
| Install the app and sign in with Google. Takes about 30 seconds — no email password to remember. | Install app dan masuk dengan Google. Sekitar 30 detik — tanpa perlu hafal password. |
| Show up to your first session tomorrow at 8:00 with Coach Novia at Court 2. | Datang ke sesi pertama besok jam 08.00 dengan Coach Novia di Lapangan 2. |
| See your progress the moment Coach Novia finishes the assessment — skills, tier, coach's note. | Lihat progresmu langsung setelah Coach Novia selesai menilai — skill, tier, catatan coach. |
| This invite expires in 7 days | Undangan ini kedaluwarsa dalam 7 hari |
| Not Andi? This isn't for me | Bukan Andi? Ini bukan untuk saya |
| Powered by PadelCoach | Didukung oleh PadelCoach |
| Welcome, Andi | Selamat datang, Andi |
| Let's get you started. | Yuk mulai perjalananmu. |
| Your first session | Sesi pertamamu |
| Tomorrow, 8:00 am · Court 2 · with Coach Novia | Besok, 08.00 · Lapangan 2 · dengan Coach Novia |
| Your skills will appear here | Skill-mu akan muncul di sini |
| After your first session, Coach Novia will rate your skills... | Setelah sesi pertama, Coach Novia akan menilai skill-mu... |

## Design rationale

**Why phone is the only required field besides name.** Friction kills conversion. Every additional required field on the Add Trainee form drops completion rate. Trainees fill in DOB, parent contact, and other details after they sign in.

**Why WhatsApp is the invite channel, not SMS or email.** Indonesia uses WhatsApp ubiquitously. SMS feels formal/transactional; email is rarely opened by mobile-first users. The wa.me URL scheme requires no API integration — coach taps button, WhatsApp opens, message pre-filled.

**Why invite tokens contain a workspace slug + trainee handle.** Two reasons: (1) makes the URL human-readable in the unfurl card and chat preview ("padelcoach.app/i/sp-andi-9k3f" is recognizable), (2) helps debugging — engineers reading logs immediately know which workspace and trainee a token is for.

**Why the welcome screen carries CLUB branding, not PadelCoach branding.** This is the SaaS-vs-white-label distinction handled correctly. It's PadelCoach for Senayan, branded as Senayan. Andi never has to learn "PadelCoach" as a brand. White-label feels at 80% the cost of full white-label engineering.

**Why "Continue with Google" is primary, "email" is secondary.** Google handles auth + identity in 2 taps; email requires password creation, verification, and a longer flow. For Indonesia where Android is dominant, Google account presence is near-universal.

**Why the empty radar in first-run home has no CTA.** Trainee can't fix the empty state — only the coach can, by assessing them. Adding a "Hurry coach up" or similar CTA is awkward. The 3-step explainer below sets the right expectation.

**Why we surface "tomorrow's session" prominently in first-run.** Concrete next-step orientation. Most apps' onboarding leaves the user at a generic dashboard; this one says "you have a real thing happening tomorrow at 8 am with a real person."

## Out of MVP scope

- Phone OTP sign-in (V1.5)
- SMS invite fallback (V2 — unlikely to ever ship; WhatsApp is dominant)
- Email-only invite path (V1.5 — for parents without WhatsApp)
- Bulk invite (CSV upload) (V1.5)
- QR code invite (V2 — for in-person)
- Coach profile photo on welcome card (V1.5 — nice to have)
- Multi-language detection on landing page based on browser locale (V1.5)
- Auto-detect Indonesia phone format (V1.5 — for MVP, default +62 prefill)
- Resend / revoke invite from coach side (V1.5)

## Open questions

1. If trainee has the app installed but isn't logged in, does the deep link open the welcome screen pre-filled with the invite, or the standard login? **Recommendation:** welcome screen — preserve the invite context.
2. If trainee taps invite link from a different phone than the one in the WhatsApp message, do we still let them sign up? **Recommendation:** yes — phone number is for invite delivery, not identity verification. Identity is via Google/email auth.
3. Token expiry: 7 days fixed, or configurable per workspace? **Recommendation:** 7 days fixed at MVP. Makes UX clear.
4. What if a coach tries to invite a phone number that's already a trainee in another workspace? **Recommendation:** allow — same person can be a trainee in multiple workspaces (e.g., student of two different coaches).
5. Re-invite when expired: same token, new expiry, or new token? **Recommendation:** new token (security). Old token explicitly invalidated.

## Related screens

- `05-trainee-home.md` — first-run home is documented there
- `06-workspace-settings.md` — branding read by the welcome screen and landing page
- `09-empty-states.md` — first-run home references this for the empty radar
- `10-error-offline-states.md` — token errors, offline states
