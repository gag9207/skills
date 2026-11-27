---
name: live-meeting-minutes
description: >-
  Use this skill when the user wants to write live, interactive HTML meeting
  minutes while conversing in real time, organizing notes by context, adding
  tables, distinguishing facts/questions/opinions with color-coded modal
  footnotes, and delegating source research to background subagents.
---

# Live Interactive HTML Meeting Minutes

Guide for capturing real-time meeting notes with the user into a structured,
tabbed HTML document while delegating source verification to background
subagents.

## Core Principles

1. **Role Separation (No File Conflicts)**
   - **Main Agent**: Stays responsive to the user, structures incoming notes,
     and owns all edits to the HTML file.
   - **Subagents** (`invoke_subagent`, `TypeName: "self"`, `Model: "flash"`):
     Research sources via `search_web` in the background and report back with
     source titles, verified URLs, and 2–3 sentence Korean summaries. Subagents
     must **never** edit the HTML file directly.
2. **Synthesize, Do Not List**
   - Never dump user inputs as a raw chronological list. Group related points
     under thematic headings (`.topic-group`), fix obvious typos naturally,
     convert comparisons into clean HTML tables (`.compare-table`), and
     sub-categorize long action lists.
   - If the user states an item is internal/private ("내부자료니까 찾지 마"),
     record it directly without launching a research subagent.

## HTML Document Structure

Create `회의록_YYYY-MM-DD.html` in the workspace root with:

- **Header**: Title, date, location (omit or adjust fields as requested), and
  per-session presenter/organization metadata when provided.
- **Session Tabs**:
  - Top `.session-tabs` navigation bar with `.session-tab` buttons targeting
    `#session-1`, `#session-2`, etc.
  - Only the active `.session` is displayed on screen; `@media print` displays
    all `.session` sections and `.footnotes`.
- **Color-Coded Footnotes & Modal Popup**:
  - **Blue `[1]`, `[2]`, ...**: External evidence/sources researched by
    subagents.
  - **Orange `[?]` (`.fn-question`)**: User questions raised during the meeting,
    updated with subagent research answers when available.
  - **Green `[!]` (`.fn-opinion`)**: User opinions or takeaways.
  - Keep `<section class="footnotes">` hidden on screen (`display: none`) so the
    page stays compact; clicking any `sup.fn-ref a` opens a centered modal
    (`.fn-modal-backdrop`) showing a color-matched badge, title, summary, and
    clickable source links (dismissible via `✕`, backdrop click, or `Escape`).

## Workflow

1. **Initialize**: When the user starts taking meeting notes for HTML viewing,
   copy [meeting-template.html](./resources/meeting-template.html) to
   `회의록_YYYY-MM-DD.html` in the workspace root and fill in the placeholders
   (`{{MEETING_TITLE}}`, `{{DATE}}`, `{{LOCATION}}`, `{{SESSION_1_TITLE}}`,
   `{{UPDATED_AT}}`). See [sample-meeting.html](./examples/sample-meeting.html)
   for a complete reference output with tables, tabs, and modal footnotes.
2. **Update Live**: For each user message:
   - Integrate the content into the appropriate thematic group (or table) of the
     active session and update the footer timestamp.
   - Tag questions with `[?]` and opinions with `[!]`.
   - For factual claims, statistics, or incidents needing citations (unless
     marked internal), immediately launch a background `self` subagent (`flash`)
     to find primary sources, URLs, and Korean summaries.
3. **Attach Footnotes**: When a subagent reports back, add the `<sup class="fn-ref">`
   link in the body and the corresponding `<li id="fn-...">` entry inside
   `.footnotes`. If a subagent stalls (e.g., `waiting_for_dependents`), use
   `send_message` to instruct it to return its already-gathered URLs and
   summaries immediately.
4. **Add Sessions**: When the user moves to a new session, add a new `.session-tab`
   button, set it active, and create `<section class="session active" id="session-N">`.
