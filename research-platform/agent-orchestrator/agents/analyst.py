# agent-orchestrator/agents/analyst.py
import logging
import os
from typing import Any
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

try:
    llm = ChatGroq(
        model=os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        api_key=os.getenv('GROQ_API_KEY'),
        temperature=0.5,
        max_tokens=2048
    )
except Exception as e:
    logger.error(f"Failed to initialize Groq LLM: {str(e)}")
    llm = None

def analyst_agent(state: dict) -> dict:
    """Analyze research material and extract key findings."""
    try:
        if llm is None:
            logger.error("LLM not initialized")
            return {'findings': [], 'error': 'LLM not available'}
        
        retrieved = state.get('retrieved', [])
        web_results = state.get('web_results', [])
        query = state.get('query', '')
        
        # Combine sources
        all_sources = retrieved + web_results
        context = '\n---\n'.join(all_sources) if all_sources else "No sources found"
        
        logger.info(f"[Analyst] Analyzing {len(all_sources)} sources for query: {query[:100]}")
        
        prompt = f'''Analyze the following research material for the query: {query}
Extract 5-8 key findings. For each, note source and confidence (HIGH/MED/LOW).
Material:
{context[:6000]}
Return findings as a numbered list.'''
        
        response = llm.invoke(prompt)
        
        if response and hasattr(response, 'content'):
            findings = [line.strip() for line in response.content.split('\n') if line.strip()]
            logger.info(f"[Analyst] Extracted {len(findings)} findings")
            return {'findings': findings, 'status': 'analyzed'}
        else:
            logger.warning("[Analyst] Empty response from LLM")
            return {'findings': [], 'status': 'analyzed', 'error': 'Empty LLM response'}
            
    except Exception as e:
        logger.error(f"[Analyst] Error during analysis: {str(e)}", exc_info=True)
        return {'findings': [], 'error': str(e)}