from google import genai
from embedder import embed_text
from db import VectorStore
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


class RAGSearcher:
    def __init__(self):
        self.store = VectorStore()

    def ask(self, question: str, debug: bool = False) -> str:
        query_vec = embed_text(question, task_type="RETRIEVAL_QUERY")
        if not query_vec:
            return "임베딩 생성에 실패했습니다."

        docs = self.store.search(query_vec)
        if debug:
            print(f"\n[디버그] 저장된 청크: {self.store.count()}개")
            print(f"[디버그] 검색 결과: {len(docs)}개")
            if docs:
                for i, d in enumerate(docs):
                    print(f"  [{i + 1}] {d['page_title']} (유사도: {d['similarity']})")
            else:
                # 모든 결과를 가져와서 왜 필터링되었는지 확인
                all_results = self.store.search(query_vec, all_results=True)
                print(f"[디버그] 임계값 적용 전 결과: {len(all_results)}개")
                if all_results:
                    for i, d in enumerate(all_results[:5]):
                        print(f"  [{i + 1}] {d['page_title']} (유사도: {d['similarity']})")
        if not docs:
            return "관련 문서를 찾지 못했습니다."

        context = "\n\n---\n\n".join([f"[{d['page_title']}] (유사도: {d['similarity']})\n{d['text']}" for d in docs])

        prompt = f"""당신은 나의 Notion 개인 비서입니다.
아래 [Context]를 바탕으로 질문에 답하세요.
모르는 내용은 지어내지 말고 "정보가 부족하여 알 수 없습니다"라고 답하세요.

[Context]
{context}

[Question]
{question}"""

        response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
        return response.text
