# agent-orchestrator/agents/web_search.py
import logging
import os
from typing import Any
from tavily import TavilyClient

logger = logging.getLogger(__name__)

try:
    tavily = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
except Exception as e:
    logger.error(f"Failed to initialize Tavily client: {str(e)}")
    tavily = None

def web_search_agent(state: dict) -> dict:
    """Search the web for research material."""
    try:
        if tavily is None:
            logger.error("Tavily client not initialized")
            return {'web_results': [], 'error': 'Web search unavailable'}
        
        subtasks = state.get('subtasks', [])
        results = []
        
        if not subtasks:
            logger.warning("No subtasks provided to web search agent")
            return {'web_results': []}
        
        for subtask in subtasks[:2]:  # search top 2 subtasks
            try:
                logger.info(f"[WebSearch] Searching for: {subtask[:100]}")
                resp = tavily.search(query=subtask, max_results=3, include_raw_content=False)
                
                search_results = resp.get('results', [])
                for r in search_results:
                    result_str = f"[{r.get('url', 'N/A')}]: {r.get('content', '')}"
                    results.append(result_str)
                
                logger.info(f"[WebSearch] Found {len(search_results)} results for subtask")
                
            except Exception as e:
                logger.error(f"[WebSearch] Error searching for '{subtask}': {str(e)}", exc_info=True)
                # Continue with next subtask on error
                continue
        
        logger.info(f"[WebSearch] Total web results: {len(results)}")
        return {'web_results': results}
        
    except Exception as e:
        logger.error(f"[WebSearch] Unexpected error: {str(e)}", exc_info=True)
        return {'web_results': [], 'error': str(e)}