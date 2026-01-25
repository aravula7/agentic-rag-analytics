"""Router Agent implementation."""

import json
import logging
from typing import Dict, Any
from openai import OpenAI
from .prompts import ROUTER_SYSTEM_PROMPT, USER_QUERY_TEMPLATE

logger = logging.getLogger(__name__)


class RouterAgent:
    """Router Agent for query planning and orchestration."""

    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 500):
        """Initialize Router Agent.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
            max_tokens: Maximum tokens in response
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        logger.info(f"RouterAgent initialized with model: {model}")

    def route(self, query: str) -> Dict[str, Any]:
        """Route a user query and determine execution plan.
        
        Args:
            query: User's natural language query
            
        Returns:
            Dictionary with routing decision:
            {
                "requires_sql": bool,
                "requires_email": bool,
                "tables_involved": list,
                "query_complexity": str,
                "reasoning": str
            }
        """
        logger.info(f"Routing query: {query[:100]}...")

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": USER_QUERY_TEMPLATE.format(query=query)}
                ],
                max_tokens=self.max_tokens,
                temperature=0.0  # Deterministic routing
            )

            # Parse JSON response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json\n", "").replace("\n```", "")
            elif content.startswith("```"):
                content = content.replace("```\n", "").replace("\n```", "")
            
            routing_decision = json.loads(content)
            
            logger.info(f"Routing decision: {routing_decision}")
            return routing_decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse routing response as JSON: {e}")
            # Fallback decision
            return {
                "requires_sql": True,
                "requires_email": False,
                "tables_involved": [],
                "query_complexity": "unknown",
                "reasoning": "Failed to parse routing decision, defaulting to SQL execution"
            }
        except Exception as e:
            logger.error(f"Router Agent error: {e}")
            raise


    def should_execute_sql(self, routing_decision: Dict[str, Any]) -> bool:
        """Check if SQL execution is required.
        
        Args:
            routing_decision: Output from route()
            
        Returns:
            True if SQL should be executed
        """
        return routing_decision.get("requires_sql", False)

    def should_send_email(self, routing_decision: Dict[str, Any]) -> bool:
        """Check if email delivery is required.
        
        Args:
            routing_decision: Output from route()
            
        Returns:
            True if email should be sent
        """
        return routing_decision.get("requires_email", False)