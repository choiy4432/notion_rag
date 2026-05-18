# 📚 Notion RAG — 개인 지식 베이스 검색기

> Notion 페이지 전체를 AI가 읽고, 자연어 질문에 답해주는 개인 AI 비서

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google)](https://aistudio.google.com)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-green)](https://www.trychroma.com)
[![Notion](https://img.shields.io/badge/Source-Notion_API-black?logo=notion)](https://developers.notion.com)

---

## 🧠 Overview

Notion에 저장된 모든 페이지와 데이터베이스를 자동으로 수집하고, **RAG(Retrieval-Augmented Generation)** 파이프라인을 통해 자연어로 검색할 수 있는 개인 지식 베이스입니다.

키워드가 정확히 일치하지 않아도 **의미 기반 검색**으로 관련 정보를 찾아내고, Gemini가 컨텍스트를 바탕으로 자연어 답변을 생성합니다.

---

## 🏗️ Architecture

```
Notion Pages & Databases
        ↓  (Notion API — 재귀 탐색)
   텍스트 추출 + 청킹 (1000자 단위)
        ↓
  Gemini Embedding API (3072차원 벡터)
        ↓
   ChromaDB 로컬 벡터 저장소
        ↓  ← 인덱싱 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   사용자 자연어 질문 입력
        ↓
   질문 → 벡터 변환
        ↓
   코사인 유사도 기반 문서 검색
        ↓
   검색 결과 + 질문 → Gemini LLM
        ↓
   자연어 답변 출력
```

---

## ✨ Features

- **전체 Notion 자동 탐색** — Integration에 연결된 페이지 + 하위 페이지 + 데이터베이스 재귀 수집
- **Notion API 2025-09-03 대응** — `data_sources.query` 방식으로 최신 API 스펙 지원
- **의미 기반 검색** — 키워드 불일치해도 문맥으로 검색 (코사인 유사도)
- **Rate Limit 자동 처리** — Notion / Gemini API 요청 제한 시 자동 재시도
- **로컬 벡터 DB** — ChromaDB로 임베딩 영구 저장, 재실행 시 즉시 검색 가능
- **증분 재로드** — `-reload` 플래그로 필요할 때만 재수집

---

## 🛠️ Tech Stack

| 역할 | 기술 |
|---|---|
| 언어 | Python 3.10+ |
| Notion 수집 | `notion-client` 3.x |
| 임베딩 | Gemini `gemini-embedding-2` (3072차원) |
| LLM | Gemini `gemini-2.5-flash` |
| 벡터 DB | ChromaDB (로컬 영구 저장) |
| API 클라이언트 | `google-genai` |

---

## 🚀 Getting Started

### 1. 레포지토리 클론

```bash
git clone https://github.com/choiy4432/notion_rag.git
cd notion_rag
```

### 2. 가상환경 및 패키지 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. API 키 발급

**Gemini API 키**
1. [Google AI Studio](https://aistudio.google.com) 접속
2. **Get API key → Create API key**

**Notion API 키**
1. [Notion Integrations](https://www.notion.so/profile/integrations) 접속
2. **새 API 통합** 생성 (타입: Internal)
3. 연동할 Notion 페이지에서 `...` → **연결 추가** → 생성한 Integration 선택

### 4. 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```env
NOTION_API_KEY=secret_xxxxx
GEMINI_API_KEY=AIzaxxxxx
```

### 5. 실행

```bash
# 최초 실행 또는 Notion 업데이트 후 (데이터 수집 + 임베딩)
python main.py -reload

# 이후 바로 검색 모드로 시작
python main.py
```

---

## 💬 Usage Example

```
=== 검색 모드 시작 (종료: 'q') ===
현재 DB에 243개 청크 저장됨

질문: 관상 프로젝트에서 사용한 모델이 뭐야?

생각 중...

답변: 관상 프로젝트에서는 MediaPipe, SegFace, Gemini API를 사용했습니다.
얼굴 랜드마크 추출에 MediaPipe, 얼굴 세그멘테이션에 SegFace를 활용했으며,
최종 관상 분석 결과 생성에 Gemini API를 사용했습니다.
XAI 시각화도 포함되어 있어 분석 근거를 시각적으로 확인할 수 있습니다.
```

---

## 📁 Project Structure

```
notion_rag/
├── main.py            # CLI 진입점 (-reload / 검색 모드)
├── notion_loader.py   # Notion 페이지 재귀 수집 + 청킹
├── embedder.py        # Gemini 임베딩 (Rate Limit 자동 처리)
├── db.py              # ChromaDB 벡터 저장 / 검색
├── rag.py             # RAG 파이프라인 (검색 + 프롬프트 + 답변)
├── config.py          # 환경변수 및 파라미터 설정
├── requirements.txt
└── .env               # API 키 (gitignore됨)
```

---

## ⚙️ Configuration

`config.py`에서 파라미터 조정 가능:

```python
CHUNK_SIZE = 1000           # 청킹 단위 (글자 수)
SIMILARITY_THRESHOLD = 0.3  # 검색 유사도 임계값 (낮을수록 더 많이 검색)
TOP_K = 5                   # 상위 몇 개 문서를 컨텍스트로 사용할지
```

---

## 📌 Notes

- Notion Integration을 연결한 페이지와 그 하위 페이지/데이터베이스만 수집됩니다.
- Gemini API 무료 티어 기준으로 동작합니다 (임베딩 1000만 토큰/분, LLM 250회/일).
- 벡터 DB는 `./chroma_db` 폴더에 로컬 저장되며, `-reload` 없이 재실행 시 기존 데이터를 그대로 사용합니다.

---
