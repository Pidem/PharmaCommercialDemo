import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from tavily import AsyncTavilyClient
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class WebSearch:
    """
    A class to perform concurrent web searches using the Tavily API.

    Attributes:
        output_dir (str): Directory to save search results
        save_search_results (bool): Whether to save search results to files
        tavily_async (AsyncTavilyClient): Async client for Tavily API
    """

    MAX_RESULTS = 5
    SEARCH_TOPIC = "general"

    def __init__(
        self,
        tavily_api_key: str,
        save_search_results: bool = False,
        output_dir: str = "search_results",
    ):
        self.output_dir = output_dir
        self.save_search_results = save_search_results
        self.tavily_async = AsyncTavilyClient(api_key=tavily_api_key)

    async def search(self, search_queries: List[str]) -> List[Dict[str, Any]]:
        """
        Performs concurrent web searches using the Tavily API.

        Args:
            search_queries (List[SearchQuery]): List of search queries to process

        Returns:
                List[dict]: List of search responses from Tavily API, one per query. Each response has format:
                    {
                        'query': str, # The original search query
                        'follow_up_questions': None,
                        'answer': None,
                        'images': list,
                        'results': [                     # List of search results
                            {
                                'title': str,            # Title of the webpage
                                'url': str,              # URL of the result
                                'content': str,          # Summary/snippet of content
                                'score': float,          # Relevance score
                                'raw_content': str|None  # Full page content if available
                            },
                            ...
                        ]
                    }
        """
        if not search_queries:
            raise ValueError("Search queries list cannot be empty")

        if not all(isinstance(query, str) for query in search_queries):
            raise ValueError("All search queries must be strings")

        search_tasks = []
        for query in search_queries:
            search_tasks.append(
                self.tavily_async.search(
                    query,
                    max_results=self.MAX_RESULTS,
                    include_raw_content=True,
                    topic=self.SEARCH_TOPIC,
                )
            )

        # Execute all searches concurrently
        search_docs = await asyncio.gather(*search_tasks)

        unique_docs = self._deduplicate_sources_by_url(search_docs)

        if self.save_search_results:
            await self._save_search_docs(search_docs)

        return unique_docs

    def _deduplicate_sources_by_url(self, search_response) -> List[Dict[str, Any]]:
        # Collect all results
        sources_list = []
        for response in search_response:
            sources_list.extend(response["results"])

        # Deduplicate by URL
        unique_sources = {source["url"]: source for source in sources_list}

        return unique_sources.values()

    async def _save_search_docs(self, search_docs: List[Dict[str, Any]]) -> None:
        """
        Save search results to files in the specified directory.
        Creates one file per search query.

        Args:
            search_docs: List of search results to save
        """
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for docs in search_docs:

                query_hash = hashlib.sha256(docs["query"].encode()).hexdigest()
                file_path = output_path / f"search_{query_hash}.json"

                file_path.write_text(
                    json.dumps(docs, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except Exception as e:
            raise IOError(f"Error saving search results: {str(e)}") from e


@tool
def web_search(query: str) -> str:
    """Search the web for information using Tavily API."""
    print(f"🔧 Tool Called: web_search with query: '{query}'")
    
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if not tavily_api_key:
        return "❌ Error: TAVILY_API_KEY not found in environment variables"
    
    try:
        search_client = WebSearch(tavily_api_key=tavily_api_key)
        results = asyncio.run(search_client.search([query]))
        
        # Format results for the agent
        formatted_results = []
        for result in list(results)[:3]:  # Limit to top 3 results
            formatted_results.append(f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content'][:300]}...")
        
        print(f"✅ Web search completed: {len(formatted_results)} results found")
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        error_msg = f"❌ Error performing web search: {str(e)}"
        print(error_msg)
        return error_msg