# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
[Step] → verify: [check]

[Step] → verify: [check]

[Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Error Capture & Logging

**Handled errors should also be reported to Sentry, not just logged. New code should log its significant actions.**

- When an exception is caught, call `sentry_sdk.capture_exception(e)` in addition to any existing logging.
- When an error condition is detected without a raised exception (e.g. invalid input, failed validation), call `sentry_sdk.capture_message(...)` with an appropriate level.
- Don't add Sentry calls for expected/routine control flow (e.g. normal 404s from user-facing lookups) unless the error indicates a real problem worth investigating.
- When writing new code, add logging (e.g. `logger.info`/`warning`/`error`) for significant actions and error conditions, not just the happy-path return value.

## 6. Python Style Guide

**Strict typing and modern Python conventions.**

- **Type Hinting:** Explicit PEP 484 type hints are strictly required for all Python code.
- **Functions & Methods:** Every single function and method must include explicit parameter types and a return type annotation.
- **Modern Syntax:** Use modern Python 3.10+ typing features. Use standard collections like `list[int]` (not `typing.List`) and union types like `str | None` (not `Optional[str]`).
- **Specificity:** Avoid using `Any` wherever possible. Be precise with generic collections, `Mapping`, `Sequence`, and custom classes.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, zero untyped Python code blocks, and clarifying questions come before implementation rather than after mistakes.
