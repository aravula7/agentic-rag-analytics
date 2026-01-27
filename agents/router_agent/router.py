"""Router Agent for query routing decisions."""

import logging
import json
import re
from typing import Dict, Any

from langfuse import observe
from openai import OpenAI

logger = logging.getLogger(__name__)

from .prompts import ROUTER_SYSTEM_PROMPT, USER_QUERY_TEMPLATE


class RouterAgent:
    """Router agent to determine query requirements."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize Router Agent with Langfuse tracing."""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info("RouterAgent initialized with Langfuse tracing")

    @observe(name="router_agent")  # This creates the trace!
    def route(self, query: str) -> Dict[str, Any]:
        """Route query and determine requirements."""
        logger.info(f"Routing query: {query[:100]}...")

        try:
            response = self.client.chat.completions.create(     # type: ignore[call-overload]
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": USER_QUERY_TEMPLATE.format(query=query)}
                ],
                temperature=0.0,
            )

            decision_text = response.choices[0].message.content
            if decision_text is None:
                raise ValueError("Router returned empty response")

            # Strip markdown code blocks if present
            decision_text = re.sub(r'^```json\s*', '', decision_text)
            decision_text = re.sub(r'\s*```$', '', decision_text)
            decision_text = decision_text.strip()
            
            decision = json.loads(decision_text)
            logger.info(f"Routing decision: {decision}")
            return decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse router decision: {e}")
            return {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": [],
                "query_complexity": "simple",
                "reasoning": f"Error parsing decision: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Router error: {e}")
            raise