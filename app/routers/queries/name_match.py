from collections.abc import Sequence

# Releases and tracks are sent by the backend with `title`; labels, artists and
# playlists with `name`. A field missing from a document simply does not match.
SEARCH_FIELDS: tuple[str, ...] = ("name", "title")


def name_match_query(
    query: str, fields: Sequence[str] = SEARCH_FIELDS
) -> dict[str, object]:
    """Every word must match; the last word matches as a prefix (type-ahead).

    Words are passed as values, so user text is never parsed as query syntax.
    """
    words = query.split()
    if not words:
        return {"match_none": {}}

    *whole_words, last_word = words
    must: list[dict[str, object]] = []
    if whole_words:
        must.append(
            {
                "multi_match": {
                    "query": " ".join(whole_words),
                    "fields": list(fields),
                    "operator": "and",
                }
            }
        )
    must.append(
        {
            "bool": {
                "should": [
                    {"prefix": {field: {"value": last_word.lower()}}}
                    for field in fields
                ],
                "minimum_should_match": 1,
            }
        }
    )
    return {"bool": {"must": must}}


def visible_filter() -> dict[str, object]:
    """Releases and tracks must be visible; every other type passes."""
    return {
        "bool": {
            "should": [
                {
                    "bool": {
                        "must_not": {
                            "terms": {"type": ["releases", "tracks"]},
                        },
                    },
                },
                {"term": {"is_visible": True}},
            ],
            "minimum_should_match": 1,
        },
    }
