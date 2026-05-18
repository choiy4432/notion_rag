import sys
import os
import json
from notion_loader import NotionLoader
from embedder import embed_text
from db import VectorStore
from rag import RAGSearcher


def reload():
    """Incremental Notion data reload: only embed changed pages."""
    print("=== Notion incremental 데이터 로딩 시작 ===")
    loader = NotionLoader()
    store = VectorStore()

    index_path = os.path.join(os.path.dirname(__file__), "page_index.json")
    prev_index = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                prev_index = json.load(f)
        except Exception:
            prev_index = {}

    pages = loader.get_pages_summary()
    pages_by_id = {p["id"]: p for p in pages if p.get("id")}

    # detect removed pages
    removed = [pid for pid in prev_index.keys() if pid not in pages_by_id]
    for pid in removed:
        print(f"삭제된 페이지 제거 중: {pid}")
        try:
            store.remove_page(pid)
        except Exception as e:
            print(f"  DB 삭제 실패: {pid} ({e})")
        prev_index.pop(pid, None)

    # detect updated or new pages
    to_update = []
    for pid, p in pages_by_id.items():
        last = p.get("last_edited_time")
        prev_last = prev_index.get(pid)
        if (not prev_last) or (last and prev_last != last):
            to_update.append(p)

    print(f"총 {len(pages)}개 페이지 중 {len(to_update)}개 변경됨")

    total_new_chunks = 0
    for idx, page in enumerate(to_update):
        pid = page["id"]
        title = page.get("title") or ""
        print(f"  [{idx + 1}/{len(to_update)}] 업데이트 처리: {title or pid}")
        text = loader.get_page_text(pid)
        if not text.strip():
            print("    내용 없음, 건너뜀")
            prev_index[pid] = page.get("last_edited_time")
            continue
        chunks = loader.chunk_text(text, pid, title)
        embeddings = []
        for c in chunks:
            vec = embed_text(c["text"])
            if vec:
                embeddings.append(vec)
            else:
                embeddings.append(None)
        valid = [(c, e) for c, e in zip(chunks, embeddings) if c and e]
        if valid:
            valid_chunks, valid_embeddings = zip(*valid)
            store.add_chunks(list(valid_chunks), list(valid_embeddings))
            total_new_chunks += len(valid_chunks)
        prev_index[pid] = page.get("last_edited_time")

    # save updated index
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(prev_index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"인덱스 저장 실패: {e}")

    print(f"\n✅ 완료! {total_new_chunks}개 새/변경된 청크가 DB에 저장됨")
    return store


def search_mode():
    """대화형 검색 모드"""
    print("\n=== 검색 모드 시작 (종료: 'q') ===")
    rag = RAGSearcher()
    print(f"현재 DB에 {rag.store.count()}개 청크 저장됨\n")

    while True:
        question = input("질문: ").strip()
        if question.lower() in ("q", "quit", "exit"):
            break
        if not question:
            continue
        print("\n생각 중...\n")
        answer = rag.ask(question)
        print(f"답변: {answer}\n")
        print("-" * 50)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-reload":
        reload()
    elif len(sys.argv) > 1 and sys.argv[1] == "-debug":
        # 디버그 모드: 저장된 청크 통계 확인
        store = VectorStore()
        print(f"💾 저장된 청크 총 개수: {store.count()}")
        try:
            all_items = store.collection.get(include=["metadatas"])
            page_chunks = {}
            for meta in all_items.get("metadatas", []):
                page_id = meta.get("page_id")
                if page_id:
                    page_chunks[page_id] = page_chunks.get(page_id, 0) + 1
            print(f"📄 페이지 개수: {len(page_chunks)}")
            if page_chunks:
                print("\n상위 10개 페이지:")
                # get metadata for titles
                sorted_pages = sorted(page_chunks.items(), key=lambda x: x[1], reverse=True)[:10]
                for idx, (page_id, count) in enumerate(sorted_pages):
                    # find first metadata with this page_id to get title
                    title = "?"
                    for meta in all_items.get("metadatas", []):
                        if meta.get("page_id") == page_id:
                            title = meta.get("page_title", "?")
                            break
                    print(f"  [{idx + 1}] {title}: {count}개 청크")
        except Exception as e:
            print(f"진단 실패: {e}")
    elif len(sys.argv) > 2 and sys.argv[1] == "-test":
        # 테스트 모드: 특정 질문으로 검색 결과 확인
        rag = RAGSearcher()
        question = " ".join(sys.argv[2:])
        print(f"질문: {question}\n")
        answer = rag.ask(question, debug=True)
        print(f"\n답변:\n{answer}")
    else:
        search_mode()
