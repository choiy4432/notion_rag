import time
from notion_client import Client
import config


class NotionLoader:
    def __init__(self):
        self.client = Client(auth=config.NOTION_API_KEY, timeout_ms=30000)
        self.visited = set()

    @staticmethod
    def _clean_data_source_id(db_id: str) -> str:
        """데이터베이스 ID에서 URL 파라미터(예: ?v=...) 제거"""
        if "?" in db_id:
            return db_id.split("?")[0]
        print(db_id)
        return db_id

    def get_all_pages(self):
        self.visited = set()
        results = []
        cursor = None

        while True:
            resp = self.client.search(
                filter={"property": "object", "value": "page"}, start_cursor=cursor, page_size=100
            )
            for item in resp["results"]:
                pid = item["id"]
                if pid not in self.visited:
                    self.visited.add(pid)
                    results.append(item)
                    self._crawl_children(pid, results)
            if not resp.get("has_more"):
                break
            cursor = resp["next_cursor"]
            time.sleep(0.3)

        return results

    def get_pages_summary(self):
        """Return list of pages with id, title and last_edited_time for incremental checks."""
        pages = self.get_all_pages()
        summary = []
        for p in pages:
            pid = p.get("id")
            title = ""
            if p.get("properties"):
                title_prop = p.get("properties", {}).get("title") or p.get("properties", {}).get("Name")
                if title_prop and title_prop.get("title"):
                    title = "".join([t.get("plain_text", "") for t in title_prop.get("title")])
            # try to get last_edited_time if present, otherwise fetch page object
            last_edited = p.get("last_edited_time")
            if not last_edited and pid:
                try:
                    pg = self.client.pages.retrieve(page_id=pid)
                    last_edited = pg.get("last_edited_time")
                except Exception:
                    last_edited = None
            summary.append({"id": pid, "title": title, "last_edited_time": last_edited})
        return summary

    def _crawl_children(self, block_id, results):
        try:
            cursor = None
            while True:
                resp = self.client.blocks.children.list(block_id=block_id, page_size=100, start_cursor=cursor)
                for block in resp["results"]:
                    btype = block.get("type")
                    if btype == "child_page":
                        pid = block.get("id")
                        if pid not in self.visited:
                            self.visited.add(pid)
                            title = block.get("child_page", {}).get("title", "")
                            results.append(
                                {
                                    "id": pid,
                                    "object": "page",
                                    "properties": {"title": {"title": [{"plain_text": title}]}},
                                }
                            )
                            self._crawl_children(pid, results)
                    elif btype == "link_to_page":
                        pid = block.get("link_to_page", {}).get("page_id")
                        if pid and pid not in self.visited:
                            self.visited.add(pid)
                            results.append(
                                {
                                    "id": pid,
                                    "object": "page",
                                    "properties": {"title": {"title": [{"plain_text": ""}]}},
                                }
                            )
                            self._crawl_children(pid, results)
                    elif btype == "child_database":
                        db_id = block.get("id")  # 이건 database_id
                        if not db_id:
                            continue
                        try:
                            # 1. 데이터베이스 retrieve → data_sources 배열 꺼내기
                            db_obj = self.client.databases.retrieve(database_id=db_id)
                            data_sources = db_obj.get("data_sources", [])

                            if not data_sources:
                                print(f"  DB 스킵: data_sources 없음 ({db_id})")
                                continue

                            # 2. 각 data_source_id로 쿼리
                            for ds in data_sources:
                                ds_id = ds.get("id")
                                if not ds_id:
                                    continue
                                try:
                                    ds_cursor = None
                                    while True:
                                        ds_resp = self.client.data_sources.query(
                                            data_source_id=ds_id, start_cursor=ds_cursor, page_size=100
                                        )
                                        for item in ds_resp.get("results", []):
                                            pid = item.get("id")
                                            if pid and pid not in self.visited:
                                                self.visited.add(pid)
                                                results.append(item)
                                                self._crawl_children(pid, results)
                                        if not ds_resp.get("has_more"):
                                            break
                                        ds_cursor = ds_resp.get("next_cursor")
                                        time.sleep(0.2)
                                except Exception as e:
                                    print(f"  data_source 스킵: {ds_id} ({e})")
                        except Exception as e:
                            print(f"  DB retrieve 스킵: {db_id} ({e})")
                    elif block.get("has_children"):
                        child_id = block.get("id")
                        if child_id:
                            self._crawl_children(child_id, results)
                        else:
                            print(f"  하위 블록 스킵: no id for block type {btype}")
                if not resp.get("has_more"):
                    break
                cursor = resp.get("next_cursor")
                time.sleep(0.2)
        except Exception as exc:
            print(f"  스킵: {block_id} ({exc})")

    def get_page_text(self, page_id, depth=0):
        if depth > 2:
            return ""
        texts = []
        try:
            cursor = None
            while True:
                resp = self.client.blocks.children.list(block_id=page_id, start_cursor=cursor, page_size=100)
                for block in resp["results"]:
                    text = self._extract_text(block)
                    if text:
                        texts.append(text)
                    if block.get("has_children"):
                        child_id = block.get("id")
                        if child_id:
                            time.sleep(0.3)
                            child_text = self.get_page_text(child_id, depth + 1)
                            texts.append(child_text)
                        else:
                            print(f"  하위 텍스트 스킵: no id for block type {block.get('type')}")
                if not resp.get("has_more"):
                    break
                cursor = resp.get("next_cursor")
                time.sleep(0.2)
        except Exception as exc:
            print(f"  스킵: {page_id} ({exc})")
        return "\n".join(texts)

    def _extract_text(self, block):
        block_type = block["type"]
        content = block.get(block_type, {})
        rich_texts = content.get("rich_text", [])
        return "".join([rt.get("plain_text", "") for rt in rich_texts])

    def chunk_text(self, text, page_id, page_title):
        chunks = []
        for i in range(0, len(text), config.CHUNK_SIZE):
            chunk = text[i : i + config.CHUNK_SIZE]
            if chunk.strip():
                chunks.append({"id": f"{page_id}_{i}", "text": chunk, "page_id": page_id, "page_title": page_title})
        return chunks

    def load_all_chunks(self):
        all_chunks = []
        pages = self.get_all_pages()
        print(f"총 {len(pages)}개 페이지 발견")
        for i, page in enumerate(pages):
            page_id = page["id"]
            title_prop = page.get("properties", {}).get("title") or page.get("properties", {}).get("Name", {})
            title = ""
            if title_prop and title_prop.get("title"):
                title = "".join([t["plain_text"] for t in title_prop["title"]])
            print(f"  [{i + 1}/{len(pages)}] 처리 중: {title or page_id}")
            text = self.get_page_text(page_id)
            if text.strip():
                chunks = self.chunk_text(text, page_id, title)
                print(f"    ↳ {len(chunks)}개 청크 생성")
                all_chunks.extend(chunks)
            else:
                print("    ↳ 내용 없음")
            time.sleep(0.4)
        print(f"총 {len(all_chunks)}개 청크 생성 완료")
        return all_chunks
