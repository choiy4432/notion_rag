import chromadb
import config


class VectorStore:
    def __init__(self):
        # 로컬에 데이터 저장 (./chroma_db 폴더 생성됨)
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="notion_pages", metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
        )

    def add_chunks(self, chunks: list, embeddings: list):
        """청크와 임베딩 벡터를 DB에 저장"""
        self.collection.upsert(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=[c["text"] for c in chunks],
            metadatas=[{"page_id": c["page_id"], "page_title": c["page_title"]} for c in chunks],
        )

    def remove_page(self, page_id: str):
        """Remove all chunks belonging to a page_id from the collection."""
        try:
            all_items = self.collection.get(include=["metadatas"])
        except Exception:
            all_items = self.collection.get()
        ids = all_items.get("ids", [])
        metadatas = all_items.get("metadatas", [])
        ids_to_delete = []
        for idx, meta in enumerate(metadatas):
            if isinstance(meta, dict) and meta.get("page_id") == page_id:
                ids_to_delete.append(ids[idx])
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

    def search(self, query_embedding: list, top_k: int = None, all_results: bool = False) -> list:
        """쿼리 벡터와 유사한 문서 검색, 임계값 이상만 반환
        all_results=True면 임계값 적용 전 모든 결과 반환 (디버깅용)"""
        top_k = top_k or config.TOP_K
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=top_k, include=["documents", "metadatas", "distances"]
        )

        filtered = []
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            similarity = 1 - dist  # chromadb cosine distance → similarity 변환
            if all_results or similarity >= config.SIMILARITY_THRESHOLD:
                filtered.append(
                    {"text": doc, "page_title": meta.get("page_title", ""), "similarity": round(similarity, 3)}
                )
        return filtered

    def count(self):
        return self.collection.count()
