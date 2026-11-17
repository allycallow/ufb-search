# Concepts Brief: Improve top-results search

**Author:** Alex Callow
**Date:** 2026-11-16
**Mode:** Brainstorm
**Status:** Decisions in this brief were settled and built. See [top-results-search-relevance-design.md](top-results-search-relevance-design.md) for what shipped and what is still open.
**Reviewer status:** all seven lenses completed (design, codebase-details, zoom-out, comprehension, implementation-readiness, structural, inventive-catalyst). None are `not run`.

## Overview

Searching "Hot Creations" in full returns the label first, then "Hot Since 82" and "Hot Natured". The user expects the label, then the label's releases. Today unrelated records appear because any document containing "hot" matches.

Cause, checked in `app/routers/queries/fetch_top_results.py`:

- Line 15 builds a `query_string` of `*Hot Creations*` with no `default_operator`, so it is OR. That is two terms, `*Hot` and `Creations*`, and any doc with "hot" matches. It also searches all fields and uses a leading wildcard, whose cost grows with index size.
- The `should` boosts (phrase, term, type, popularity) use `minimum_should_match: 1`. The `range popularity gte 0` clause matches every doc that has a popularity value, so these clauses only rerank. They never filter.
- `fetch_labels_results.py`, `fetch_artist_results.py`, `fetch_releases_results.py` and `fetch_tracks_results.py` use the same `*{query}*` pattern. `fetch_playlist_results.py` uses it too, but limits it to the `name` field.

Proposed behaviour:

1. Every typed word must match. Earlier words match whole; the last word matches as a prefix (input is debounced type-ahead). Non-matching docs are removed.
2. If the top match is a label, return the label, then its releases. If it is an artist, return the artist, then its releases and tracks. Children are ordered by popularity ("trending" equals popularity in v1).
3. The result size stays 8.

Part 1 is a query change. Part 2 needs data that this repo does not define (see Analysis).

## Analysis

### Verified facts

- No code in this repo indexes documents. Docs arrive from an external backend (outbox payload). The mapping in `app/utils/index_mappings.py` defines only `popularity` (integer) plus playlist fields. `name`, `type` and `is_visible` are dynamically mapped. `name.keyword` is used in the query but never mapped explicitly.
- No link field appears anywhere in `app/`, and seed data has no release or track docs. The producer is the Django backend (`~/Sites/ufb/backend/upfrontbeats/models/release.py` and `track.py`, `release_to_dict` and `track_to_dict`). Its payloads carry `label: {id, name}` (null-able on tracks) and `artists: [{id, name}]` ordered by position. Tracks also carry `remixers`, `release: {id, title}`, `popularity` and `playCount`. Releases have no `popularity`.
- The backend payload uses `title` for tracks and releases, but this repo queries `name` and `type`. Something between Kafka and OpenSearch must rename `title` to `name` and add `type`. That transform was not found in `ufb-kafka-connect` (Dockerfile and JMX only) and is probably in connector config elsewhere. It is not confirmed that `label` and `artists` reach the index unchanged.
- The link fields are dynamically mapped today, so `label.id` is likely `text` with a `.keyword` subfield. A `term` lookup needs `label.id.keyword` or an explicit `keyword` mapping.
- No analyzers, normalizers, aliases or reindex path exist. Index settings and mappings are applied in three places (`app/routers/search.py:158`, `app/grpc/server.py:88`, `app/seed.py:60`) with no shared constant.
- `fetch_suggestions_results.py` already uses `match_phrase_prefix` on `name`. It is the closest existing pattern, but it requires words to be adjacent and in order, which is stricter than "all words must match".
- Response shape: REST returns `results.top` and five per-type lists as raw `_source` dicts. gRPC maps the same six lists to `Struct`. Label-then-children fits inside the existing `top` list without a proto change, provided each item is still a JSON-compatible dict.
- Search calls use the synchronous OpenSearch client inside `async def`, so the calls under `asyncio.gather` do not run concurrently. A second query adds serial blocking time.
- Tests in `app/routers/queries/__tests__/test_fetch_top_results.py` mock `client.search`. Two assert exact query structure (`test_boosts_playlists` and `test_excludes_unpublished_and_unready`) and will need updates. No test can check ranking.

### Findings (deduplicated, by severity)

**Blockers**

1. **The link field exists in the backend payload; its path through to the index is unconfirmed (downgraded from blocker).** Releases and tracks carry `label.id` and `artists[].id`; a track can have several artists, and `track.label` can be null. The open question is whether these reach the live index unchanged, because the `title` to `name` and `type` transform is not in the repos checked. Link by stable ID, not by name text, because same-name artists and labels exist and labels get renamed. Map link fields as `keyword`; dynamic mapping would make them `text`, which breaks `term` lookups. Releases have no `popularity`, so child ordering needs a fallback (suggested: `release_date` descending).
2. **"All words must match" conflicts with "show the label's releases".** Releases and tracks rarely contain "hot creations" in their own names, so a strict match removes them. The fix is two stages: stage 1 resolves the query to a top entity with strict matching; stage 2 fetches that entity's releases and tracks by link ID, not by text. Alternative: copy label and artist names onto release and track docs at index time so one-stage matching can hit them. That adds stale-name risk on rename.
3. **The response contract is undefined.** Open: whether `top` stays a flat list; how the 8 slots are shared between the lead entity and children; which children are shown if a label has hundreds; how clients tell the lead from its children.

**Major**

4. **Anchor rule is undefined.** Expand children only when the top label or artist matches the whole query exactly or as a whole-phrase prefix; otherwise return the flat ranked list. Without a rule, "Hot" could pick an arbitrary anchor and fill the list with the wrong entity's children. Same-name artist and label needs a deterministic order (suggested: exact `name.keyword` match, then type priority, then popularity, then `_id`).
5. **Size 8 is shared.** A prolific label fills all 8 slots. Use slot quotas, for example 1 lead plus a few releases plus a few tracks, then fill the rest from other matches.
6. **Leading wildcards do not scale.** The index is effectively unbounded. Edge-n-gram on `name` (or a `search_as_you_type` field) moves cost to index time. It needs a new index, a bounded gram length, and a load test.
7. **`query_string` on raw user input is unsafe.** Characters such as `:`, `(`, `"`, `/` and the words AND/OR change meaning or raise a parse error (500 in REST, unhandled in gRPC). Replace it with a `bool` of `match` (operator AND) clauses for earlier words and a prefix clause for the last word. State rules for case, punctuation and accents. Add a minimum query length and a token cap.
8. **Mapping change needs a versioned index behind an alias.** Create a v2 index, reindex or replay from the backend, swap the alias, keep v1 for rollback. `seed()` only creates an index when it is absent, so it never migrates. The index name comes from an env var read in more than one module. Move mapping and settings into one shared definition. The gRPC `DeleteIndex` calls `client.indices.delete_index(...)`, which looks like a wrong method name (the REST path uses `client.indices.delete`); check it before relying on that path for a migration.
9. **Rollout order matters.** If code ships before the index and link fields exist, strict matching can return nothing. Order: add fields and v2 index, backfill, verify counts and sample queries, deploy behind a flag with the old query as fallback, ramp, then remove the old path.
10. **Ranking clauses are partly dead.** The always-true popularity range and `minimum_should_match: 1` do nothing useful. Separate filtering (must) from ranking (popularity via `function_score` or sort, with `missing` handled and `_id` as final tie-break). Playlist and some seed docs have no `popularity`.
11. **Same pattern in five other fetch files.** Changing only top results leaves noisy matches in the per-type lists of the same response. Put the name-matching clause and the `is_visible` filter (duplicated in top-results and suggestions) in one shared builder.
12. **Observability gaps.** No latency metric or span around OpenSearch calls; no zero-result or expansion counter; no error capture in query functions (CLAUDE.md section 5 asks for Sentry capture and logging); `_score` and `_id` are dropped, so ranking cannot be explained in production. `search_terms_total{term}` has unbounded labels and debounced prefixes will grow it.
13. **Undefined terms and scope.** Top match, label query, artist query, trending, and match scope (`name` only, or all fields as now) need definitions. Which files are in scope (labels and others) is unstated.

**Nit**

14. Strict matching raises zero-result rates for typos. Consider a flagged `fuzziness: AUTO` fallback on the last word if that rate rises.
15. Empty and one- or two-character queries need a defined response.
16. Briefly cache stage-1 results by normalised query; debounced prefixes repeat.
17. Add a lowercase normalizer to `name.keyword`, otherwise the exact-match boost is case sensitive.
18. Confirm `is_visible` is mapped as boolean in the live index; a missing mapping silently excludes docs.

### Where the lenses disagree

- **Edge-n-gram now or later.** Zoom-out says the bug is fixed by operator and prefix changes alone, and n-grams can wait until prefix queries prove slow. Design, structural and inventive-catalyst say wildcards and prefix cost grow with the index, so n-gram and a reindex are the right choice. This brief stages it: query-only fix first, n-gram in a later stage, decided by measurement.
- **One query or two.** Inventive-catalyst allows a single `msearch`; structural, design and zoom-out prefer two explicit queries. Two queries (or `msearch`) is the common ground.

## Goals vs. Non-Goals

**Goals**

- "Hot Creations" returns the label first and no longer returns docs that match only "hot".
- Every typed word must match; the last word matches as a prefix.
- A label query returns the label, then its releases. An artist query returns the artist, then its releases and tracks. Children are ordered by popularity.
- No leading wildcards; raw user text is no longer interpreted as query syntax.
- Result size stays 8.
- A fixed list of example queries with expected results, usable as tests.

**Non-Goals**

- A real "trending" signal. Popularity stands in for v1.
- Fixing "Hot" alone: it still returns Hot Since 82 and Hot Natured. That is correct under the prefix rule.
- Typo tolerance or fuzzy matching (a possible later addition).
- Redesigning the per-type endpoints beyond reusing the shared matching clause.
- Changing the gRPC proto, unless the response-contract decision requires it.

## Alternatives Weighed

| Option | Fixes the symptom | Needs link field | Needs reindex | Verdict |
| --- | --- | --- | --- | --- |
| A. Set `default_operator: AND` on the current `query_string` | Yes | No | No | Smallest change, but keeps leading wildcards and syntax risk. Acceptable only as an interim step. |
| B. `bool` with `match` (AND) on earlier words and prefix on last word, replacing `query_string` | Yes | No | No (works on the standard analyzer) | Recommended for stage 1. |
| C. Edge-n-gram on `name` (or `search_as_you_type`) with B | Yes, and stays fast at scale | No | Yes | Recommended for a later stage, once measured. |
| D. Two-stage lookup: top entity, then a `term` filter on link ID, sorted by popularity | Delivers label then releases | Yes | Yes if fields are missing | Recommended for stage 3. |
| E. Copy label and artist names onto release and track docs, match in one query | Delivers label then releases | Yes (plus names) | Yes | Not chosen: stale names after renames and larger docs. Revisit if D adds too much latency. |
| F. Single compound query with a pinned top hit | Possible | Yes | Maybe | Not chosen: ordering is harder to test and explain. |
| G. Split into per-type indices behind one alias | Allows per-type analyzers | Yes | Yes | Not chosen for now: more indices to manage and scores cannot be compared across them. If kept as one index, name link fields distinctly (for example `parent_label_id`) and treat them as sparse. |

## Key Decisions & Staging for Next Steps

### Decisions needed from the owner

1. Link fields: the backend sends `label.id` and `artists[].id`. Confirm they reach the live index by running one `_search` against a real release and a real track, and find where `title` becomes `name`. If they are dropped, who adds them and who backfills?
2a. Release ordering: releases have no `popularity`. Use `release_date` descending, or the maximum popularity of the release's tracks?
2. Response contract: keep `top` as a flat list, or add a marker or grouped sections? How are the 8 slots split (for example 1 lead plus 3 releases plus 4 tracks)?
3. Anchor rule: exact or whole-phrase prefix only, or any top label or artist?
4. Tie order for a same-name artist and label (suggested: label over artist, then popularity; or show both).
5. Whether labels, artists, releases, tracks and playlists change in the same release (suggested: yes, through a shared builder, after top-results is proven).
6. Minimum query length and the empty-result response.
7. Whether a label query should also return the label's tracks. The user answers list releases only for labels.

### Staging

- **Stage 0: Discovery (blocks stages 2 and 3).** Confirm that `label.id` and `artists[].id` reach the live index and how they are mapped, where `title` becomes `name`, the live mapping of `is_visible` and `name`, and the cluster mode (`OPENSEARCH_MANAGED`) for later reindex steps.
- **Stage 1: Strict matching, no reindex.** Build a shared query builder (matching clause plus `is_visible` filter), use `bool`/`match` AND plus a last-word prefix, drop the dead popularity range, and add errors capture and logging. Add a minimum query length. Apply to top-results first, then the other fetch files. Update the two structure-asserting tests. Add an integration fixture with a label plus releases, "Hot Since 82", "Hot Natured", and a same-name artist and label, and assert the order for "Hot Creations", "Hot Crea" and "Hot". Add `search_opensearch` latency and zero-result metrics.
- **Stage 2: Index v2 (if measurement or link fields require it).** One shared mapping and settings definition, explicit `keyword` link fields, `name.keyword` with a lowercase normalizer, optional edge-n-gram subfield with bounded gram length, versioned index behind an alias, backfill, count checks, flag-gated cutover with rollback to v1.
- **Stage 3: Lead entity and children.** Two queries (or `msearch`): top match, then a link-ID filter sorted by popularity with `is_visible`, run only when the lead is a label or artist and meets the anchor rule. Compose in application code with slot quotas. Add expansion counters and a log of lead type and hit count.
- **Stage 4: Cleanup.** Remove the old query after a soak period; revisit fuzzy fallback and the `search_terms_total` label cardinality.

## Key objections and open risks

1. The backend sends `label.id` and `artists[].id`, but it is unconfirmed that they reach the live index, and they need a `keyword` mapping. Releases have no `popularity` to order by.
2. Strict matching deletes the docs the user wants unless children are fetched by link ID in a second step. That step also needs a decided response shape and slot split.
3. Any mapping change needs a new index and alias swap with no existing tooling, and mapping is defined in three places. Ship the query-only fix first and treat the reindex as a separate, measured step.
