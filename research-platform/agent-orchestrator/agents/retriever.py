# agent-orchestrator/agents/retriever.py
import logging
from typing import Any
from tools.vector_search import search_documents

logger = logging.getLogger(__name__)

def retriever_agent(state: dict) -> dict:
    """Retrieve documents using vector search."""
    try:
        all_chunks = []
        subtasks = state.get('subtasks', [])
        
        if not subtasks:
            logger.warning("No subtasks provided to retriever agent")
            return {'retrieved': []}
        
        for subtask in subtasks[:3]:  # search top 3 subtasks
            try:
                logger.info(f"[Retriever] Searching for: {subtask[:100]}")
                # Invoke tool with proper LangChain signature
                results = search_documents.invoke({
                    'query': subtask,
                    'top_k': 3
                })
                
                if results:
                    all_chunks.extend(results)
                    logger.info(f"[Retriever] Found {len(results)} chunks for subtask")
                else:
                    logger.debug(f"[Retriever] No results for subtask: {subtask}")
                    
            except Exception as e:
                logger.error(f"[Retriever] Error searching for subtask '{subtask}': {str(e)}", exc_info=True)
                # Continue with next subtask on error
                continue
        
        logger.info(f"[Retriever] Total chunks retrieved: {len(all_chunks)}")
        return {'retrieved': all_chunks}
        
    except Exception as e:
        logger.error(f"[Retriever] Unexpected error: {str(e)}", exc_info=True)
        return {'retrieved': [], 'error': str(e)}
