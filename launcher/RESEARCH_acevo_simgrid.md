# Competitor Research — acevo.gg & SimGrid Grid Pass

> Captured 2026-06-09 via headless browser (accessibility snapshots, not memory).
> Purpose: harvest features/logic from the two leading AC/sim-racing portals to
> inform **Launch Bay** (`http://localhost:8765/`, `launcher_dashboard.py`).
>
> **acevo.gg is a SimGrid white-label** (footer: "powered by SimGrid"). So the two
> sites share the same data model; acevo is the consumer-facing AC Evo skin,
> SimGrid is the full multi-sim platform + the paid analytics layer (Grid Pass).
>
> Note: `acevo.gg/user_championships/1280924` (the page originally asked about) is
> **Steam-login-gated** — it redirects to Steam OpenID. The structure below is the
> public equivalent rendered from the same templates (`/events/:id/standings`).

---

## 1. acevo.gg — structure & logic

### 1.1 Entity model
Everything is an **Event**. An event is either a `Quick Race`, `Championship`, or
recurring `Daily` series. Each event exposes a **5-tab sub-nav**:

| Tab | URL | Shows |
|-----|-----|-------|
| Schedule | `/events/:id` | Upcoming race instances (the default landing tab) |
| Scoring | `/events/:id/scoring` | Points system / scoring rules |
| Rounds | `/events/:id/rounds` | Full calendar of rounds |
| Results | `/events/:id/results?race_id=&round_id=` | Per-race finishing order |
| Standings | `/events/:id/standings` | Aggregated championship table |

### 1.2 Event header (persists across all tabs)
- Badge row: **type** (`Quick Race` / `Championship`) + **price** (`Free`)
- Hero artwork tile, title (`<h1>`), one-line blurb
- **"Hosted by"** + sim/platform chips (`AC Evo on PC`)
- **Session Details card**:
  - Conditions with weather icons (`Clear`, `Variable`)
  - Pitstops (`No Pitstops`)
  - 3-segment **session pill strip**: `2 min practice · 5 min qualifying · 10 min race`
  - Honest total-time line: *"You will need 17min+ to complete this event."*
  - **Platform / Simulator / Track / Class** definition list
- **Live countdown**: "Registration Closes In — 00 Hrs 15 Min 01 Sec"
- "Classes & Cars" accordion
- "Join the Conversation" Discord card

### 1.3 Schedule tab — table of race instances
Columns: date/time (or **`Now Live`**) · track · `Race 65 · Week 28 · Round 1` ·
**entrant count** · state-dependent action cell.
Action cell states observed: `results` (link) / `Grid Open` / `closed` / `Sign In`.
Helper note: *"Registration opens 4 hours and closes 30 seconds before the session."*

### 1.4 Standings tab — the championship table (core of `user_championships`)
Columns:

| P | Driver | Rating · Tier | Pen | R1 | R2… | PTS |
|---|--------|---------------|-----|----|----|-----|

- **Driver cell**: avatar + name + country flag emoji (🇫🇷 🇨🇦 🇮🇹 …)
- **Rating cell**: `2,828 · silver` — numeric Grid Rating + **colored tier badge**
  (`bronze` / `silver` / `gold` / `platinum`)
- **Pen** = penalty points column
- **One column per round** (`R1`, `R2`…); the header links to that round's results
- **PTS** = bold total
- Grouped/filtered by **class** (button tabs, e.g. "Mazda MX-5 Cup")
- **Paginated 40 rows/page** (`?page=2…`)

### 1.5 Homepage — Daily Racing card grid
Each card: artwork · type+price badges · session pill strip · Conditions/Track/Class
definition list · **"Upcoming Races"** mini-list (grid-open times + **live entrant
count** + `Grid Open` link). Footer "Browse All Daily Events" CTA.

---

## 2. SimGrid — Grid Pass (`thesimgrid.com/pass`)

The paid tier. This is where the **logic/feature depth** lives. It's a freemium
SaaS: free racing + paid analytics.

### 2.1 Pricing / tier logic
| | Free | Grid Pass |
|---|------|-----------|
| Price | $0 forever | **$5.99/mo** per driver (Chargebee, auto-renew, VAT excl.) |
| League racing | Unlimited | Unlimited |
| Ranked racing | ✓ | ✓ (`New!`) |
| Registration window | 4 hours | **8 hours** |
| Teams / Driver Profiles / Grid Rating / Driving Stats / Perf Analysis / Hide Ads / Calendar Feed | ✓ | ✓ |
| **SimGrid Seasons** | — | ✓ |
| Avatar blue ring, Discord Pro role | — | ✓ |

Note the gating logic: the free tier already lists Perf Analysis etc., but the
**deep app + Seasons** are the paid unlock. The pass is sold partly as
**platform support** ("Stand Out" — cosmetic blue ring + Discord role).

### 2.2 Performance Analysis app (the flagship feature)
"See every lap from every stint and every race." Logic:
- **Stints in detail** — solo and team events
- **Compare stints** side-by-side (teammate vs teammate, team vs team)
- **Positions gained / lost** flagged per lap (colored markers)
- Per-driver stint card metrics:
  `Laps · Valid Laps · Valid Laps % · Drive Time · Best · Average · Optimal`
- **Lap-by-lap list**, color-coded, with per-lap position-gained/lost icons and an
  **AVG line** chart overlay
- Sub-themes: *"No place to hide"*, *"Who was carrying the team?"*,
  *"Lap by Lap Analysis"* (Fastest Laps, Valid Lap %, **Rising Average**,
  Positions Gained/Lost, Laps from every Stint, Stint Driving Time, Compare Teammates)
- Has public **Solo Demo** and **Team Demo** deep-links.

### 2.3 In-depth statistics (driver career profile)
- **Grid Rating** + **Grid Rating Progress** line chart (per race, across sims/platforms)
- **Wins & Podiums**, **Laps Driven**, **Events Competed**, **Performance Ratios**
- **Activity Overview** tiles: `Events · Rounds · Race Sessions · Withdrawals · DNS · DNF · DSQ`
- **Laps Driven** block: Total (Q+R) / Race / Qualifying / Fastest Laps — each with a
  **percentile vs field** (`99.1%`) linking to a leaderboard compare view
- **Performance Ratios**: `Wins`, `Win Ratio %`

### 2.4 Favourite cars & classes
Three small tables: **Most Lapped Cars**, **Most Lapped Car Classes**,
**Most Successful Cars** (by *Avg Position*). Same pattern repeated for tracks:
**Most Lapped Circuits** + **Most Successful Circuits** (Avg Position).

### 2.5 "But that is not all" — secondary perks
- **Calendar Sync** (personal calendar + reminders)
- **Stand Out** (blue avatar ring, site-wide)
- **Discord Role** (private channels)
- **Disable Adverts**

### 2.6 Platform IA (global nav)
`Home · Race · Hosts(/communities) · Tools · Pass` + global **search**
("Community, Championship, Circuit etc"). Footer surfaces **Leaderboards**,
**Calendar**, **Communities**, Coach Dave Academy (setups/coaching) cross-sell.

---

## 3. What maps to Launch Bay

Launch Bay today *fires* solo AC challenges (81 tiles / 8 series) but has no
**persistence / standings / career analytics** layer. That's exactly what both
sites are built around. Ranked by value:

1. **Season Standings page** ⭐ — biggest new capability. Aggregate Pablo's results
   across challenges into a points table (`P · Driver · Rating·Tier · Pen · R1… · PTS`).
   Solo, so populate the grid with **AI/ghost rivals** (Verstappen, Lando, benchmark
   drivers already used) to give a leaderboard to climb. Turns 81 disconnected tiles
   into a championship arc. *(Pablo chose to keep this as spec for now, 2026-06-09.)*

2. **5-tab event template** — add `Overview · Rounds · Results · Standings` sub-nav to
   existing event pages (N24, Monaco). Already have hero + gallery; tabs make them feel
   like a real series page.

3. **Driver career profile / stats** (from Grid Pass §2.3–2.4): laps driven, events,
   DNF/DNS, win ratio, **Grid Rating progress chart** (ties into Pablo's iRating ~1352),
   **Most Lapped / Most Successful cars & tracks** tables. Launch Bay already parses
   results + has a Recharts ProgressionChart — this is mostly aggregation.

4. **Performance Analysis (lap-by-lap)** (§2.2): per-stint lap list, color-coded,
   Best/Avg/Optimal, positions gained/lost. Highest-effort but the genuine "wow".

5. **Session-detail card on cards** (acevo §1.2): practice/qual/race pill strip +
   **tier badge** + honest time estimate. Cheap, very legible.

6. **Per-round results-as-links** + **state cells** (`Now Live` / `closed` / count)
   in a schedule table — maps to the existing "Active challenges" concept.

---

## 4. Sources (this session)
- `https://acevo.gg/` (homepage card grid)
- `https://acevo.gg/events/25127` (event Schedule tab + header)
- `https://acevo.gg/events/25127/standings` (championship standings table)
- `https://www.thesimgrid.com/pass` (Grid Pass pricing + feature/logic breakdown)
- `acevo.gg/user_championships/1280924` — Steam-login-gated, not directly viewable.
