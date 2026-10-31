# Iterations log

Living build log for **every product/engineering slice**, including work that is not a milestone checklist item (polish, merges, test hardening, CI). Newest first.

**Current version:** `0.6.92`

Versioning: bump **patch** for docs/tests/CI-only; **minor** for user-facing polish or API surface; reserve **major** for milestone-aligned releases (A/B/C/D). Milestone gates still have their own logs ([milestone_a.md](./milestone_a.md), [milestone_b.md](./milestone_b.md), [milestone_c.md](./milestone_c.md)). Outages stay in [incident_log.md](./incident_log.md).

**Standing rule:** end every coding slice with a new version entry here (and bump **Current version**). If the slice also closes milestone checklist items, update that milestone file too — do not fold polish-only work into a closed milestone’s checklist as if it were new C/D scope.

---

## Entry template

```markdown
## X.Y.Z — Short title

**Why:** one line

**What shipped:**
- …

**How to try:** (omit if not user-facing)

**Tests:** (omit if untouched)

**Related:** optional links
```

---

## 0.6.92 — Transparent SVG mark; nav-only on welcome

**Why:** PNG mark had a paper background; large page logo competed with the hero wordmark.

**What shipped:**
- `AhoyMark` redrawn as transparent SVG (sail chevron + pennant + hull)
- `/welcome` shows the mark only in the top nav; hero is wordmark + copy

**How to try:** Open `/welcome` — logo in header only; no boxed background.

---

## 0.6.91 — Welcome landing + email capture

**Why:** Platform gate alone doesn’t explain A-hoy services to prospects.

**What shipped:**
- Public `/welcome` with boat mark hero, Bridge/Engine Room, niches, Harbor/Cruiser/Flagship
- Email acquisition form → `POST /api/v1/marketing/leads` + `marketing_leads` migration
- `/` keeps Ship/Crew gate; “New here? See A-hoy” → `/welcome`

**How to try:** Open `/welcome`, submit an email; confirm row in `marketing_leads`. Apply `005_marketing_leads.sql` if needed.

---

## 0.6.90 — Trail no longer vanishes on long scroll

**Why:** ResizeObserver + pathLength remounts wiped the trail when scrolling far/fast.

**What shipped:**
- Reveal via `pathLength={1}` (no length flicker)
- SVG grows with page height without rebuilding the path
- Debounced layout; stop observing `documentElement` resize-on-scroll

**How to try:** Hard-refresh Manifest and scroll hard to the bottom — trail should stay drawn.

---

## 0.6.89 — No waves on Manifest

**Why:** Manifest should be trail-only; waves competed with the slither.

**What shipped:**
- ShipAtmosphere turns off deck waves on Manifest / queue

**How to try:** Open Manifest — grey trail only, no bottom waves.

---

## 0.6.88 — Trail stays on fast scroll; prior opacity

**Why:** Fast scroll re-rendered the mask at ~0 length so the trail vanished; opacity felt too strong.

**What shipped:**
- Reveal length tied to scroll progress in React (no reset to empty)
- Restored previous dotted stroke opacity / dash pattern

**How to try:** Hard-refresh Manifest and fling-scroll — trail should keep its drawn length.

---

## 0.6.87 — Trail in-frame and more visible

**Why:** Slither swung off-screen and was too faint to notice.

**What shipped:**
- Amp clamped inside the viewport with edge margin
- Stronger stroke, denser dashes, higher opacity (light + dark)

**How to try:** Hard-refresh Manifest — grey trail should stay on-screen and read clearly in the gutters.

---

## 0.6.86 — Smoother, faster Manifest trail

**Why:** Trail rebuilt + binary-searched on every scroll, so draw felt laggy.

**What shipped:**
- Path rebuilds only on layout change; scroll only updates reveal (DOM dasharray)
- Linear scroll→length mapping; softer longer curves, fewer segments

**How to try:** Hard-refresh Manifest and scroll — trail should draw smoothly without hitching.

---

## 0.6.85 — Randomized Manifest trail

**Why:** Path felt identical every visit.

**What shipped:**
- Each session gets a unique L↔R downward slither — random swing length, width, and curve ease
- Seeded so scrolling doesn’t reshuffle mid-page

**How to try:** Hard-refresh Manifest a few times — trail shape/size should change, still left↔right and down.

---

## 0.6.84 — Trail clears Manifest header text

**Why:** Slither started through the Manifest title/subtitle.

**What shipped:**
- Trail starts below the header block, out in the left gutter

**How to try:** Hard-refresh Manifest — grey trail should miss the copy under the title.

---

## 0.6.83 — Shared Manifest column width

**Why:** Feed vs List used different max-widths, so the toggle jumped.

**What shipped:**
- Both layouts share one `max-w-lg` column and the same chrome padding

**How to try:** Manifest → toggle Feed / List — toolbar stays put.

---

## 0.6.82 — Manifest Feed / List toggle

**Why:** Keep both the social feed and the earlier compact list.

**What shipped:**
- Feed vs List chooser on Manifest (persists in localStorage)
- Same approve / edit / swap actions in both layouts

**How to try:** Manifest → switch Feed / List in the toolbar.

---

## 0.6.81 — Manifest as social feed

**Why:** Queue cards read like an admin list, not a captain’s content feed.

**What shipped:**
- Feed posts: avatar + business name, square media, caption under image, status badge
- Narrow feed column; relative timestamps; actions under each post when awaiting

**How to try:** Open Manifest — scroll a social-style feed of posts to approve.

---

## 0.6.80 — Drop Crew lantern glow

**Why:** Red silhouette ball on Crew was unwanted.

**What shipped:**
- Removed the swaying lantern glow from Crew atmosphere

**How to try:** Hard-refresh `/crew` — kelp/copper hawsers only, no red orb.

---

## 0.6.79 — Crew wave colors

**Why:** Crew hawsers shared Captain’s grey/crimson and didn’t read as Crew.

**What shipped:**
- Hawser bands use kelp + copper (indigo fitting) instead of fg/lantern

**How to try:** Hard-refresh `/crew` — teal and indigo ropes, not grey/crimson.

---

## 0.6.78 — Subtle Crew, still solid

**Why:** Softening Crew reintroduced beaded “dots” via round caps on stretched SVGs.

**What shipped:**
- Captain-level opacity/fill kept
- Solid continuous strokes only (`butt`/`miter`, explicit `strokeDasharray="none"`)

**How to try:** Hard-refresh `/crew` — quiet solid hawsers, no dots.

---

## 0.6.77 — Subtler Crew atmosphere

**Why:** Crew hawsers/lantern were louder than Captain’s quiet waves.

**What shipped:**
- Matched Ship wave opacities (0.14 / 0.22) and stroke weight
- Softer lantern glow + gentler sway; vignette/band size aligned with Ship

**How to try:** Hard-refresh `/crew` — ropes should sit as quiet as Ship waves.

---

## 0.6.76 — No beads on Crew ropes

**Why:** Dual round-cap strands looked like random dots when the SVG stretched.

**What shipped:**
- One solid stroke per hawser; butt caps (no dash, no double strand)

**How to try:** Hard-refresh `/crew` — clean solid scrolling lines only.

---

## 0.6.75 — Solid Crew hawsers

**Why:** Dashed rope strands read as dotted lines.

**What shipped:**
- Hawser strokes are solid (no dash pattern)

**How to try:** Hard-refresh `/crew` — solid scrolling ropes only.

---

## 0.6.74 — Crew hawsers + lantern sway

**Why:** Crew needed its own pirate motion — not a copy of Captain’s sea waves.

**What shipped:**
- Scrolling dual-strand rope/hawser bands (same scroll engine as Ship)
- Soft pennant-crimson lantern glow that sways above the berth

**How to try:** Hard-refresh `/crew` — ropes scroll at the bottom; lantern light rocks gently.

---

## 0.6.73 — Crew waves only, no grid

**Why:** Chart grid cluttered Crew; only the animated bands were wanted.

**What shipped:**
- Removed chart grid / rule lines from Crew atmosphere
- Kept the three scrolling wave bands + vignette

**How to try:** Hard-refresh `/crew` — animated waves only, no grid.

---

## 0.6.72 — Crew atmosphere actually visible

**Why:** Chart backdrop was nearly invisible (and easy to miss without a hard refresh).

**What shipped:**
- Stronger chart grid + lantern/kelp corner washes
- Three scrolling bands (fg / kelp dashed / lantern), thicker strokes, taller bottom band
- Lighter vignette so motion isn’t washed out

**How to try:** Hard-refresh `/crew` or Brand Brain — grid + scrolling chart bands should be obvious like Ship waves.

---

## 0.6.71 — Clear animated Crew bands

**Why:** Crew backdrop was too faint and barely moved vs Captain’s scrolling waves.

**What shipped:**
- Same dual scrolling bottom bands as Ship (16s / 24s), with chart rules + dashed course line
- Clearer grid field; vignette matched to Ship so the motion stays readable

**How to try:** Open `/crew` — chart grid + scrolling ops bands should read as clearly as Ship waves.

---

## 0.6.70 — Crew chart-room background

**Why:** Crew was sharing Ship sea waves; operators need a workspace feel.

**What shipped:**
- Crew layout backdrop: chart grid, kelp rigging lines, soft lantern wash (no ocean waves)
- Removed Ship waves from Brand Brain; both `/crew` and client berths use `CrewAtmosphere`

**How to try:** Open `/crew` or a client Brand Brain — chart/ops desk behind content, not rolling waves.

---

## 0.6.69 — Trail on Manifest; waves on Brand Brain

**Why:** Trail belonged only on Manifest; Brand Brain needed the deck waves.

**What shipped:**
- Grey slither only on Manifest (`/ship/posts`, queue); other Ship pages keep waves only
- Deck waves on Crew Brand Brain (`/crew/clients/…`); removed atmosphere from Crew Deck list
- `AhoyScrollProgress` takes `trail` / `waves` props; Ship uses `ShipAtmosphere`

**How to try:** Manifest → grey trail. Map/Vault/Radar → waves, no trail. Crew client Brand Brain → waves.

---

## 0.6.68 — Wider trail into gutters

**Why:** Soft narrow path sat under the center column and disappeared.

**What shipped:**
- Larger swing amplitude so the slither reaches the side gutters

**How to try:** Hard-refresh `/ship` — grey trail should show left/right of the cards.

---

## 0.6.67 — Softer trail curves

**Why:** Even with fewer loops, the L↔R turns still looked sharp.

**What shipped:**
- Longer swing spacing (560 → 780) and smaller amplitude
- Gentler cubic handles so arcs ease instead of whipping through S-bends

**How to try:** Hard-refresh `/ship` — grey trail should feel like long soft waves.

---

## 0.6.66 — Fewer trail loops

**Why:** Slither swung L↔R too often.

**What shipped:**
- Doubled vertical swing spacing (280 → 560) so the path loops about half as often

**How to try:** Hard-refresh `/ship` — grey trail should take longer arcs between sides.

---

## 0.6.65 — Drop red tip and X

**Why:** Red marks cluttered the trail; grey slither is enough.

**What shipped:**
- Removed lantern tip circle and end X
- Grey dotted path still draws on scroll

**How to try:** Hard-refresh `/ship` — only the grey trail remains.

---

## 0.6.64 — Red tip behind content

**Why:** Red tip (and X) sat above panels; grey path was already behind.

**What shipped:**
- Tip + X drawn in the same behind-content SVG as the grey slither
- Removed the elevated marks layer

**How to try:** Hard-refresh `/ship` and scroll — red tip should duck under cards like the grey trail.

---

## 0.6.63 — Tip actually reaches the X

**Why:** Red tip stopped short — end coords and path terminus disagreed; progress rarely hit 100%.

**What shipped:**
- Path ends with an exact `L` onto the X point; tip + X both use `getPointAtLength(len)`
- Near page bottom (or past end Y), progress snaps to full length so the tip lands on the X
- Remeasure after the SVG path commits (double rAF)

**How to try:** Hard-refresh `/ship` and scroll to the bottom — red tip should meet the X, then become it.

---

## 0.6.62 — X below content, not on a post

**Why:** End mark was anchored on the last Manifest post.

**What shipped:**
- X / path end sits under `main` (clear of cards)
- Removed last-post trail end markers on Manifest

**How to try:** Hard-refresh `/ship/posts` and scroll to the bottom — X should sit in the space under the list.

---

## 0.6.61 — Keep red tip until the real end

**Why:** Tip vanished mid-scroll — hidden too early and drawn under opaque cards.

**What shipped:**
- Tip stays until ~98.5% path / page bottom (then X)
- Tip + X rendered in a higher layer above panels; grey path stays behind

**How to try:** Hard-refresh `/ship` and scroll — red tip should stay visible the whole way, then become the X at the end.

---

## 0.6.60 — Trail from first container to reachable X

**Why:** Path didn’t start on the first content block, and the tip often never reached the X.

**What shipped:**
- Path starts at the first `[data-ahoy-trail]` / Ship header container
- Ends on the last marked container; scroll-to-bottom snaps tip to the end so the X appears
- ShipHeader marked as trail start; Manifest last post (or empty state) marked as end

**How to try:** Hard-refresh `/ship` — grey trail begins on Treasure Map header; scroll to bottom for the red X.

---

## 0.6.59 — Subtler grey trail

**Why:** Trail still felt loud.

**What shipped:**
- Lower grey opacity, thinner/sparser dashes
- Smaller softer tip + quieter end X

**How to try:** Hard-refresh `/ship` — atmosphere-level trail.

---

## 0.6.58 — Grey trail, red tip, end X

**Why:** Wanted simple palette — grey path, red traveler, X only at the finish.

**What shipped:**
- Grey dotted slither; lantern-red tip only
- Simple crimson X fades in near the path end; tip hides then
- Still continuous down the page, behind content

**How to try:** Hard-refresh `/ship` — grey dots + red tip; scroll to the bottom for the X.

---

## 0.6.57 — Trail behind content again

**Why:** Lantern slither was sitting on top of cards.

**What shipped:**
- Dropped trail `z-index` under `.relative.z-10` so panels/nav stay on top
- Kept bright lantern dots + continuous downward slither

**How to try:** Hard-refresh `/ship` — crimson trail reads in the gutters, not over the cards.

---

## 0.6.56 — Clear lantern slither (early look)

**Why:** Downward slither was right, but grey Pirate Ship stroke was too faint — wanted the early bright crimson dots + tip.

**What shipped:**
- Lantern crimson dots + soft glow (not grey)
- Larger bright tip on the lead
- Trail floats above panels again (`z-index: 12`) so it stays readable
- Same continuous downward page slither

**How to try:** Hard-refresh `/ship` and scroll — obvious pink/crimson dotted trail snake-ing down with a glowing tip.

---

## 0.6.55 — Continuous slither down the page

**Why:** Viewport loop/lap wasn’t the ask — wanted the dotted trail to keep snake-ing downward as you scroll.

**What shipped:**
- Document-space serpentine generated to page height (more L↔R swings on longer pages)
- Ink + tip advance continuously down with scroll — no lap reset, no wrap to top
- Tip tracks ~mid-viewport so the slither rides with you down the page
- Trail stays behind content

**How to try:** Hard-refresh `/ship` or `/ship/posts` and scroll — grey dotted path should keep slithering downward without jumping back to the start.

---

## 0.6.54 — Continuous looping trail (no reset)

**Why:** Lap reset wiped the line and restarted at the top; wanted seamless circuits.

**What shipped:**
- Closed serpentine so the route is a real loop (no teleport at the seam)
- Moving wake + tip that wraps across the join instead of clearing
- Same constant scroll→lap speed; longer pages still mean more continuous laps

**How to try:** Hard-refresh `/ship/posts` and keep scrolling — dotted wake should ride around the circuit without jumping back empty.

---

## 0.6.53 — Trail loops at constant scroll speed

**Why:** Mapping 0–1 to full page height made long pages (Manifest) crawl the path; wanted more laps, same speed.

**What shipped:**
- Path progress uses fixed ~1.15 viewports per lap (`scrollY / loopPx % 1`)
- Longer pages complete more circuits; short pages still finish at least one pass while scrolling
- Top progress bar still tracks true page progress

**How to try:** Hard-refresh `/ship/posts` and scroll — dotted route should redraw/loop at a steady pace, not crawl.

---

## 0.6.52 — Fix Manifest crush from page-tall trail

**Why:** Trail SVG sized to document height — Manifest (~100+ posts) ballooned to ~26k px and felt broken.

**What shipped:**
- Dotted line is fixed-viewport again (never matches document height)
- Sits behind content so cards/tabs stay readable and clickable
- Manifest only runs AhoyReveal on the first 12 posts (rest render plain)

**How to try:** Hard-refresh `/ship/posts` — page should scroll normally; trail stays a light viewport overlay.

---

## 0.6.51 — Faithful Pirate Ship dotted line

**Why:** Floating crimson wake ≠ pirateship.com/features. Match their real model.

**What shipped:**
- Page-locked SVG (absolute over `.ahoy-trail-root`, scrolls with content)
- Brand stroke: width 8, dash `10 30`, round caps, grey foam color
- Mask trim reveal with scroll (dots stay in place — no sliding dashoffset on the dots)
- z-index 15 so it hovers above panels like their wrapper
- Removed tip/wake/X gimmicks

**How to try:** Hard-refresh `/ship` at top (little/no line) → scroll — grey dotted path grows down the page over the cards.

---

## 0.6.50 — Hovering Pirate Ship–style dotted trail

**Why:** Element-connector trail sat under cards and was effectively invisible. Want a moving hovering trail like Pirate Ship.

**What shipped:**
- Fixed full-viewport dotted serpentine that floats *above* content (`z-index: 25`)
- Only a moving wake (~40% of the route) is visible — travels with scroll; tip rides the lead
- Thick bright lantern dots + glow; X near the finish
- Waves stay as lower atmosphere

**How to try:** Hard-refresh `/ship` — crimson dotted trail should be obvious and slide along the path as you scroll.

---

## 0.6.49 — Reveal-only trail connecting page elements

**Why:** Whole route was visible at once; wanted ink that appears as you scroll, linking real UI.

**What shipped:**
- No ghost full path — only the scroll-revealed segment is drawn
- Path anchors to `[data-ahoy-trail]` (header → stat cards → CTA on `/ship`)
- Soft curves in document space; waypoints light as the tip reaches them; X at the end
- Waves stay as fixed atmosphere

**How to try:** Hard-refresh `/ship` at the top (almost no trail) → scroll down — crimson line grows between Treasure Map, the four cards, and the Manifest CTA.

---

## 0.6.48 — Full-screen draw-on-scroll trail

**Why:** Document-locked path looked unchanged on short `/ship` pages — faint, barely moved.

**What shipped:**
- Path is fixed full-viewport again (covers the screen, not a page slice)
- Soft full-bleed serpentine; scroll progress inks dashes + moves tip
- Short lead visible at top so the trail is obvious from the first paint
- X near finish; waves stay as fixed atmosphere

**How to try:** Hard-refresh `/ship` and scroll — crimson dashes grow across the screen with scroll; tip rides the lead.

---

## 0.6.47 — Document-space trail (fix broken lock)

**Why:** Fixed SVG + `translateY(-scrollY)` desynced from real page height — path looked stuck/broken.

**What shipped:**
- Path is `absolute inset-0` inside the relative page shell (scrolls with content, Pirate Ship–style)
- Dropped height/translate hack; waves/vignette stay fixed atmosphere
- ResizeObserver keeps draw progress in sync as content loads
- Softer full-bleed route (no stacked edge U-turns that read as a corner streak)
- Slightly stronger ghost + lantern stroke

**How to try:** Hard-refresh `/ship` — path spans the full page area and scrolls away with the cards while dashes ink in.

---

## 0.6.46 — Full-page path locked to scroll

**Why:** Path sat in a corner of the viewport instead of riding the real page scroll.

**What shipped:**
- Path SVG height = document height; `translateY(-scrollY)` locks it to the page
- Broad full-width serpentine; thicker draw stroke
- Tip + end X still driven by scroll progress

**How to try:** Hard-refresh `/ship` — dashed line spans the page and draws as you scroll the content.

---

## 0.6.45 — Pirate Ship–style draw-on-scroll path

**Why:** Floating ribbon ≠ Pirate Ship. Want the dashed path to *draw* as you scroll.

**What shipped:**
- Broad serpentine path revealed via `stroke-dasharray` from scroll progress
- Tip traveler on the leading edge; X only near finish
- Removed viewport-sliding ribbon

**How to try:** Hard-refresh `/ship` — path grows downward with scroll; undoes on scroll up.

---

## 0.6.44 — Scroll-following ribbon

**Why:** Static map path felt wrong — the trail should ride with scroll.

**What shipped:**
- Removed fixed full-route spine
- Wide L→R dotted ribbon that moves down the viewport with scroll
- Trailing side fades; lead stays bright; dashes crawl with progress
- X still only near the finish

**How to try:** Hard-refresh `/ship` and scroll — the ribbon travels with you.

---

## 0.6.43 — Broader, thicker trail

**Why:** Path felt narrow; visible dots needed more weight.

**What shipped:**
- Wider left↔right serpentine (near full deck width)
- Thicker visible crimson dots (`strokeWidth` 3.25)
- Slightly wider trail SVG inset

**How to try:** Hard-refresh `/ship` — broader swings, heavier dotted stroke.

---

## 0.6.42 — X only at the finish

**Why:** Treasure mark should stay hidden until the Captain reaches the end.

**What shipped:**
- X fades in only after ~92% scroll progress

**How to try:** Hard-refresh `/ship` and scroll to the bottom — X appears at the trail end.

---

## 0.6.41 — Visible trail X

**Why:** End X was easy to miss (low, soft, under vignette).

**What shipped:**
- Path ends at fixed center mark `(600, 400)`
- Larger crimson X with deck halo
- Trail SVG above waves/vignette (`z-index: 2`)

**How to try:** Hard-refresh `/ship` — X should sit mid-screen at the trail end.

---

## 0.6.40 — Align traveler to start/end

**Why:** Progress inset left the scroll dot short of the path head and the X.

**What shipped:**
- Full 0→1 scroll mapping along the path
- Snap traveler to exact start/end points at the extremes

**How to try:** Hard-refresh `/ship` — top of page sits on the trail head; bottom sits on the X.

---

## 0.6.39 — Keep trail X in frame

**Why:** End X sat too low and clipped into the wave area.

**What shipped:**
- Shortened path; finish ~mid viewport
- Extra bottom inset on the trail SVG box

**How to try:** Hard-refresh `/ship` and scroll to the bottom — X stays on screen.

---

## 0.6.38 — Trail end X only

**Why:** Start port mark was unnecessary; keep the treasure X.

**What shipped:**
- Removed start circle
- Kept crimson **X** at trail end

**How to try:** Hard-refresh `/ship` — X at the finish only.

---

## 0.6.37 — Trail start + end marks

**Why:** Voyage needed a clear beginning and treasure end.

**What shipped:**
- Start: open port circle at path head
- End: crimson **X** at path tail
- Faint full dotted spine so the route reads start→end

**How to try:** Hard-refresh `/ship` — circle at the start, X at the finish.

---

## 0.6.36 — Trail stays in frame

**Why:** Marker/trail clipped under the nav at the start and into the waves at the end.

**What shipped:**
- Path inset inside a safe frame (clear of header + wave strip)
- SVG `meet` + padded layout box
- Scroll progress eased so start/end sit slightly on-path

**How to try:** Hard-refresh `/ship` — first and last scroll positions keep the trail visible.

---

## 0.6.35 — Softer, less clustered trail

**Why:** Turns felt pointy; dots/path reads were too bunched.

**What shipped:**
- Wide soft U-turns (serpentine L→R with roomy vertical gaps)
- Airier dash spacing (`2 22`)
- Shorter visible window so fewer dots on screen at once

**How to try:** Hard-refresh `/ship` — open curves, sparse crimson dots.

---

## 0.6.34 — Cleaner trail

**Why:** Trail overlay felt messy (too many strokes / zigzags).

**What shipped:**
- One soft S-curve path, single crimson dotted stroke
- Slimmer scroll window + tiny marker
- Two quieter wave layers (dropped the third)

**How to try:** Hard-refresh `/ship` — calmer dotted trail over soft waves.

---

## 0.6.33 — Single serpentine dotted trail

**Why:** Rows of lines were wrong — needed one continuous L→R trail that travels down.

**What shipped:**
- One serpentine dotted path (left→right legs, descending)
- Scroll window: trail behind clears, lead ahead pops
- Soft marker on the path; waves kept

**How to try:** Hard-refresh `/ship` and scroll — follow the single winding dotted trail.

---

## 0.6.32 — L→R bands that pop while traveling down

**Why:** Wanted left-to-right dotted lines that travel downward and pop as they enter.

**What shipped:**
- Stacked horizontal dotted bands (alternating L→R / R→L)
- Scroll focus moves top→bottom: trailing bands fade out, leading bands scale/pop in
- Crimson accent on the active band + soft pip
- Waves kept

**How to try:** Hard-refresh `/ship` and scroll — each L→R row pops as you reach it, then clears behind.

---

## 0.6.31 — Subtle vertical trail window

**Why:** Trail should run top→bottom; past dots vanish, ahead dots appear; overall quieter.

**What shipped:**
- Vertical dotted path (center, slight curve)
- Scroll-linked mask: trailing fade-out, leading fade-in
- Softer marker + quieter waves
- Side trails removed

**How to try:** Hard-refresh `/ship` and scroll — dots behind you clear; dots ahead open up.

---

## 0.6.30 — Dotted trail follows scroll

**Why:** Lines were sliding away; they should stay on screen and track the Captain.

**What shipped:**
- Dotted trails fixed to the viewport (no parallax fly-off)
- Crimson route draws with scroll progress
- Marker (X-dot) rides the path as you scroll
- Waves kept rolling at the keel

**How to try:** Hard-refresh `/ship` and scroll — the crimson spot moves along the trail with you.

---

## 0.6.29 — Waves + scroll dotted trails

**Why:** Wanted the sine waves back, with dotted trails that clearly move on scroll.

**What shipped:**
- Restored monochrome/crimson wave tracks at the keel
- Three visible dotted voyage paths (ink + crimson) with parallax + dash crawl
- Small crimson X; map grid/islands cartouche removed for clarity

**How to try:** Hard-refresh `/ship` and scroll — dotted lines slide; waves keep rolling.

---

## 0.6.28 — Map lines scroll with you

**Why:** Treasure map felt static; lines should slide as the Captain scrolls.

**What shipped:**
- Parallax layers: grid (fastest), route, islands, X/cartouche (slowest)
- Route dash offset tied to scroll position
- Extended grid so lines keep flowing without empty edges

**How to try:** Hard-refresh `/ship` and scroll — latitude/longitude lines drift under the deck.

---

## 0.6.27 — Treasure map overlay

**Why:** Wanted a treasure-map theme behind the deck, not sail/waves chrome.

**What shipped:**
- Full-bleed map overlay: grid, torn border, islands, palms, mountains
- Crimson dashed voyage route + pulsing **X**
- Small cartouche legend; ink grain; vignette keeps UI readable
- Removed wave tracks / sail / anchor

**How to try:** Hard-refresh `/ship` — chart sits behind Treasure Map content.

---

## 0.6.26 — Sail + anchor overlay marks

**Why:** Floating compass rose and glow ball felt wrong for the deck.

**What shipped:**
- Removed compass + lantern ball
- Soft sail/pennant (gentle sway) and faint anchor (soft bob)
- Chart latitude lines kept

**How to try:** Hard-refresh `/ship` — sail starboard, anchor port, over the waves.

---

## 0.6.25 — Monochrome wave colors

**Why:** Teal / crimson / indigo wave bands fought the B/W deck.

**What shipped:**
- Wave fills + most strokes use `ahoy-fg` at low opacity
- One pennant crimson crest as the accent line
- Vignette stays neutral (no kelp wash)

**How to try:** Hard-refresh `/ship` — waves should read ink/foam + one crimson line.

---

## 0.6.24 — Real sine waves, no clipping

**Why:** Overlay blobs didn’t read as waves; edges looked cut off.

**What shipped:**
- Proper cubic sine wave strokes + soft fills (3 layers)
- Seamless horizontal loop (`translateX(-50%)` on a 2× tile)
- Waves live in a bottom strip; chart rose kept clear of the crop

**How to try:** Hard-refresh `/ship` — continuous rolling sine lines at the keel.

---

## 0.6.23 — Stronger overlay motion

**Why:** Ambient overlay was too faint to notice.

**What shipped:**
- Higher tide/rose/glow opacity; wider wave travel
- Faster loops (~18–28s tides, 72s rose, 6–8s glow)
- Lighter vignette so the chart reads through

**How to try:** Hard-refresh `/ship` — sea bands and rose should be obvious behind content.

---

## 0.6.22 — Overlay ambient motion

**Why:** Background chart was still; wanted life in the overlay without crowding UI.

**What shipped:**
- Tide bands slowly drift (staggered, alternate)
- Compass rose turns over ~3 min
- Latitude lines + lantern glow soft breathe
- Still behind content; `prefers-reduced-motion` kills loops

**How to try:** Hard-refresh `/ship` and watch the background sea/chart, not the cards.

---

## 0.6.21 — Quieter pirate atmosphere

**Why:** Ship mark + rolling sea + yawing cards were too distracting vs. the work.

**What shipped:**
- Removed voyage ship and bottom wave strip
- Soft chart/sea **background overlay** + vignette (gentle parallax)
- Thin progress line only; reveals reduced to a soft lift
- Content stays above overlay (`z-10`)

**How to try:** Hard-refresh `/ship` — atmosphere sits behind the deck, not on it.

---

## 0.6.20 — Pirate scroll motions

**Why:** Plain fade-up felt generic; scroll should feel like sailing.

**What shipped:**
- Reveal variants: `sail` (port fill), `heave` (bilge sway), `drop` (anchor)
- Voyage rope + tiny ship mark tracking scroll at the top
- Rolling sea strip at the keel (translateX with scroll)
- Wired across Ship + Crew; still transform/opacity only

**How to try:** Hard-refresh `/ship` and scroll — ship rides the rope; cards yaw in.

---

## 0.6.19 — Scroll animations

**Why:** Website feel — content should rise into view as you sail down the page.

**What shipped:**
- `AhoyReveal` — IntersectionObserver fade/rise (transform + opacity only; once)
- Staggered cards/list rows on Ship Map, Manifest, Vault, Radar + Crew Deck
- `AhoyScrollProgress` — thin crimson scaleX bar at the top
- Honors `prefers-reduced-motion`

**How to try:** Hard-refresh `/ship`, scroll the Map cards / open Manifest.

---

## 0.6.18 — Fix dual-server nav break

**Why:** Two `next dev` instances (3000 + 3001) left JS/CSS out of sync — top links rendered as one glued string.

**What shipped:**
- Nav spacing/active underline via Tailwind on the component (no fragile custom class dependency)
- Wider gaps between Map / Manifest / Vault / Radar
- Kill duplicate servers; run a single web dev process

**How to try:** Use only `http://localhost:3000/ship` after one `npm run dev` in `apps/web`.

---

## 0.6.17 — Top nav polish

**Why:** First top-nav pass still felt like a relocated app bar (icon pills); layout also broke when CSS lagged HMR.

**What shipped:**
- Classic site header: logo · text links · theme (Tailwind for structure)
- Active = crimson underline, not filled pills; dropped per-link icons
- Solid sticky bar (no frosted wrap)

**How to try:** Hard-refresh `/ship` — single-row header with Map / Manifest / Vault / Radar.

---

## 0.6.16 — Top site navigation

**Why:** Bottom tab bar read as an app; this is a website — primary nav belongs at the top.

**What shipped:**
- Ship chrome: sticky top header (logo + horizontal links + theme toggle)
- Removed bottom-fixed nav and `pb-24` spacer
- Theme dock hidden on `/ship` (toggle lives in the header)

**How to try:** Open `/ship` — nav is along the top; hover links for lift.

---

## 0.6.15 — Bigger returns + hover motion

**Why:** Return paths were easy to miss; controls needed clearer hover feedback without GPU thrash.

**What shipped:**
- `AhoyBackLink` — 48px+ hit target, copper edge, arrow slides on hover
- Wired on Crew client detail, sign-in → Home, Logbook → Manifest
- Button/ghost/tab/logo hover via transform only; gated Sign-in CTAs use `ahoy-btn`
- `prefers-reduced-motion` kills hover transforms

**How to try:** Open a Crew client → big “Crew Deck” return; hover buttons on Ship.

---

## 0.6.14 — Faster first load

**Why:** Dual Google fonts + eager ROI breakdown made first paint feel slow.

**What shipped:**
- Single font (Atkinson only; display uses same face via size/weight)
- `display: swap` + font fallback adjust
- Route `loading.tsx` shells
- Treasure Map: ROI summary first; breakdown fetch only when opened

**How to try:** Hard-refresh `/ship` — Map should paint sooner; open revenue for breakdown.

---

## 0.6.13 — Align type system

**Why:** Mixed Tailwind `text-sm` / `font-semibold` / mono fought Fraunces + Atkinson scale.

**What shipped:**
- Roles only: `ahoy-brand`/`logo-word`, `title`, `title-sm`, `stat`, `prose`, `muted`, `label`, `strong`, `nav-label`
- Stripped stray size/weight utilities from Ship/Crew/auth; tables/inputs/tabs inherit scale

**How to try:** Hard-refresh — headings should share Fraunces sizes; body/UI share Atkinson.

---

## 0.6.12 — A-hoy logo

**Why:** Brand needed a real mark, not only loose pirate icons.

**What shipped:**
- SVG logo: sail-as-**A** + hull + pennant (`AhoyLogo` / `AhoyMark`)
- Wired on landing, sign-in, Ship nav; favicon `app/icon.svg`
- Raster mark also at `apps/web/public/ahoy-logo-mark.jpg` (generated asset)

**How to try:** `/` hero logo; favicon in the browser tab; nav mark on Ship.

---

## 0.6.11 — Type that pops + stays readable

**Why:** Need stronger hierarchy without losing body clarity.

**What shipped:**
- Display: Fraunces (brand + titles) with clamp() scale
- Body/UI: Atkinson Hyperlegible at 18px+; buttons bold 700
- Clearer size steps: brand / title / title-sm / body / kicker

**How to try:** Hard-refresh `/` — big soft display headlines, plain readable body.

---

## 0.6.10 — Atkinson Hyperlegible

**Why:** Source Sans still felt wrong; need maximum on-screen clarity.

**What shipped:**
- UI face → Atkinson Hyperlegible (400/700)
- Base size 18px; slightly roomier title/prose line-height

**How to try:** Hard-refresh. If you still hate it, say whether you want serif, rounded, or mono-ish next.

---

## 0.6.9 — Readable UI type

**Why:** EB Garamond (esp. italic brand/kickers) was hard to scan.

**What shipped:**
- Single face: Source Sans 3 for brand, titles, and body
- Dropped italic display; tighter sans titles / uppercase kickers

**How to try:** Hard-refresh — type should feel clearer everywhere.

---

## 0.6.8 — Pennant accent (drop orange)

**Why:** Lantern orange read as generic warm CTA; wanted a sharper pirate signal.

**What shipped:**
- Primary accent → pennant crimson (`--ahoy-lantern`)
- Secondary fittings → indigo (`--ahoy-copper`); links stay kelp/teal

**How to try:** Hard-refresh — buttons, top stripe, active nav/tabs should be crimson, not orange.

---

## 0.6.7 — Reviews theme surfaces

**Why:** Reputation Radar draft boxes used always-black `--ahoy-void` + hardcoded emerald/red, so Night/Day watch barely showed.

**What shipped:**
- Reviews use `ahoy-inset`, lantern stars, `ahoy-success` / `ahoy-error`
- Same message/inset fix on Manifest placeholders

**How to try:** Radar → toggle Day/Night — cards, draft reply, stars should flip with the deck.

---

## 0.6.6 — In-app Day / Night watch toggle

**Why:** Demo needs explicit light/dark without relying on OS settings alone.

**What shipped:**
- `data-theme` on `<html>` + `localStorage` (`ahoy-theme`)
- Boot script to prevent flash; `ThemeProvider` + **Day watch / Night watch** dock (all pages)
- CSS keyed off `html[data-theme="light"|"dark"]` (B/W deck, pirate accents)

**How to try:** Top-right **Night watch** / **Day watch** — persists across refresh.

---

## 0.6.5 — B/W deck + pirate chrome

**Why:** Wanted a simple black/white page (system light/dark) with pirate limited to accents, assets, and light motion.

**What shipped:**
- `prefers-color-scheme`: `#fff` / `#000` page + matching panels
- Pirate kept on: lantern CTAs, copper kickers/marks, kelp links, lantern top stripe, SVG marks
- One-shot rise + rule glow only (`prefers-reduced-motion` off)

**How to try:** Toggle OS light/dark → hard-refresh. Background flips B/W; accents stay pirate.

---

## 0.6.4 — Chart room daylight

**Why:** Privateer cabin was distinctive but too dark to live in.

**What shipped:**
- Light salt-stained parchment deck + sailcloth panels; ink text
- Kept lantern CTAs, copper fittings, kelp links, EB Garamond
- Nav: light sailcloth with mahogany active state

**How to try:** Hard-refresh `/` — bright chart paper, still warm privateer (not navy SaaS).

---

## 0.6.3 — Privateer cabin (less generic)

**Why:** Cool navy + brass read as stock “dark pirate SaaS.” Needed a warmer, chart-room identity that stays sloop-fast.

**What shipped:**
- Palette: tar deck, mahogany plank, bone text, lantern amber CTAs, copper fittings, kelp links, signal red
- Display font: EB Garamond (italic brand/kickers) instead of Cinzel
- Kickers copper italic (not uppercase tracking-heavy navy labels)

**How to try:** Hard-refresh `/` — warm brown hold, lantern buttons, bone type (not blue-black + gold).

---

## 0.6.2 — Night hull palette

**Why:** Light deck read as generic SaaS; needed a darker pirate hold without bringing back GPU-heavy effects.

**What shipped:**
- Palette: void/hull/deck/plank + foam text, bright brass CTAs, sea links ([apps/web/src/app/globals.css](../apps/web/src/app/globals.css))
- Brass waterline stripe; brass primary buttons; dark nav with brass active
- Replaced leftover light `slate-*` utilities on Ship/Crew surfaces

**How to try:** Hard-refresh `/` and `/ship` — should feel below-decks dark with brass fittings.

---

## 0.6.1 — Pirate SVG marks

**Why:** Theme needed recognizable pirate assets without image weight or GPU effects.

**What shipped:**
- Inline SVG set: wheel, compass, scroll, chest, spyglass, anchor, sloop, coins ([apps/web/src/components/pirate/Icons.tsx](../apps/web/src/components/pirate/Icons.tsx))
- Ship nav icons; page headers via `ShipHeader`; landing + sign-in marks
- Stroke/`currentColor` only — no raster, blur, or animation

**How to try:** `/` (sloop/wheel/anchor) → Ship bottom nav icons → Treasure Map / Manifest / Vault / Radar titles.

---

## 0.6.0 — Sloop theme (pirate + fast)

**Why:** Wanted a clearer pirate read without the galleon-weight CSS that slowed the machine.

**What shipped:**
- Sloop palette: hull ink, sea waterline, cool deck, sail panels, brass fittings — **solid fills only**
- Body: flat deck + 5px hull top stripe (no gradients/blur/keyframes)
- Panels: sail white + inset brass nail edge
- Primary buttons: hull ink; jib-sail CSS triangle on brand marks
- Nav: solid sail bar with hull active state
- Still 2 Google fonts / minimal weights

**How to try:** Hard-refresh `/` — should feel snappy; look for hull stripe, brass panel edge, jib on **A-hoy**.

---

## 0.5.2 — Theme perf (whole-PC load)

**Why:** Layered body gradients + motion still taxed GPU; three Google font families with many weights inflated Next/Turbopack work (~1GB `next dev`).

**What shipped:**
- Flat mist background only (no radial stacks, no keyframes)
- Dropped Source Code Pro; Cinzel/Source Sans limited to needed weights
- Rise animation classes are no-ops

**How to try:** Hard-refresh (Ctrl+Shift+R). If the machine is still hot, restart `npm run dev` in `apps/web` — the old Turbopack process was ~1GB RAM.

---

## 0.5.1 — Theme perf (kill scroll jank)

**Why:** Infinite body `background-position` animation + full-viewport chart grid + `backdrop-filter` on every panel forced constant paint and felt laggy.

**What shipped:**
- Removed `ahoy-swell` infinite animation and fixed chart-grid overlay
- Solid panels/nav (no backdrop blur); simpler button hover (no `filter`/`transform`)
- `prefers-reduced-motion` disables rise animations

**How to try:** Hard-refresh `/ship` — scroll and tab switches should feel normal again.

---

## 0.5.0 — Pirate / nautical UX theme

**Why:** Product metaphor (Ship, Crew, Treasure Map) was verbal only — UI still looked like generic SaaS slate/sky.

**What shipped:**
- Theme tokens: ink / sea / foam / brass; chart-grid + swell atmosphere ([apps/web/src/app/globals.css](../apps/web/src/app/globals.css))
- Fonts: Cinzel (display/brand) + Source Sans 3 (UI) + Source Code Pro
- Shared chrome: `.ahoy-brand`, `.ahoy-title`, `.ahoy-panel`, `.ahoy-btn`, `.ahoy-tab`, rise/swell motion
- Landing brand-first **A-hoy**; Ship nav Map / Manifest / Vault / Radar
- Copy/surfaces aligned across Ship, Crew, sign-in

**How to try:** Open `/` then Captain `/ship` and Crew `/crew` — sea mist background, engraved titles, brass rules.

**Related:** post-C polish (not Milestone D)

---

## 0.4.0 — Test matrix + A↔B↔C integration

**Why:** Run milestones in isolation and together; catch role/tenant regressions across A→B→C; keep CI honest.

**What shipped:**
- Pytest markers: `milestone_a`, `milestone_b`, `milestone_c`, `integration_ab`, `integration_abc` ([apps/api/pyproject.toml](../apps/api/pyproject.toml))
- Shared helpers + seeded IDs ([apps/api/tests/helpers.py](../apps/api/tests/helpers.py))
- New [apps/api/tests/test_integration_abc.py](../apps/api/tests/test_integration_abc.py) (ROI → generate/release → swap → approve-all → review reply + tenancy)
- Split Milestone C cases: swap vs approve-all; seeded low-star review id; Crew forbidden on swap
- CI runs each marker then full suite ([.github/workflows/ci.yml](../.github/workflows/ci.yml)); Ruff ignores for FastAPI `Depends`/`File`/`Form` defaults

**Tests:**
```powershell
cd apps/api
uv run pytest -m milestone_a
uv run pytest -m milestone_b
uv run pytest -m milestone_c
uv run pytest -m integration_ab
uv run pytest -m integration_abc
uv run pytest
uv run ruff check app tests
```

**Related:** [milestone_a.md](./milestone_a.md), [milestone_b.md](./milestone_b.md), [milestone_c.md](./milestone_c.md)

---

## 0.3.0 — Ship Posts + Queue merge

**Why:** Two Captain feeds (Queue vs Posts) were redundant; one actionable Posts screen.

**What shipped:**
- `/ship/posts` — tabs All / Awaiting you / Approved; Approve, Request edit, Swap media, Approve all on `pending_client` ([apps/web/src/app/ship/posts/page.tsx](../apps/web/src/app/ship/posts/page.tsx))
- Legacy `/ship/queue` → redirect `?tab=pending`
- Ship nav: Home, Posts, Media, Reviews (Queue link removed)
- Push/notify deep links → `/ship/posts?tab=pending`
- Mobile README path note

**How to try:** Captain `+15551234001` → `/ship/posts`. Open `/ship/queue` and confirm redirect.

**Related:** [milestone_c.md](./milestone_c.md) (C2 polish surface; merge is post-checklist UX)

---

## 0.2.0 — Crew UX polish (type, media upload, Posts tabs)

**Why:** Make Crew Deck readable and match the staged draft → release → approved mental model.

**What shipped:**
- Geist on body, larger base type, `.ahoy-prose` / `.ahoy-muted` on Crew + Ship surfaces
- Crew media: **Upload photo** + thumbnails (below Brand Brain)
- Crew **Posts** tabs: Drafts / Awaiting Captain / Approved (replaces mixed queue table)

**How to try:** Crew `+15551234002` → client page → Brand Brain → Media → Generate drafts → Posts tabs → Release.

**Related:** [milestone_b.md](./milestone_b.md)

---

## 0.1.0 — Approval refill path documented + test

**Why:** Captains need a clear path after approving empties the awaiting list.

**What shipped:**
- Docs for generate → release refill after approve
- `test_approve_leaves_queue_and_refill_via_generate_release` (`milestone_b`)

**How to try:** Approve all awaiting posts as Captain → Crew Generate + Release → posts reappear under Awaiting you.

**Related:** [milestone_b.md](./milestone_b.md)
