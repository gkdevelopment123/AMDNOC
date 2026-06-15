# DESIGN_SPEC.md — The "Billion-Dollar Product" UI Spec

> The dashboard is what judges SEE. It must look like a flagship enterprise product — a NOC command center from a top-tier vendor — not a hackathon demo. This file is the binding visual brief. Build the UI to **this**, not to Gradio defaults.

> **Not dark-themed.** Colorful, bright, premium, energetic. Think a modern observability product (Datadog / Grafana Cloud / Cisco ThousandEyes) but brighter and more confident, with a vivid accent palette on light surfaces.

---

## 1. Design thesis

A **live network operations command center** that turns chaos into calm in front of your eyes. The emotional arc the UI must deliver: **alarm storm = visceral red chaos → resolution = calm green order.** The interface itself should perform that transformation as the pipeline runs.

Audience: enterprise telco decision-makers + technical judges. The page's one job: make them believe this is production software they could deploy Monday.

---

## 2. Color system (light, vivid, premium — NOT dark)

Use these as the token palette. Light canvas, saturated functional accents.

```
--bg-canvas:    #F7F9FC   /* app background — soft cool white */
--bg-surface:   #FFFFFF   /* cards / panels */
--bg-elevated:  #FDFEFF   /* raised elements */
--ink:          #0F1B2D   /* primary text — deep navy, not black */
--ink-soft:     #5B6B82   /* secondary text */
--hairline:     #E6ECF4   /* borders / dividers */

/* Brand gradient — the signature */
--brand-1:      #4F6BFF   /* electric indigo */
--brand-2:      #7A5CFF   /* violet */
--brand-3:      #00C2FF   /* cyan */
--brand-grad:   linear-gradient(120deg,#4F6BFF,#7A5CFF,#00C2FF)

/* Functional status colors (vivid) */
--critical:     #FF3B6B   /* CRITICAL alarms — hot pink-red */
--major:        #FF8A3D   /* MAJOR — amber-orange */
--minor:        #FFC23D   /* MINOR — gold */
--healthy:      #18C98D   /* resolved / healthy — emerald */
--info:         #00C2FF   /* informational — cyan */
```

Rule: **the canvas stays light.** Color comes from data and status, not from a dark background. Panels are white with soft colored shadows. The "storm → calm" arc is shown by the panel/graph shifting from red-dominant to green-dominant.

---

## 3. Typography

Two-face pairing, loaded from Google Fonts (allowed; or bundle locally):
- **Display / headings:** `Space Grotesk` (700/600) — modern, technical, confident.
- **Body / UI:** `Inter` (400/500/600) — clean enterprise workhorse.
- **Data / metrics / logs:** `JetBrains Mono` — for alarm IDs, timers, counts, the audit log.

Type scale: hero metric 48–56px, panel titles 18–20px semibold, body 14–15px, captions/labels 12px uppercase tracked. Numbers (alarm counts, SLA timer) are the visual stars — set them big in the mono face.

---

## 4. Layout — command-center grid

```
┌───────────────────────────────────────────────────────────────────────┐
│  TOP BAR: ◆ NOC Copilot logo · live clock · "● System Operational"      │
│           gradient underline · [ ⚡ Simulate Outage ] primary button     │
├───────────────┬───────────────────────────────────┬───────────────────┤
│  LEFT 30%     │   CENTER 45%                       │  RIGHT 25%        │
│               │                                   │                   │
│ ALARM FEED    │   INCIDENT CORRELATION GRAPH       │  AGENT PIPELINE   │
│ live stream,  │   (NetworkX) — 40 nodes collapse  │  vertical stepper:│
│ color-coded   │   into 1 glowing incident node    │  Ingest→Correlate │
│ severity pills│                                   │  →RCA→Remediate   │
│ counter:      │   below: ROOT CAUSE card          │  each lights up   │
│ "42 active"   │   confidence ring (animated)      │  as it runs       │
│               │                                   │                   │
│               ├───────────────────────────────────┤  SLA TIMER        │
│               │   REMEDIATION + ACTIONS           │  big countdown,   │
│               │   step list, risk badges,         │  green if beaten  │
│               │   [Approve] gate for high-risk    │                   │
│               │   live action results             │  ITSM TICKET card │
│               │                                   │  ticket id, status│
└───────────────┴───────────────────────────────────┴───────────────────┘
   FOOTER: "🔒 100% on-prem · AMD Instinct MI300X · Qwen3-32B · 0 external calls"
```

Everything updates **live** as the pipeline runs — judges watch panels populate in sequence.

---

## 5. The signature element (the one memorable thing)

**The correlation collapse animation.** When "Simulate Outage" is clicked:
1. The alarm feed floods — 40+ severity pills cascade in fast, the counter spins up, the center graph explodes into a messy red constellation of 40 nodes.
2. Then the Correlation agent runs and the 40 nodes **visibly pull together** into ONE pulsing incident node, edges retracting, red calming toward amber.
3. As RCA + remediation resolve, the incident node turns **emerald green** and the SLA timer locks green.

That 8-second chaos→calm transformation is the demo's "aww" moment. Spend the animation budget here; keep everything else calm and precise.

---

## 6. Component styling rules

- **Cards:** white, 16px radius, soft *colored* shadow (e.g. `0 12px 32px rgba(79,107,255,.12)`), 1px `--hairline` border. Generous padding (20–24px).
- **Severity pills:** rounded, filled with the status color, white text, the alarm count badge in mono.
- **Confidence ring:** circular progress (SVG), brand gradient stroke, the % in the center in Space Grotesk.
- **Agent stepper:** each agent a row with an icon; idle = grey, running = brand gradient with a subtle pulse, done = emerald check. This visually proves "multi-agent."
- **Buttons:** primary = brand gradient, white text, soft glow on hover; "Approve" = emerald; "Simulate Outage" = the hero, slightly larger with a lightning icon.
- **Approval gate:** when high-risk, a card slides in with an amber left-border, the proposed action, and [Approve] / [Skip]. Makes the safety story visible.
- **Motion:** smooth 200–300ms eases; the one orchestrated moment is the collapse animation. Respect `prefers-reduced-motion`.

---

## 7. How to achieve this in Gradio (important)

Default Gradio looks like a demo. To hit billion-dollar quality:
- Use `gr.Blocks(theme=..., css=CUSTOM_CSS)` with a **large custom CSS block** implementing the tokens above. Override Gradio's defaults aggressively.
- Set a Google Fonts import at the top of the CSS.
- Use `gr.HTML()` components to render custom panels (alarm feed, agent stepper, confidence ring, SLA timer) as styled HTML/SVG you control — don't rely on stock Gradio widgets for the hero visuals.
- Render the correlation graph with NetworkX + matplotlib (styled, light bg) OR better: a `gr.HTML` block with inline SVG/vis-network for the animated collapse.
- Keep `share=False`.
- Target a wide layout; use `gr.Row()` / `gr.Column(scale=...)` for the 30/45/25 grid.

> If Gradio fights the premium look (it can), the fallback in RULES_AND_GIT.md §"UI polish escalation" applies: export the UI files and have them perfected externally, then paste back.

---

## 8. Copy / tone (no filler)

- Top bar status: "● System Operational" → during storm: "● 42 Active Alarms" (red) → resolved: "● Incident Resolved" (green).
- Buttons say what they do: "Simulate Outage", "Approve Router Reset", "View Audit Log".
- Root cause card leads with the cause in plain language, confidence as a number.
- Footer is the proof line: on-prem, AMD, zero external calls. Always visible.

---

## 9. Quality floor (non-negotiable)
- Looks intentional at 1920px (judges' projector) AND on a laptop.
- No default-Gradio grey-on-grey anywhere visible.
- Every number that matters (alarm count, confidence, SLA) is big and mono.
- The chaos→calm arc is unmistakable even from across a room.
