NOT_SEARCHABLE_KEYWORD: dict[str, object] = {"type": "keyword", "index": False}

# Playlist documents are the backend outbox payload. Only `name` (mapped
# elsewhere) is searchable, so every other field is stored but not indexed.
# Mappings apply to the whole shared index, so this also covers the same field
# names on other document types.
PLAYLIST_MAPPING: dict[str, dict[str, object]] = {
    "id": {"type": "keyword"},
    "sub_title": NOT_SEARCHABLE_KEYWORD,
    "description": {"type": "text", "index": False},
    "colour": NOT_SEARCHABLE_KEYWORD,
    "artwork_url": NOT_SEARCHABLE_KEYWORD,
    "hero_image_url": NOT_SEARCHABLE_KEYWORD,
    "created_by_id": NOT_SEARCHABLE_KEYWORD,
    "private": {"type": "boolean", "index": False},
    "category": {
        "properties": {"id": NOT_SEARCHABLE_KEYWORD, "name": NOT_SEARCHABLE_KEYWORD}
    },
    "tags": {
        "properties": {"id": NOT_SEARCHABLE_KEYWORD, "name": NOT_SEARCHABLE_KEYWORD}
    },
}

INDEX_PROPERTIES: dict[str, dict[str, object]] = {
    "popularity": {"type": "integer"},
    **PLAYLIST_MAPPING,
}
