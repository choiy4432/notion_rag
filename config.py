import os
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHUNK_SIZE = 1000  # 청킹 단위
SIMILARITY_THRESHOLD = 0.2  # 검색 유사도 임계값 (낮을수록 더 많은 결과)
TOP_K = 5  # 상위 K개 결과 반환
