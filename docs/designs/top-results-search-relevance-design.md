# Top-results search relevance

*   **Author:** Alex Callow
*   **Status:** Implemented (word matching in #3, label and artist expansion in #5). Live-index checks open.
*   **Date:** 2026-11-16

--------------------------------------------------------------------------------

## Overview

The top-results search in `ufb-search` returns up to 8 mixed results (artists, labels, releases, tracks, playlists) as the user types. This design changes how the query matches text and how it orders results, so that searching for a label or artist by full name returns that label or artist first, followed by its own releases and tracks.

## The Problem

Searching "Hot Creations" returns the Hot Creations label first. The next results are "Hot Since 82" and "Hot Natured", which share only the word "hot". The label's own releases and tracks, such as "Double Up", do not match the text, so they only appear if they happen to rank.

Cause, in `app/routers/queries/fetch_top_results.py`:

*   The main clause is a `query_string` of `*Hot Creations*` with no `default_operator`, so it is OR. The wildcards attach only to the outer edges, giving `*Hot` and `Creations*`. Any document containing "hot" matches. The clause also searches every field and starts with a wildcard, which gets slower as the index grows.
*   The phrase, exact-name, type and popularity clauses sit in `should` with `minimum_should_match: 1`. The popularity range (`gte: 0`) matches every document that has a popularity value, so it satisfies `minimum_should_match` alone. These clauses change the order of results. They never remove any.
*   The same `*{query}*` pattern is in `fetch_labels_results.py`, `fetch_artist_results.py`, `fetch_releases_results.py` and `fetch_tracks_results.py`. `fetch_playlist_results.py` uses it too, but only on `name`.

Proposed solution: require every typed word to match (the last word as a prefix, because input is debounced type-ahead), remove documents that do not match, and when the best match is a label or artist, add that entity's releases and tracks by a stable ID link. Releases are newest first and tracks are ordered by popularity.

## Goals

*   Searching a full label name, for example "Hot Creations", returns the label first. Documents that match only part of the query, such as "Hot Since 82" and "Hot Natured", no longer appear.
*   Every typed word must match. The last word matches as a prefix, so "Hot Crea" still finds Hot Creations.
*   A label match is followed by that label's releases. An artist match is followed by that artist's releases and tracks. Children are linked by ID, not by name text. Releases are newest first and tracks are ordered by popularity.
*   No leading wildcards, and raw user text is no longer parsed as query syntax.
*   The result size stays 8.
*   A fixed list of example queries with expected results exists and runs as tests.

## Non-Goals

*   A "trending" signal. Popularity stands in for it in this version.
*   Changing what a one-word query like "Hot" returns. It still returns Hot Since 82 and Hot Natured, because each of those matches every typed word.
*   Typo tolerance or fuzzy matching.
*   Redesigning the per-type endpoints beyond reusing the shared matching clause.
*   Changing the gRPC proto, unless the response-shape decision in the Technical Plan requires it.

## Open Questions

*   **Link fields in the live index (UPF-325)**: The Django backend (`ufb/backend/upfrontbeats/models/release.py`, `track.py`) sends `label: {id, name}` and `artists: [{id, name}]`. It is not confirmed that these reach the live OpenSearch index, or how they are mapped. The code uses `label.id.keyword` and `artists.id.keyword`, which is right for a dynamically mapped index. If the live mapping differs, change `LABEL_ID_FIELD` or `ARTIST_ID_FIELD` in `fetch_top_results.py`. Until this is confirmed, a label or artist still comes first but its children may not appear.
*   **Field renaming**: The backend payload uses `title` for tracks and releases, but this repo queries `name` and `type`. The transform between Kafka and OpenSearch was not found in the repos checked. The matcher searches both `name` and `title`, so it works either way.
*   **Minimum query length**: Not decided. An empty or whitespace-only query matches nothing (`match_none`). A one-character query runs as a normal prefix query.
*   **Latency metric**: The brief proposed a latency metric around OpenSearch calls. It was not added. Only the lead-expansion and zero-result counters were.

Decided while implementing: no feature flag (rollback is a revert of the deploy), and the work shipped as two pull requests (word matching first, then label and artist expansion). All six fetch files changed in the first one.

## Technical Plan (Architecture)

### Decisions recorded

| Decision | Choice |
| --- | --- |
| Response shape | Flat `results.top` list, lead first, then its children. No new fields and no `search.proto` change. |
| Anchor rule | Expand only when the normalised query equals the lead's full name. |
| Slot split | Quotas with refill: 1 lead, artist gets 3 releases and 4 tracks, label gets 7 releases. Unused slots are filled with the next-best text matches. |
| Release ordering | `release_date` descending, releases with no date last. Tracks are ordered by `popularity` descending. |
| Same-name artist and label | Fixed type priority, artist first, set in one constant. |
| Label tracks | Releases only for a label, as you described. |
| Rollout | No feature flag. Rollback is a revert of the deploy. |
| Delivery | Two pull requests: word matching in all six fetch files (#3), then lead expansion in top results (#5). |

### How a request flows

`fetch_top_results(query)` keeps its signature and return type (a list of `_source` dicts). Inside it does three things.

1.  **Strict text match.** One OpenSearch query, size 8, over `name` and `title` (the backend sends `title` for releases and tracks). Earlier words must each match whole (`multi_match` with `operator: and`). The last word matches as a prefix (a `prefix` clause per field on the lowercased token). Documents that fail either condition are removed. This replaces `query_string` entirely, so raw user text is never parsed as query syntax. The existing `is_visible` filter for releases and tracks stays. The type boosts stay as `should` clauses that only rank. The popularity range clause is replaced by a `function_score` on `popularity` (`field_value_factor`, `log1p` modifier, `missing: 1`), so popularity ranks results without deciding whether a document matches.
2.  **Lead detection, in application code.** Take the hits from step 1. The lead is a hit of type `labels` or `artists` whose `name`, trimmed and case-folded, equals the trimmed, case-folded query. If both a label and an artist qualify, the fixed priority constant picks one. If none qualifies, there is no lead, and the response is the step 1 hits as they are.
3.  **Children by ID, one `msearch`.** When there is a lead, send its child queries in a single `client.msearch` call.
    *   **Label lead:** releases where `label.id` equals the lead's `id`, `is_visible` true, sorted by `release_date` descending, size 7.
    *   **Artist lead:** releases where `artists.id` equals the lead's `id`, size 3, sorted by `release_date` descending. And tracks where `artists.id` equals the lead's `id`, size 4, sorted by `popularity` descending. Both need `is_visible` true.

The final list is the lead, then its releases, then its tracks, then step 1 hits not already included (the refill) until 8 results exist. Children are matched by ID and not by text, so "Double Up" appears even though its name does not contain "hot creations".

```text
GET /?q=Hot Creations
        |
        v
 fetch_top_results
        |
        +--> 1. strict text match (AND words, last word prefix) ---> hits (<= 8)
        |
        +--> 2. lead = hit of type label/artist whose name == query
        |         |
        |         +-- none --> return hits
        |         |
        |         +-- found --> 3. msearch children by label.id / artists.id
        |                                |
        v                                v
   [lead] + releases + tracks + remaining hits (refill)  --> results.top (8)
```

Example: "Hot Creations" matches the label by exact name. Step 3 returns up to 7 of its releases by `release_date`. "Hot Since 82" and "Hot Natured" do not contain "creations", so step 1 never returns them. "Hot Crea" has no exact-name lead, so it returns the step 1 hits only, with no children.

### Reuse and shared pieces

*   The matching clause is built by one shared function. `fetch_top_results.py` and the five per-type fetch files (artists, labels, releases, tracks, playlists) all use it in the same change, so the five lists beside `top` stop returning "hot"-only matches. They do not gain children. `fetch_suggestions_results.py` is not changed, because it already uses `match_phrase_prefix` and does not have this bug.
*   The sync OpenSearch client already runs inside `async def`, so these calls do not run concurrently with each other. Using one `msearch` for the child queries limits the extra cost to one more round trip.

### Error handling and observability

*   If the child lookup fails, or an `msearch` item reports an error, the function logs a warning, calls `sentry_sdk.capture_exception`, and returns the step 1 hits, so a failed expansion never empties the response. An error in the step 1 search is not caught here. It reaches the caller, and FastAPI's Sentry integration reports it.
*   The lead type, lead id and child counts are logged when a lead expands. `search_lead_expansions_total{lead_type}` counts expansions and `search_zero_results_total{endpoint}` counts searches with no results.

### Not changed

*   `search.proto`, the REST response keys and the gRPC mapping of `top`.
*   The index mapping and settings. The exact-name test runs in application code, so `name.keyword` needs no normalizer in this change.

### Dependencies on facts not yet confirmed

*   The child queries need `label.id` on releases, and `artists.id` on releases and tracks, to be filterable as exact values. Dynamic mapping likely makes them `text` with a `.keyword` subfield, so the queries may need `label.id.keyword` and `artists.id.keyword`. If the live fields do not exist, label and artist expansion is blocked on a backend and mapping change, and only the strict matching ships.
*   The backend payload uses `title` for releases and tracks. The matcher searches `name` and `title`, so it works whether or not something maps `title` to `name`.

## Alternatives Considered

### Approach alternatives (from the concepts brief)

#### Alternative A: Set `default_operator: AND` on the current `query_string`

*   **Pros**: A one-line change. Fixes the "Hot Since 82" symptom. No reindex and no link field needed.
*   **Cons**: Keeps the leading wildcard, whose cost grows with the index. Keeps parsing raw user text as query syntax, so characters such as `:`, `(`, `"` and `/` change meaning or raise a parse error (a 500 in REST and an unhandled error in gRPC). Does not deliver the label's releases.
*   **Reason for Rejection**: Rejected by author: it fixes only the symptom and leaves the cost and the query-syntax risk in place.

#### Alternative B: Edge-n-gram or `search_as_you_type` on `name`

*   **Pros**: Moves prefix cost from query time to index time, so it keeps its speed as the index grows. Removes the need for `prefix` queries.
*   **Cons**: Needs a new index, a bounded gram length, a reindex or replay from the backend, and a load test. The repo has no alias or reindex tooling, and mappings are defined in three places (`app/routers/search.py`, `app/grpc/server.py`, `app/seed.py`).
*   **Reason for Rejection**: Rejected by author for this change: the strict match fixes the reported bug without a mapping change. The `prefix` clause on one field is bounded by the debounced input. Revisit if measured latency on the `prefix` clause is too high at the real index size (see Future Improvements).

#### Alternative C: Copy label and artist names onto release and track documents, and match in one query

*   **Pros**: One query could match "hot creations" against a release's own copy of the label name, with no second step.
*   **Cons**: Names go stale when a label or artist is renamed unless every child is republished. Documents grow. A text match on the copied name would also return every release whose label name matches, which is a different rule from the exact-name anchor.
*   **Reason for Rejection**: Rejected by author: stale names after renames and larger documents. The ID link already exists in the payload, so it is the better source.

#### Alternative D: A single compound query with a pinned top hit

*   **Pros**: One round trip.
*   **Cons**: The ordering is harder to explain and to test, because the lead, the children and the other matches share one score.
*   **Reason for Rejection**: Rejected by author: the application-side composition in the Technical Plan has a defined order and can be tested with a fixed list of example queries.

#### Alternative E: Split the index into per-type indices behind one alias

*   **Pros**: Allows per-type analyzers.
*   **Cons**: More indices to manage. Scores from different indices cannot be compared.
*   **Reason for Rejection**: Rejected by author for now: it is a larger migration than the problem needs.

### Decision alternatives (chosen during drafting)

#### Response shape: marker field, or separate sections

*   **Marker field** (`match_role` on each item) would let clients group the lead and its children, but every client has to read a new field, and the backend and the apps need to agree on it.
*   **Separate sections** (`lead` and `lead_children` beside `top`) is explicit, but needs a `search.proto` change and regeneration, and clients that show `top` and `lead` together would show the lead twice.
*   **Reason for Rejection**: Rejected by author: a flat list with the lead first needs no contract change. Grouping is by position and by `type`.

#### Anchor rule: whole-query prefix, or any top label or artist

*   **Whole-query prefix** would expand while the user is still typing, but "Hot" would expand whichever name starting with "hot" has the highest popularity, which may be the wrong entity.
*   **Any top label or artist** has the fewest conditions, but weak matches would get children too.
*   **Reason for Rejection**: Rejected by author: exact name only gives no wrong anchors. The cost is that a partial name, such as "Hot Creat", shows no children until the full name is typed.

#### Slot split: quotas without refill, or one merged list

*   **Quotas without refill** leave slots empty when a lead has fewer children than its quota.
*   **One merged list** needs a score that compares releases and tracks, and releases have no `popularity`.
*   **Reason for Rejection**: Rejected by author: quotas with refill always give 8 results when 8 exist, and the quotas are easy to test.

#### Release ordering: backend popularity, or query-time computation

*   **Backend release popularity** matches the wording "by popularity", but needs a backend change, a backfill, and a republish when track popularity changes.
*   **Query-time computation** needs no backend change, but adds an aggregation or an extra query to every expansion.
*   **Reason for Rejection**: Rejected by author: `release_date` descending needs no new data. The cost is that an old hit can rank behind newer minor releases.

#### Same-name artist and label: higher popularity, or expand both

*   **Higher popularity leads** follows real behaviour, but labels and artists may not have comparable popularity, so one type could always win.
*   **Expand both** hides nobody, but each lead gets fewer children and the list holds two groups.
*   **Reason for Rejection**: Rejected by author: a fixed type priority is deterministic and easy to test. The cost is that a user who meant the other type sees it second.

--------------------------------------------------------------------------------

### Future Improvements

*   **Edge-n-gram on `name`**: If the `prefix` clause is too slow at the real index size, move prefix matching to index time (Alternative B).
*   **Typo tolerance**: A flagged `fuzziness: AUTO` fallback on the last word, if the zero-result rate rises after strict matching.
*   **Trending**: Replace popularity with a real trending signal.
*   **Caching**: A short cache of the first query by normalised query, because debounced prefixes repeat.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

This section describes what shipped. All new and changed Python follows the repo's `CLAUDE.md`: explicit parameter and return types on every function and method, modern union and collection types, no `Any`, logging for significant actions, and `sentry_sdk.capture_exception` wherever an exception is caught. The existing per-type fetch functions were untyped, so every function that was edited got types.

Constants:

*   In `name_match.py`: `SEARCH_FIELDS = ("name", "title")`, the fields the word match queries.
*   In `fetch_top_results.py`: `LABEL_ID_FIELD = "label.id.keyword"` and `ARTIST_ID_FIELD = "artists.id.keyword"` (the link fields on releases and tracks, defaulting to the `.keyword` subfield of the dynamic mapping, changed in one place if the live mapping differs), `LEAD_TYPE_PRIORITY = ("artists", "labels")`, `TOP_SIZE = 8`, `LABEL_RELEASE_QUOTA = 7`, `ARTIST_RELEASE_QUOTA = 3`, `ARTIST_TRACK_QUOTA = 4`.

### Target Files to Create/Modify

#### 1. `app/routers/queries/name_match.py` (Create)

*   **Type / Scope**: Python module, shared query builder.
*   **Proposed Changes**:
    *   `name_match_query(query: str, fields: Sequence[str] = SEARCH_FIELDS) -> dict[str, object]`: split the query on whitespace. Return a `bool` query whose `must` has one `multi_match` clause over `fields` with `operator: "and"` for all words except the last, and one `bool` of `prefix` clauses (one per field, at least one must match) for the last word, lowercased. With a single word, only the `prefix` clause is present. Words are inserted as values, never concatenated into a query string, so characters such as `:`, `(` and `"` carry no query syntax. An empty or whitespace-only query returns a `match_none` query.
    *   `visible_filter() -> dict[str, object]`: the existing filter that excludes releases and tracks without `is_visible: true` and lets other types through. It is the same filter that `fetch_top_results.py` builds today.
    *   `SEARCH_FIELDS`.

#### 2. `app/routers/queries/fetch_top_results.py` (Modify)

*   **Type / Scope**: Python query function.
*   **Proposed Changes**:
    *   `fetch_top_results(query: str) -> list[dict[str, object]]` keeps its name and caller contract.
    *   Step 1 query: `size: TOP_SIZE`. `bool.must` is `name_match_query(query)`. `bool.filter` is `visible_filter()`. The type boosts (artists, labels, tracks, releases, playlists) stay as `should` with no `minimum_should_match`. Remove the `match_phrase`, `term` on `name.keyword` and `range` popularity clauses. Wrap in `function_score` with `field_value_factor` on `popularity` (`modifier: "log1p"`, `missing: 1`) and `boost_mode: "sum"`.
    *   Private `_find_lead(hits, query) -> dict[str, object] | None`: among hits with `type` in `LEAD_TYPE_PRIORITY`, return the one whose `name`, trimmed and case-folded, equals the trimmed, case-folded query, preferring the earlier type in `LEAD_TYPE_PRIORITY`; return `None` if no hit qualifies.
    *   Private `_fetch_children(lead) -> tuple[list[dict[str, object]], list[dict[str, object]]]`: send one `client.msearch` call. For a label lead: one request, `term` on `LABEL_ID_FIELD` equal to the lead `id`, `type` `releases`, `is_visible` true, `sort` `release_date` desc with `missing: "_last"` and `unmapped_type: "date"` (so an index with no release dates yet does not fail the sort), size `LABEL_RELEASE_QUOTA`. For an artist lead: a releases request (`ARTIST_ID_FIELD`, size `ARTIST_RELEASE_QUOTA`, same sort) and a tracks request (`ARTIST_ID_FIELD`, `type` `tracks`, `is_visible` true, `sort` `popularity` desc, size `ARTIST_TRACK_QUOTA`). Returns `(releases, tracks)`.
    *   Private `_compose(lead, releases, tracks, hits) -> list[dict[str, object]]`: lead, then releases, then tracks, then the step 1 hits whose `id` is not already included, truncated to `TOP_SIZE`.
    *   Error handling: on an `msearch` error, or an error in any `msearch` item, log a warning, call `sentry_sdk.capture_exception`, and return the step 1 hits. A step 1 error is not caught and reaches the caller.
    *   Logging: `logger.info` when a lead expands (lead type, lead id, release count, track count) and when a search returns nothing.
    *   Metrics: `search_lead_expansions_total` when a lead expands and `search_zero_results_total` when there are no hits.

#### 3. `app/routers/queries/fetch_artist_results.py`, `fetch_labels_results.py`, `fetch_releases_results.py`, `fetch_tracks_results.py`, `fetch_playlist_results.py` (Modify, one change each)

*   **Type / Scope**: Python query functions.
*   **Proposed Changes**: Replace each `query_string` `*{query}*` clause with `name_match_query(query)`. Keep each file's other clauses (the `type` filter, the `is_visible` filter and the sort). In `fetch_artist_results.py`, remove the always-true popularity range clause. Add `query: str` and a return type to each function. Playlists keep matching only `name` (`fields=["name"]`), as they do today.

#### 4. `app/utils/metrics.py` (Modify)

*   **Type / Scope**: Prometheus counters.
*   **Proposed Changes**: Add `search_lead_expansions_total` (labels: `lead_type`, added with the expansion in #5) and `search_zero_results_total` (labels: `endpoint`, added with the word matching in #3). Both have low cardinality. The existing `search_terms_total{term}` is left as it is.

#### 5. `app/seed.py` (Modify)

*   **Type / Scope**: Local seed data.
*   **Proposed Changes**: Change the `SEED_DOCUMENTS` type from `list[dict[str, str | int | None]]` to `list[dict[str, object]]`, because link fields are nested objects. Add: the artists "Hot Since 82", "Hot Natured" and "Ronnie Spiteri"; two releases and a track for Hot Creations carrying `label: {id, name}`, `artists: [...]` and (for releases) `release_date`. Each has `is_visible` where the type needs it. These let `make local-up` reproduce "Hot Creations" by hand.

#### 6. `app/routers/queries/__tests__/test_name_match.py` (Create)

*   **Type / Scope**: Unit test.
*   **Proposed Changes**: Check that `name_match_query("Hot Creations")` has `multi_match` AND on "Hot" and `prefix` on "creations" for each field; a one-word query has only `prefix`; the last word is lowercased; characters such as `:`, `"`, `(` and `AND` appear only as values; an empty query returns `match_none`. Check that `visible_filter()` equals the filter the old query used.

#### 7. `app/routers/queries/__tests__/test_fetch_top_results.py` (Modify)

*   **Type / Scope**: Unit test, mocked `client`.
*   **Proposed Changes**: Update `test_fetch_top_results_returns_hits` and the empty-result test so `client.search` mocks match the new flow. Update `test_fetch_top_results_boosts_playlists` (the type boosts are still in `should`) and `test_fetch_top_results_excludes_unpublished_and_unready` (the filter now comes from `visible_filter()`). Add cases: an exact-name label hit leads (ignoring case and extra spaces) and `msearch` is called with `LABEL_ID_FIELD` and the lead `id`; an artist lead sends releases and tracks requests with the 3 and 4 quotas; a same-name artist and label gives the artist the lead; no exact-name hit means no `msearch` call; the refill excludes ids already used and the result is truncated to 8; a partial name and a playlist with the same name do not expand; an `msearch` error, or an error inside an `msearch` item, returns the step 1 hits and calls `sentry_sdk.capture_exception`.

#### 8. `app/routers/queries/__tests__/test_fetch_artists_results.py`, `test_fetch_labels_results.py`, `test_fetch_releases_results.py`, `test_fetch_tracks_results.py`, `test_fetch_playlist_results.py` (Modify only if they assert the old query)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: Update any assertion on `query_string` to assert the `name_match_query` clause. Tests that only check returned hits stay as they are.

#### 9. `app/routers/queries/__tests__/test_top_results_integration.py` (Create)

*   **Type / Scope**: Integration test against a real OpenSearch, skipped unless `OPENSEARCH_INTEGRATION=1` is set. `OPENSEARCH_INTEGRATION_URL` points at a cluster without the security plugin (the file's docstring has a `docker run` command).
*   **Proposed Changes**: Create a temporary index, load a fixture (the label "Hot Creations" with releases and tracks, "Hot Since 82", "Hot Natured", a same-name artist and label, a release with a null `release_date`, and an invisible release), run `fetch_top_results`, then delete the index. Expected results: "Hot Creations" returns the label first, then its visible releases by `release_date` descending (null last), and neither "Hot Since 82" nor "Hot Natured"; "Hot Crea" returns the text matches and no children; "Hot" returns "Hot Since 82", "Hot Natured", the label and a track with no children; the same-name query returns the artist first, with 3 releases and 4 tracks; results never exceed 8. This is the fixed list of example queries from the Goals.

### Verification Plan

*   **Compilation/Build**: `pipenv run type_check` (mypy).
*   **Unit Tests**: `pipenv run tests`.
*   **Static Analysis & Linting**: `pipenv run lint` (flake8), `pipenv run format --check .` (black), `pipenv run sort --check-only` (isort). These are the same commands `.circleci/config.yml` runs.
*   **Test Coverage Requirement**: The repo has no coverage threshold. Every new function and every branch in `_find_lead`, `_fetch_children` and `_compose` has a unit test.
*   **E2E/Integration**: `OPENSEARCH_INTEGRATION=1 OPENSEARCH_INTEGRATION_URL=http://localhost:9201 pipenv run tests app/routers/queries/__tests__/test_top_results_integration.py` against a local container. All 5 integration tests passed when #5 was written.
*   **Live-index check (UPF-325)**: Run one `_search` on a real release and a real track in the live index. Confirm that `label.id` and `artists.id` exist and how they are mapped (to set `LABEL_ID_FIELD` and `ARTIST_ID_FIELD`). If the link fields are missing, a label or artist still leads but gets no children, which is the behaviour before #5. Then check "Hot Creations" in the app.
*   **Rollout and rollback**: No mapping or proto change, so there is no data migration. Deploy as usual. Rollback is a revert of the deploy.

--------------------------------------------------------------------------------

*Drafted with EGM*
