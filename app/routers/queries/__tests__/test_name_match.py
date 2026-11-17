from app.routers.queries.name_match import name_match_query, visible_filter


def test_all_words_but_the_last_must_match_and_the_last_is_a_prefix() -> None:
    assert name_match_query("Hot Creations") == {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": "Hot",
                        "fields": ["name", "title"],
                        "operator": "and",
                    }
                },
                {
                    "bool": {
                        "should": [
                            {"prefix": {"name": {"value": "creations"}}},
                            {"prefix": {"title": {"value": "creations"}}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
            ]
        }
    }


def test_a_single_word_is_only_a_lowercased_prefix() -> None:
    must = name_match_query("HOT")["bool"]["must"]  # type: ignore[index]

    assert len(must) == 1
    assert "multi_match" not in str(must)
    assert {"prefix": {"name": {"value": "hot"}}} in must[0]["bool"]["should"]


def test_user_text_is_only_ever_a_value() -> None:
    query = name_match_query('foo:bar (AND) "x"')

    assert "query_string" not in str(query)
    assert "multi_match" in str(query)
    assert query["bool"]["must"][0]["multi_match"]["query"] == "foo:bar (AND)"  # type: ignore[index]


def test_extra_whitespace_is_ignored() -> None:
    assert name_match_query("  Hot   Creations ") == name_match_query("Hot Creations")


def test_an_empty_query_matches_nothing() -> None:
    assert name_match_query("") == {"match_none": {}}
    assert name_match_query("   ") == {"match_none": {}}


def test_fields_can_be_limited() -> None:
    query = name_match_query("late night", fields=["name"])

    assert "title" not in str(query)


def test_visible_filter_lets_other_types_through_and_hides_unready_media() -> None:
    should = visible_filter()["bool"]["should"]  # type: ignore[index]

    assert {"bool": {"must_not": {"terms": {"type": ["releases", "tracks"]}}}} in should
    assert {"term": {"is_visible": True}} in should
