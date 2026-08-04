import logging
import urllib.parse
import urllib.request
import json
import gzip
import re
from html import unescape
from typing import Dict, Any, List
from src.tools.base import BaseTool
from src.config import settings

logger = logging.getLogger("blaine.tools.web_search")

class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Searches the web for real-time information, news, weather forecasts, live facts, or technical documentation."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (e.g. 'Weather in London today', 'Glendale Arizona information', 'Raspberry Pi 5 specs')."
                }
            },
            "required": ["query"]
        }

    def _search_brave(self, query: str, api_key: str) -> List[Dict[str, str]]:
        url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
                "User-Agent": "BlaineAssistant/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                content = gzip.decompress(content)
            data = json.loads(content.decode("utf-8"))

        web_results = data.get("web", {}).get("results", [])
        results = []
        for item in web_results:
            title = item.get("title", "")
            snippet = item.get("description", "")
            url_link = item.get("url", "")
            if title and snippet:
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url_link
                })
        return results

    def _keyless_fallback(self, query: str) -> List[Dict[str, str]]:
        results = []

        # 1. Wikipedia Search API
        try:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(
                wiki_url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("query", {}).get("search", [])[:3]:
                title = item.get("title", "")
                snippet = unescape(re.sub(r"<[^>]+>", "", item.get("snippet", ""))).strip()
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                if title and snippet:
                    results.append({"title": title, "snippet": snippet, "url": page_url})
        except Exception as e:
            logger.debug(f"Wikipedia fallback search error: {e}")

        # 2. DuckDuckGo Instant Answer API
        try:
            ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(ddg_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            abstract = data.get("AbstractText", "")
            heading = data.get("Heading", "")
            abstract_url = data.get("AbstractURL", "")
            if abstract and heading:
                results.insert(0, {"title": heading, "snippet": abstract, "url": abstract_url})
        except Exception as e:
            logger.debug(f"DuckDuckGo fallback search error: {e}")

        return results

    async def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "").strip()
        if not query:
            return {"status": "ERROR", "message": "No query provided."}

        logger.info(f"Executing WebSearchTool for query: '{query}'")

        results = []
        source = "brave"

        # Step 1: Use Brave Search API if BRAVE_API_KEY is configured
        if settings.BRAVE_API_KEY:
            try:
                results = self._search_brave(query, settings.BRAVE_API_KEY)
            except Exception as e:
                logger.error(f"Brave Search API error: {e}. Falling back to keyless search.")
                source = "keyless_fallback"

        # Step 2: Keyless Fallback if no BRAVE_API_KEY or if Brave fails
        if not results:
            source = "keyless_fallback" if settings.BRAVE_API_KEY else "keyless"
            results = self._keyless_fallback(query)

        if not results:
            return {
                "status": "SUCCESS",
                "query": query,
                "summary": f"No web search results found for '{query}'.",
                "results": []
            }

        # Build readable summary string for LLM context
        summary_lines = []
        for i, r in enumerate(results[:5], 1):
            url_part = f" ({r['url']})" if r.get("url") else ""
            summary_lines.append(f"{i}. {r['title']}{url_part}\n   {r['snippet']}")

        summary_text = "\n\n".join(summary_lines)

        return {
            "status": "SUCCESS",
            "query": query,
            "source": source,
            "results": results[:5],
            "summary": summary_text
        }