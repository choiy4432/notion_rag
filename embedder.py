import time
from google import genai
from google.genai import types
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-2", contents=text, config=types.EmbedContentConfig(task_type=task_type)
            )
            return result.embeddings[0].values
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = 30 * (2**attempt)  # Exponential backoff: 30, 60, 120초
                print(f"  Rate limit 도달. {wait_time}초 대기...")
                time.sleep(wait_time)
            elif "503" in error_str or "unavailable" in error_str.lower():
                wait_time = 10 * (2**attempt)  # 10, 20, 40초
                if attempt < max_retries - 1:
                    print(f"  서버 과부하. {wait_time}초 후 재시도... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"  임베딩 오류 (최대 재시도 초과): {e}")
                    return None
            else:
                print(f"  임베딩 오류: {e}")
                return None
    return None
