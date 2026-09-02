import os
from groq import Groq
from dotenv import load_dotenv
from typing import Tuple, Optional

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

class ReferenceResolver:
    """
    Analyzes the current question and conversation history to resolve pronouns 
    (e.g., 'their', 'it', 'those') into explicit entities.
    """
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def resolve(self, question: str, history: list) -> Tuple[bool, str]:
        """
        Determines if the question is a follow-up and rewrites it if necessary.
        Also detects if the user has pivoted to a completely different domain.
        Returns (is_follow_up, resolved_question).
        """
        if not history:
            return False, question

        # We take the last 3 turns for context
        recent_context = history[-3:]
        context_str = ""
        for i, turn in enumerate(recent_context):
            context_str += f"Turn {i+1}:\nUser: {turn.get('question')}\nSQL: {turn.get('sql')}\nResult: {turn.get('final_result')}\n\n"

        prompt = f"""You are a Conversation Analyst. Your job is to determine if a user's current question is a follow-up to a previous conversation or a pivot to a new domain.

Conversation History:
{context_str}

Current Question: {question}

Task:
1. If the question is a complete PIVOT to a new domain or a brand new topic, return 'PIVOT | <original_question>'.
2. If the question refers to previous results (using pronouns like 'they', 'their', 'those', 'it', 'that'), rewrite it to be a complete, standalone question and return 'FOLLOW_UP | <rewritten_question>'.
3. If it's a new topic but not necessarily a pivot (just a new query), return 'NEW_TOPIC | <original_//question>'.

Example:
History: User asked for top customers.
Question: "What is the total revenue for 2025?" -> PIVOT | What is the total revenue for 2025?
Question: "What are their emails?" -> FOLLOW_UP | What are the email addresses for the top customers?

Response format:
PIVOT | <original_question>
FOLLOW_UP | <rewritten_question>
NEW_TOPIC | <original_question>
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        answer = response.choices[0].message.content.strip()
        
        if answer.startswith("FOLLOW_UP"):
            resolved = answer.replace("FOLLOW_UP | ", "").strip()
            return True, resolved
        elif answer.startswith("PIVOT"):
            resolved = answer.replace("PIVOT | ", "").strip()
            return False, "PIVOT:" + resolved
        else:
            return False, question

# Singleton instance
reference_resolver = ReferenceResolver()
