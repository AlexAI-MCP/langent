"""Tests for langent.store.graph — Cypher injection prevention"""
import pytest
from langent.store.graph import GraphStore, _validate_identifier


class TestCypherInjectionPrevention:
    def test_valid_identifiers(self):
        assert _validate_identifier("Person", "label") == "Person"
        assert _validate_identifier("name", "key") == "name"
        assert _validate_identifier("_private", "key") == "_private"
        assert _validate_identifier("Node123", "label") == "Node123"

    def test_invalid_identifiers_raise(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("Person; DROP", "label")

        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("key with spaces", "key")

        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("123start", "label")

        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("a.b.c", "key")

        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("label})-[:HACK]->(", "label")

    def test_graph_store_default_password_is_safe(self):
        gs = GraphStore()
        assert gs.password == "password"
        assert "yw" not in gs.password

    def test_create_entity_validates_label(self):
        gs = GraphStore()
        with pytest.raises(ValueError, match="Invalid Cypher label"):
            gs.create_entity("Bad Label!", {"name": "test"})

    def test_create_entity_validates_property_keys(self):
        gs = GraphStore()
        with pytest.raises(ValueError, match="Invalid Cypher property key"):
            gs.create_entity("Person", {"bad key!": "test"})

    def test_merge_entity_validates_identifiers(self):
        gs = GraphStore()
        with pytest.raises(ValueError):
            gs.merge_entity("Person; DROP", "name", {"name": "test"})
        with pytest.raises(ValueError):
            gs.merge_entity("Person", "bad key!", {"bad key!": "test"})

    def test_create_relation_validates_all(self):
        gs = GraphStore()
        with pytest.raises(ValueError):
            gs.create_relation(
                "Bad!", "name", "a", "REL", "Person", "name", "b"
            )
        with pytest.raises(ValueError):
            gs.create_relation(
                "Person", "name", "a", "BAD REL", "Person", "name", "b"
            )

    def test_search_nodes_validates_label(self):
        gs = GraphStore()
        with pytest.raises(ValueError):
            gs.search_nodes(label="Bad Label!")
