from google import genai
from google.genai import types
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
        # edit prompt to include guidelines
        prompt = f"""당신은 나의 Notion 개인 비서입니다.
[답변 가이드라인]
1. 먼저 제공된 [Context]에 질문에 대한 명확한 답이 있는지 확인하세요.
2. [Context]에 관련 내용이 있다면, 해당 정보를 바탕으로 답변하세요.
3. 만약 [Context]에 관련 내용이 없거나 부족하다면, "현재 Notion에서 해당 자료를 찾을 수는 없지만, 일반적인 정보(또는 인터넷 정보)를 바탕으로 답변드리겠습니다."라는 멘트를 서두에 반드시 포함하고, 당신이 알고 있는 지식을 활용해 성실하게 답변하세요.

[Context]
{context}

[Question]
{question}"""

        # search_config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite", contents=prompt
        )  # add config=search_config for search tool
        return response.text
