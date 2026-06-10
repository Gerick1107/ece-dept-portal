# Cursor Prompt — SDG Review Flow Overhaul

Read all existing SDG-related files thoroughly before making any changes. This is a refinement of an existing working implementation — do not rebuild from scratch, only modify what is explicitly described below.

---

## Current State (do not break these)
- Embeddings-based SDG generation is working — do not touch the generation logic
- All 17 SDGs are generated with confidence scores per project
- Review SDGs tab shows all 17 with checkboxes, 50%+ pre-ticked — this display is working
- The threshold is ≥50% (inclusive of exactly 50%)

---

## Change 1: SDG Column in Projects Table — Show Only ≥50% SDGs

### Current behaviour
The SDG column next to each project in the table shows all 17 SDGs with confidence rates.

### Required behaviour
- Show **only SDGs with confidence ≥ 50%** in the project table's SDG column.
- If no SDGs are ≥50%, show a muted label: `No SDGs assigned` (styled lightly, e.g. grey italic).
- If SDGs have been saved/accepted (i.e. a confirmed selection exists), show the **saved selection** instead of the auto-threshold ones.

### Formatting (within the table cell itself)
Each SDG on its own line, formatted as:
```
SDG 4 (71%)
SDG 7 (63%)
SDG 11 (55%)
```
- One SDG per line — no comma-separated inline lists, no wrapping blobs of text
- Format: `SDG {number} ({confidence}%)` — exactly this, no extra labels or icons in the table cell
- If the cell would overflow (many SDGs), show the first 3 and a `+N more` link that expands or opens the Review SDGs panel
- Confidence rates must always be visible — not in tooltips, not hidden behind hover

---

## Change 2: Review SDGs Panel — Full Flow

Read the existing Review SDGs panel/modal code before editing. Preserve all working display logic. Only change the action buttons and their behaviour as described below.

### Display (keep as-is)
- Show all 17 SDGs with confidence scores ✓
- ≥50% ones pre-ticked ✓
- Faculty can tick/untick any SDG freely ✓
- Formatting already done ✓

### Action Buttons — Replace existing button logic entirely

Remove whatever buttons currently exist and replace with exactly these three:

---

#### Button 1: Accept
- Saves the currently ticked SDGs (whatever is checked at time of click — could be the auto-selected ≥50% set, or a manually modified selection).
- These become the **confirmed saved SDGs** for this project.
- After saving, the SDG column in the table updates to show the saved set with confidence rates.
- The Regenerate button becomes hidden for this project (SDGs are now confirmed).
- Show a success toast/notification: *"SDGs saved successfully."*

#### Button 2: Reject
- Dismisses all SDGs for this project — saves an empty SDG list.
- The SDG column in the table shows `No SDGs assigned`.
- **The Regenerate button becomes visible** for this project.
- Show a confirmation prompt before rejecting: *"Are you sure you want to reject all SDGs for this project? This will clear all assigned SDGs."* with Confirm / Cancel.
- After confirmation, show toast: *"SDGs rejected. You can regenerate them if needed."*

#### Button 3: Save Selection
- Saves exactly the currently ticked SDGs (same as Accept in terms of data saved).
- Distinct from Accept only in label — use this if you want to preserve a semantic difference between "accept the auto selection" and "save a custom selection". If the existing codebase treats these identically, merge into one **Save** button and remove the distinction.
- After saving, same behaviour as Accept above.

---

## Change 3: Confidence Rates Must Persist After Save/Accept

### Requirement
Once SDGs are saved or accepted, wherever they are displayed — project table SDG column, project detail page, faculty directory, any other view — they must show the confidence rate alongside the SDG label.

### Implementation
- The confidence score must be stored in the SDG-project mapping record at save time, not just at generation time.
- Check the existing SDG-project mapping table: if it does not have a `confidence` column, add one via a proper migration:
  ```sql
  ALTER TABLE project_sdg_mappings ADD COLUMN confidence FLOAT;
  ```
- When saving SDGs (Accept or Save Selection), write the confidence value for each SDG into this column.
- When displaying saved SDGs anywhere in the frontend, read from `confidence` in the mapping record — do not re-derive from the generation output.
- If a saved SDG has no confidence value (legacy data), display without percentage: `SDG 4` — do not show `SDG 4 (null%)` or `SDG 4 (0%)`.

---

## Change 4: Regenerate Button — Conditional Visibility

### Current behaviour
Regenerate button is always visible for every project.

### Required behaviour
Show the Regenerate button **only when**:
1. The project has **zero confirmed SDGs** (never been accepted/saved), OR
2. The faculty clicked **Reject** (which sets SDG list to empty)

Hide the Regenerate button when:
- SDGs have been accepted or saved (confirmed selection exists, even if only 1 SDG)

### Implementation
- Add a `sdg_status` field to the project record (or a derived state from the mapping table):
  - `"pending"` — generation done, not yet reviewed (show Regenerate hidden, show Review SDGs)
  - `"confirmed"` — accepted or saved (hide Regenerate)
  - `"rejected"` — explicitly rejected (show Regenerate)
  - `"none"` — never generated (show Regenerate)
- Drive the Regenerate button visibility from this status field.
- Regenerate resets status to `"pending"` and re-runs the embedding-based generation — do not change the generation logic itself, just trigger it again for this project.
- After regeneration, the ≥50% threshold logic applies fresh, same as original generation.

---

## Summary of State Machine

```
[No SDGs generated]
       │
       ▼
  [Regenerate]
       │
       ▼
[Generated — pending review]  ← Regenerate also lands here
  SDG column: shows ≥50% auto set
  Regenerate button: HIDDEN (already generated, pending review)
       │
       ├──[Review SDGs → Accept / Save Selection]──▶ [Confirmed]
       │                                              SDG column: saved set + confidence rates
       │                                              Regenerate: HIDDEN
       │
       └──[Review SDGs → Reject]──────────────────▶ [Rejected]
                                                      SDG column: "No SDGs assigned"
                                                      Regenerate: VISIBLE
                                                             │
                                                             ▼
                                                      [Generated — pending review]
```

---

## General Reminders
- Do not touch the embedding generation logic.
- Do not change the Review SDGs panel display (all 17 shown, formatting already done).
- The ≥50% threshold is inclusive — `confidence >= 0.50` (or `>= 50` depending on how scores are stored — check the existing data type and be consistent).
- Run any schema changes as proper migration files.
- Test all four states: no SDGs, pending, confirmed, rejected — ensure the SDG column and Regenerate button reflect the correct state in each case.
- Handle the case where a project was created before this change (legacy projects with no `sdg_status`) — treat as `"pending"` if generation data exists, `"none"` if it does not.
