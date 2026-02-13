"""
GraphStore — Neo4j Adapter for Langent
========================================
Knowledge graph storage, Cypher execution, and 3D viz export.
"""
from typing import List, Dict, Any, Optional


class GraphStore:
    """
    Neo4j 기반 지식 그래프 저장소.

    엔티티/관계 CRUD, Cypher 실행, 3D 시각화용 그래프 내보내기.
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "yw02280228",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        return self._driver

    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False

    # ─── Cypher ───────────────────────────────────────

    def run_cypher(self, query: str, params: Dict = None) -> List[Dict]:
        """Cypher 쿼리를 실행합니다."""
        with self.driver.session() as session:
            result = session.run(query, parameters=params or {})
            return [dict(record) for record in result]

    def get_schema(self) -> Dict[str, Any]:
        """현재 그래프 스키마 정보를 반환합니다."""
        labels = self.run_cypher("CALL db.labels() YIELD label RETURN label")
        rels = self.run_cypher(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )
        counts = self.run_cypher(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
        )
        return {
            "labels": [r["label"] for r in labels],
            "relationship_types": [r["relationshipType"] for r in rels],
            "node_counts": {r["label"]: r["count"] for r in counts},
        }

    # ─── Entity / Relation CRUD ───────────────────────

    def create_entity(
        self, label: str, properties: Dict[str, Any]
    ) -> Dict:
        """엔티티(노드)를 생성합니다."""
        props_str = ", ".join(f"{k}: ${k}" for k in properties)
        query = f"CREATE (n:{label} {{{props_str}}}) RETURN n"
        result = self.run_cypher(query, properties)
        return result[0] if result else {}

    def merge_entity(
        self, label: str, key: str, properties: Dict[str, Any]
    ) -> Dict:
        """엔티티를 MERGE (있으면 업데이트, 없으면 생성)"""
        set_parts = ", ".join(f"n.{k} = ${k}" for k in properties if k != key)
        query = f"MERGE (n:{label} {{{key}: ${key}}})"
        if set_parts:
            query += f" SET {set_parts}"
        query += " RETURN n"
        result = self.run_cypher(query, properties)
        return result[0] if result else {}

    def create_relation(
        self,
        from_label: str, from_key: str, from_value: str,
        rel_type: str,
        to_label: str, to_key: str, to_value: str,
        properties: Dict = None,
    ) -> Dict:
        """두 노드 간 관계를 생성합니다."""
        props = ""
        params = {"from_val": from_value, "to_val": to_value}
        if properties:
            props = " {" + ", ".join(f"{k}: ${k}" for k in properties) + "}"
            params.update(properties)

        query = (
            f"MATCH (a:{from_label} {{{from_key}: $from_val}}), "
            f"(b:{to_label} {{{to_key}: $to_val}}) "
            f"MERGE (a)-[r:{rel_type}{props}]->(b) RETURN r"
        )
        result = self.run_cypher(query, params)
        return result[0] if result else {}

    def search_nodes(
        self, label: str = None, where: str = "", params: Dict = None, limit: int = 50
    ) -> List[Dict]:
        """노드를 검색합니다."""
        label_str = f":{label}" if label else ""
        where_str = f" WHERE {where}" if where else ""
        query = f"MATCH (n{label_str}){where_str} RETURN n LIMIT {limit}"
        return self.run_cypher(query, params)

    # ─── 3D Visualization Export ──────────────────────

    def export_for_viz(self, limit: int = 500) -> Dict[str, Any]:
        """
        3D 시각화용 노드/엣지 데이터를 내보냅니다.
        Returns: {nodes: [...], edges: [...]}
        """
        # Nodes
        nodes_raw = self.run_cypher(
            "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, "
            "properties(n) AS props LIMIT $limit",
            {"limit": limit},
        )
        nodes = []
        for n in nodes_raw:
            label = n["labels"][0] if n["labels"] else "Unknown"
            name = n["props"].get("name", n["props"].get("id", str(n["id"])))
            nodes.append({
                "id": str(n["id"]),
                "label": label,
                "name": str(name),
                "properties": {k: str(v) for k, v in n["props"].items()},
            })

        # Edges
        edges_raw = self.run_cypher(
            "MATCH (a)-[r]->(b) RETURN id(a) AS src, id(b) AS dst, "
            "type(r) AS type LIMIT $limit",
            {"limit": limit * 2},
        )
        edges = [
            {"source": str(e["src"]), "target": str(e["dst"]), "type": e["type"]}
            for e in edges_raw
        ]

        return {"nodes": nodes, "edges": edges}

    # ─── Cleanup ──────────────────────────────────────

    def close(self):
        if self._driver:
            self._driver.close()

    def __repr__(self):
        return f"<GraphStore(uri='{self.uri}')>"
