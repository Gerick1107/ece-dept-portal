# Cursor Fix Prompt — Colour Coding & SDG Acceptance Bug

---

## Fix 1: Colour Coding — Range-Proportional Blue → Red Scale

### Problem
The current implementation assigns colours by absolute position in a fixed gradient (e.g., always treating index 0 as dark blue and the last item as red regardless of total count). This causes:
- With 2 items: dark blue + light blue (no red end reached)
- With 5 items: CO5 only reaches yellow, never red
- Yellow shade is too light — blends into white background, unreadable

### What to do

The colour scale must be **range-proportional**: always span the full blue→red spectrum regardless of how many items there are.

**Core rule:**
- 1 item → single midpoint colour (e.g. purple or neutral)
- 2 items → blue and red (the two extremes only)
- 3 items → blue, a distinct middle (e.g. saturated orange-yellow), red
- 4 items → blue, light-blue/teal, orange, red
- 5 items → blue, light-blue, middle yellow-orange, orange, red
- N items → evenly interpolate across the full spectrum, always anchored at blue (index 0) and red (index N-1)

**Implementation:**
Use a fixed set of hand-picked distinct, high-contrast colours rather than a CSS/D3 linear interpolation (which produces the unreadable light yellow). Define a palette array that:
1. Always starts at blue and ends at red
2. Picks evenly spaced entries from the array based on how many items need colouring
3. Every colour in the array must be visually distinct from its neighbours and readable on both white and light grey backgrounds

**Suggested palette array (from blue to red, all high-contrast, perceptually distinct):**
```
[
  "#1a6fba",   // 0 - strong blue
  "#3a9bd5",   // 1 - medium blue
  "#56b8a6",   // 2 - teal
  "#74c476",   // 3 - green
  "#d4a017",   // 4 - dark golden yellow (NOT light yellow — must be readable)
  "#f07d00",   // 5 - orange
  "#e04020",   // 6 - orange-red
  "#c0001a",   // 7 - strong red
]
```

**Selection algorithm:**
```javascript
function getColours(n, palette) {
  if (n === 1) return [palette[Math.floor(palette.length / 2)]];
  return Array.from({ length: n }, (_, i) =>
    palette[Math.round(i * (palette.length - 1) / (n - 1))]
  );
}
// e.g. n=2 → [palette[0], palette[7]] → blue, red
// e.g. n=3 → [palette[0], palette[3 or 4], palette[7]] → blue, dark-yellow, red
// e.g. n=5 → [palette[0], palette[2], palette[3], palette[5], palette[7]]
```

**Important constraints:**
- No two adjacent colours should look similar — test visually with 2, 3, 4, 5, 6, 7, 8 items
- The yellow/mid tone must use a **dark saturated yellow** (like `#d4a017` or similar goldenrod) — never a pastel or near-white yellow
- Apply this logic consistently to all charts in the Analytics tab: bar charts, heatmaps, line charts, colour-coded table cells — anywhere the blue→red scale was previously applied
- This is a utility function — centralise it in one place (e.g. `utils/chartColours.js` or equivalent) and import it everywhere rather than duplicating per chart

---

## Fix 2: SDG — Accept Button Saves All 17 Instead of Only 50%+ Ones

### Problem
The Review SDGs flow works correctly in display:
- All 17 SDGs are shown with percentages ✓
- Only SDGs ≥ 50% are pre-selected/checked ✓

But when the user clicks **Accept**, all 17 SDGs get saved regardless of which ones were checked. The acceptance logic is not reading the checkbox/selection state — it is likely submitting the full original list.

### What to do

**Backend / submission handler:**
- Find the function/handler triggered by the Accept button in the Review SDGs flow.
- It is likely passing the full list of 17 SDGs (or the original top-5 list) instead of reading the current UI selection state.
- Fix it to collect only the SDGs that are currently **checked/selected** in the UI at the time Accept is clicked, and submit only those.

**Frontend checkbox state:**
- Ensure the initial checked state is correctly set: checked = true only for SDGs with confidence ≥ 50%, false for the rest.
- Ensure the checkbox state is mutable — the user can check/uncheck any SDG before accepting.
- On Accept, read the live checkbox state and send only checked SDGs to the backend.

**Do not change:**
- The display of all 17 SDGs with their percentages (this is working correctly)
- The pre-selection logic (≥50% auto-selected is correct)
- Any other part of the SDG flow

---

## Fix 3: SDG UI Formatting — One SDG Per Line with Percentage

### Problem
The SDG list in the Review SDGs tab is not cleanly formatted — SDGs and their confidence percentages are not presented in a readable, compact per-line layout.

### What to do
Format each SDG as a single row/line in this structure:

```
[ checkbox ]  🟡 SDG 7: Affordable and Clean Energy          63%
[ checkbox ]  🔵 SDG 4: Quality Education                    71%
[ checkbox ]  ⚪ SDG 11: Sustainable Cities and Communities  38%
```

**Requirements:**
- Each SDG on its own line — no wrapping or stacking of elements
- Show: checkbox | SDG number + name | confidence percentage right-aligned (or clearly separated)
- SDGs ≥ 50% (auto-selected): visually distinct — e.g. slightly highlighted row, bold text, or a coloured left border
- SDGs < 50% (not selected): slightly muted (e.g. lighter text), still visible and checkable
- Percentage must always be visible on the same line — do not hide it or put it in a tooltip
- Keep it compact — the full list of 17 should be scannable without excessive scrolling
- Use a clean monospaced-style alignment or flex row with space-between so percentages line up on the right edge

**Example row structure (HTML/JSX):**
```jsx
<div className="sdg-row" data-selected={confidence >= 50}>
  <input type="checkbox" checked={isChecked} onChange={...} />
  <span className="sdg-label">SDG {number}: {name}</span>
  <span className="sdg-confidence">{confidence}%</span>
</div>
```

With CSS:
```css
.sdg-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 4px;
}
.sdg-label { flex: 1; }
.sdg-confidence { min-width: 42px; text-align: right; font-weight: 600; }
.sdg-row[data-selected="true"] { background: #f0f7ff; border-left: 3px solid #1a6fba; }
.sdg-row[data-selected="false"] { opacity: 0.6; }
```

---

## General Reminders
- Read the existing file before editing — do not rewrite working logic
- The SDG display (all 17 + percentages) is already working — only fix the Accept submission and the formatting
- The colour utility function should be one centralised export, not copy-pasted per chart
