# Error & Offline States

> Pattern library for the app's behavior when something's wrong — offline, sync pending, fetch failed, server error, stale data, loading.

## Purpose

Every screen needs to gracefully handle 5 distinct failure modes. This doc defines each pattern so engineering implements them consistently across the app, not ad-hoc per screen.

The product's promise is "your assessments and notes are never lost." Delivering on that promise visually is what builds trust.

## Tone & color guidelines

- **Offline ≠ error.** Offline is a state — calm, amber. Error is broken — neutral icon for network, red-tinted for server.
- **Reserve red for true errors.** Failed network = gray. Server 5xx = red-tinted icon (not red bg). Critical destructive confirmation = full red. Otherwise red stops meaning anything.
- **Never say "Oops!"** Adults find that condescending.
- **Always offer retry.** Every error state has a "Try again" primary CTA. Never strand the user.
- **Status page link earns trust.** "Check service status" beats vague apology.

## Pattern 1 — Offline banner

**When:** Network connection lost, app continues to work locally.

**Where:** Top of every screen, persists until reconnected.

```
┌─[Banner]──────────────────────────────────┐
│ [icon]  You're offline                    │
│         Changes are saved locally and     │
│         will sync when you're back online.│
└───────────────────────────────────────────┘
```

- Background: `--color-background-warning` (amber)
- Icon: `ti-cloud-off`, `--color-text-warning`
- Title: 13px, weight 500, `--color-text-warning`
- Sub: 11px, `--color-text-warning` at 0.85 opacity
- Border: 0.5px hairline in matching warning color, 0.3 alpha
- Border-radius: 10px
- Non-blocking — app continues to work

**Behavior:**
- Banner appears within ~2 seconds of network loss (debounced to avoid flicker)
- Persists across navigation
- Auto-dismisses on reconnect, replaced briefly by "All caught up" toast (~2s) at bottom of screen

## Pattern 2 — Sync indicator on item

**When:** A specific record (assessment, summary, settings change) was saved locally and is awaiting sync, OR has just synced.

**Where:** Inline pill on the affected list item.

```
┌─[Trainee row]───────────────────────────┐
│ [Avatar]  Andi Pratama                  │
│           Assessment · 8 skills         │
│                       [☁ Saved offline] │
└─────────────────────────────────────────┘
```

**Variants:**

| Variant | Icon | Background | Text color |
|---------|------|------------|-----------|
| Saved offline (pending) | `ti-cloud-upload` | `--color-background-secondary` | `--color-text-tertiary` |
| Syncing | `ti-cloud-upload` (animated) | `--color-background-info` | `--color-text-info` |
| Synced | `ti-check` | `--color-background-success` | `--color-text-success` |

**Behavior:**
- Pill appears on save while offline
- Transitions to "Syncing" briefly when reconnect happens
- Transitions to "Synced" on success
- "Synced" pill auto-fades after 5 seconds — user doesn't need to dismiss

## Pattern 3 — Couldn't load (network error full screen)

**When:** A screen's primary data can't be fetched and there's no useful cache.

**Where:** Full screen replacing the content area; nav bar and tab bar still render.

```
┌─[Full-screen state]────────────────────┐
│                                        │
│         [Icon, 64×64, gray]            │
│                                        │
│           Couldn't load                │
│                                        │
│    Check your connection and try       │
│    again. Your saved data is still     │
│    here when you're back online.       │
│                                        │
│         [Try again] (primary)          │
│         [Continue offline] (link)      │
│                                        │
└────────────────────────────────────────┘
```

- Icon: `ti-wifi-off`, neutral gray (`--color-text-tertiary`), 64×64 circle with secondary bg + hairline
- Title: 17px, weight 500
- Description: 13px, secondary, max 260px wide
- Primary CTA: "Try again" with `ti-refresh` icon
- Secondary link: "Continue offline" — drops into cached data view if available

**Voice:** calm. This isn't user's fault.

## Pattern 4 — Something went wrong (server error full screen)

**When:** Backend returns 5xx or unexpected error. Distinct from network failure.

**Where:** Full screen.

```
┌─[Full-screen state]────────────────────┐
│                                        │
│         [Icon, 64×64, danger]          │
│                                        │
│        Something went wrong            │
│                                        │
│   We're looking into it. This usually  │
│   clears up in a few minutes — try     │
│   again, or check status.              │
│                                        │
│         [Try again] (primary)          │
│         [Check service status] (link)  │
│                                        │
└────────────────────────────────────────┘
```

- Icon: `ti-alert-triangle`, `--color-text-danger` color, danger-bg fill — but **not full red bg** (just tinted icon container)
- Title, description, CTAs same dimensions as Pattern 3
- Secondary link goes to `status.padelcoach.app` (status page, can be a stub at MVP)

**Voice:** apologetic but transparent. Imply ownership.

**Why distinct from Pattern 3:** different icon + different secondary action. Network failure offers offline mode; server failure offers status page.

## Pattern 5 — Stale data warning

**When:** Cached data is older than ~5 minutes and a background refresh failed silently. The data is usable but not fresh.

**Where:** Subtle banner above the screen content.

```
┌─[Banner]─────────────────────────────────┐
│ [clock]  Showing data from 12 min ago   │
│                              [Refresh →]│
└──────────────────────────────────────────┘
```

- Background: `--color-background-secondary`, 0.5px hairline border
- Icon: `ti-clock`, secondary color
- Text: 12px secondary
- Action: tappable, accent color, weight 500
- Border-radius: 10px

**Behavior:**
- Appears only when both: cache > 5 min old AND background refresh failed
- Tappable to retry
- Dismisses on successful refresh

## Pattern 6 — Loading skeleton

**When:** First load of a screen, or pull-to-refresh on a screen with no cache.

**Where:** Replaces the content area while data is fetching.

```
┌─[Skeleton row]──────────────────────────┐
│ [○]  ████████████████████████░░░░       │
│      ████████████░░░░░░                 │
└─────────────────────────────────────────┘
┌─[Skeleton row]──────────────────────────┐
│ [○]  ████████████████░░░░░░░░░░░░       │
│      ██████████████░░░░                 │
└─────────────────────────────────────────┘
```

- Shapes match the real content (avatar circle + 2 lines for trainee lists; cards for card-shaped content)
- Pulse animation: opacity 0.6 → 0.3 → 0.6, 1.6s cycle, ease-in-out
- Background: `--color-background-secondary`
- Border-radius: 6px on lines, 50% on circles
- 3 rows typical; never full-screen of skeleton

**Pattern rules:**
- Use only on first load, NOT on every navigation (cached navigation should be instant)
- Skeleton shape matches content shape — don't show generic shimmer rectangles
- Pulse animation, not spinner — feels less "system" and more "anticipation"

## Pattern rules (cross-cutting)

| Rule | Why |
|------|-----|
| Offline ≠ error | Different visual treatment. Don't reuse error patterns for offline. |
| Always offer retry | Never strand the user with no path forward. |
| Sync indicators auto-clear | "Synced ✓" doesn't need user dismissal — fade after 5s. |
| Voice stays calm | "Couldn't load" not "Oh no, something went wrong!" |
| Status page link in server errors | Transparency builds trust. Even a stub status page works. |
| Cache aggressively | Stale data with banner > full error screen. |
| Local writes are eventually-synced | Coach can record assessment offline; never lose data. |
| Skeletons only on cold load | Don't show skeletons on every back/forward navigation. |

## Architecture implications

For these patterns to work, the app needs:

### Local-first writes

```js
// Pseudocode
async function saveAssessment(data) {
  await localDB.assessments.put(data);     // 1. Always write local first
  syncQueue.push({ type: 'assessment', data });  // 2. Queue for sync
  return { savedLocally: true };           // 3. Immediate return
}

// Background sync service
async function flushSyncQueue() {
  if (!navigator.onLine) return;
  for (const item of syncQueue) {
    try {
      await api.upsert(item);
      syncQueue.remove(item);
      uiBus.emit('synced', item.id);
    } catch { /* retry on next flush */ }
  }
}
```

### Connectivity detection

- Listen to `navigator.onLine` events on web; equivalent on RN (`@react-native-community/netinfo`)
- Debounce ~2s before showing offline banner (avoid flicker on transient drops)
- On reconnect, trigger `flushSyncQueue()` and show "All caught up" toast

### Cache freshness tracking

- Each cached resource has a `fetchedAt` timestamp
- On screen mount, check freshness:
  - Fresh (< 1 min): use cache, no refetch
  - Stale (1–5 min): use cache, background refetch
  - Stale (> 5 min): use cache, foreground refetch with skeleton
  - Background refetch fails: show stale banner

### Idempotent writes

Most PadelCoach writes are idempotent (latest wins per skill, latest summary text per session). This makes the offline-replay pattern simple — no conflict resolution needed for MVP.

## Localization

| EN | ID |
|----|----|
| You're offline | Kamu sedang offline |
| Changes are saved locally and will sync when you're back online. | Perubahan tersimpan lokal dan akan sinkronisasi saat online lagi. |
| All caught up | Semua tersinkron |
| Saved offline | Tersimpan offline |
| Syncing | Sinkronisasi |
| Synced | Tersinkron |
| Couldn't load | Gagal memuat |
| Check your connection and try again. Your saved data is still here when you're back online. | Cek koneksi dan coba lagi. Data yang sudah tersimpan tetap ada saat kamu online lagi. |
| Try again | Coba lagi |
| Continue offline | Lanjut offline |
| Something went wrong | Terjadi kesalahan |
| We're looking into it. This usually clears up in a few minutes — try again, or check status. | Kami sedang menanganinya. Biasanya selesai dalam beberapa menit — coba lagi, atau cek status. |
| Check service status | Cek status layanan |
| Showing data from 12 minutes ago | Menampilkan data dari 12 menit lalu |
| Refresh | Muat ulang |

## Out of MVP scope

- Detailed conflict resolution UI (V2 — needed if non-idempotent writes get added)
- Offline mode for read-only data (V1.5 — full offline catalog of skills/descriptors so coach can reference offline)
- Network speed warnings ("slow connection") (V2)
- Per-screen retry policies (V2)
- Background sync notifications (V2)

## Related

- Each page's "States" section references these patterns
- `09-empty-states.md` — distinct from these (empty = success, no data; error = failure)
