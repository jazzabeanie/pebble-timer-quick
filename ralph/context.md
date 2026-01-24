# Context File - Ralph Wiggum Loop

## Instructions for AI Agents
This file provides critical context about the codebase without requiring you to read everything. 

**USAGE RULES:**
- READ this file before starting work on any spec
- APPEND to the Recent Changes section with new entries (add at the top of that section, most recent first)
- Do NOT modify or delete existing Recent Changes entries - only append new ones
- UPDATE other sections (Key Components, Important Decisions, Known Issues, Future Considerations) as needed
- INCLUDE dates with your entries (YYYY-MM-DD format)
- BE CONCISE but include enough detail for future agents to understand decisions
- This file can be MANUALLY CLEARED at major project milestones when details are no longer relevant (human decision only)

**WHAT TO DOCUMENT:**
- Important architectural decisions and why they were made
- Key patterns or conventions established
- Gotchas, pitfalls, or non-obvious behavior
- Summaries of complex components
- Any context that would save future agents from re-discovering information

---

## Recent Changes
*Log recent changes with dates and brief descriptions. Most recent at top.*

<!-- Example:
- 2026-01-23: Initial project setup with ralph loop structure
-->

---

## Key Components
*Summaries of key components or modules, explaining their purpose and how they fit together.*

<!-- Example:
### Authentication Module
Located in `src/auth/`. Handles user authentication using JWT tokens. Integrates with the database layer through the User repository pattern.
-->

---

## Important Decisions
*Document architectural or design decisions with reasoning.*

<!-- Example:
### 2026-01-23: Chose Repository Pattern for Data Access
Decided to use the repository pattern to abstract database operations. This allows us to swap database implementations without changing business logic. All repositories implement interfaces defined in `src/interfaces/`.
-->

---

## Known Issues
*Technical debt and issues that need future attention but aren't blocking current work.*

<!-- Example:
- Password reset flow needs to implement rate limiting to prevent abuse
- Error messages in the API could be more descriptive for debugging
-->

---

## Future Considerations
*Ideas for enhancements or improvements identified during development.*

<!-- Example:
- Consider implementing caching layer for frequently accessed user data
- Could benefit from adding webhooks for real-time notifications
- API versioning strategy should be established before adding breaking changes
-->

---

