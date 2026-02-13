"""
Ingest 소상공인 상가 CSV data into Langent Vector DB
=====================================================
서울 데이터 (534K rows)를 벡터화하여 3D 성운으로 시각화합니다.

CSV의 각 상가를 시맨틱 검색 가능한 텍스트 문서로 변환합니다.
"""
import csv
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langent.store.vector import VectorStore

NEO4J_DIR = r"c:\Users\daewooenc\workspace\Ontology\Neo4J"
SEOUL_CSV = os.path.join(
    NEO4J_DIR, "data", "소상공인시장진흥공단_상가(상권)정보_서울_202512.csv"
)

# 핵심 컬럼 인덱스 (0-indexed)
COL = {
    "id": 0,           # 상가업소번호
    "name": 1,         # 상호명
    "branch": 2,       # 지점명
    "cat_l": 4,        # 상권업종대분류명
    "cat_m": 6,        # 상권업종중분류명
    "cat_s": 8,        # 상권업종소분류명
    "std_cat": 10,     # 표준산업분류명
    "sido": 12,        # 시도명
    "sigungu": 14,     # 시군구명
    "dong_admin": 16,  # 행정동명
    "dong_legal": 18,  # 법정동명
    "road_name": 24,   # 도로명
    "bldg_name": 28,   # 건물명
}

# 위도/경도는 마지막 2개 컬럼 (37, 38)
LAT_COL = 37
LNG_COL = 38


def row_to_text(row):
    """CSV 행을 시맨틱 검색 가능한 텍스트로 변환"""
    name = row[COL["name"]] or "?"
    branch = row[COL["branch"]]
    cat_l = row[COL["cat_l"]]
    cat_m = row[COL["cat_m"]]
    cat_s = row[COL["cat_s"]]
    sigungu = row[COL["sigungu"]]
    dong = row[COL["dong_admin"]]
    road = row[COL["road_name"]] if COL["road_name"] < len(row) else ""
    bldg = row[COL["bldg_name"]] if COL["bldg_name"] < len(row) else ""

    full_name = f"{name} {branch}".strip() if branch else name
    location = f"{sigungu} {dong}".strip()
    category = f"{cat_l} > {cat_m} > {cat_s}".strip(" >")

    text = (
        f"{full_name} — {category}. "
        f"위치: 서울 {location}"
    )
    if road:
        text += f", {road}"
    if bldg:
        text += f" ({bldg})"

    return text


def row_to_metadata(row):
    """CSV 행에서 메타데이터 추출"""
    meta = {
        "source": "neo4j_상가정보_서울",
        "id": row[COL["id"]],
        "name": row[COL["name"]] or "",
        "category_large": row[COL["cat_l"]] or "",
        "category_small": row[COL["cat_s"]] or "",
        "sigungu": row[COL["sigungu"]] or "",
        "dong": row[COL["dong_admin"]] or "",
        "extension": ".csv",
    }
    # 위도/경도
    if LAT_COL < len(row) and row[LAT_COL]:
        meta["lat"] = row[LAT_COL]
    if LNG_COL < len(row) and row[LNG_COL]:
        meta["lng"] = row[LNG_COL]
    return meta


def ingest_seoul(max_rows=5000):
    """
    서울 상가 데이터를 벡터 DB에 수집합니다.
    전체 534K는 시간이 오래 걸리므로 먼저 5,000건 샘플로 시작합니다.
    """
    print("=" * 60)
    print(f"📥 서울 상가 데이터 → ChromaDB 벡터화")
    print(f"   Source: {SEOUL_CSV}")
    print(f"   Max rows: {max_rows:,}")
    print("=" * 60)

    vs = VectorStore(
        db_path="./data/chroma_db",
        collection_name="langent_knowledge",
    )
    print(f"\n기존 벡터 수: {vs.count():,}")

    # Read CSV
    documents = []
    metadatas = []
    ids = []
    districts = {}

    with open(SEOUL_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)

        for i, row in enumerate(reader):
            if i >= max_rows:
                break

            text = row_to_text(row)
            meta = row_to_metadata(row)
            doc_id = f"store_{meta['id']}"

            documents.append(text)
            metadatas.append(meta)
            ids.append(doc_id[:16])

            # Count by district
            gu = meta["sigungu"]
            districts[gu] = districts.get(gu, 0) + 1

    print(f"\n📊 구별 분포 ({len(districts)} 구):")
    for gu, cnt in sorted(districts.items(), key=lambda x: -x[1])[:10]:
        print(f"   {gu}: {cnt:,}")

    # Batch add
    print(f"\n⏳ {len(documents):,} 문서를 벡터화 중... (시간 소요)")
    start = time.time()

    batch_size = 500
    total_added = 0
    for j in range(0, len(documents), batch_size):
        b_docs = documents[j:j + batch_size]
        b_metas = metadatas[j:j + batch_size]
        b_ids = ids[j:j + batch_size]

        try:
            vs.collection.add(
                documents=b_docs,
                metadatas=b_metas,
                ids=b_ids,
            )
            total_added += len(b_docs)
        except Exception as e:
            # Skip duplicates
            for k in range(len(b_docs)):
                try:
                    vs.collection.add(
                        documents=[b_docs[k]],
                        metadatas=[b_metas[k]],
                        ids=[b_ids[k]],
                    )
                    total_added += 1
                except Exception:
                    pass

        if (j + batch_size) % 2000 == 0:
            elapsed = time.time() - start
            print(f"   ... {j + batch_size:,} / {len(documents):,} ({elapsed:.1f}s)")

    elapsed = time.time() - start
    print(f"\n✅ 완료!")
    print(f"   추가된 벡터: {total_added:,}")
    print(f"   전체 벡터 수: {vs.count():,}")
    print(f"   소요 시간: {elapsed:.1f}s")

    # Test search
    print("\n🔍 샘플 검색: '강남 치킨'")
    results = vs.search("강남 치킨", top_k=5)
    for r in results:
        print(f"   [{r['score']:.3f}] {r['document'][:60]}...")
        print(f"          📍 {r['metadata'].get('sigungu', '?')} {r['metadata'].get('dong', '?')}")


if __name__ == "__main__":
    # 먼저 500건으로 빠른 테스트
    ingest_seoul(max_rows=500)
