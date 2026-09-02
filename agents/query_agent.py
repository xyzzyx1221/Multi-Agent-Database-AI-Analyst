import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

class QueryAgent:
    """
    Translates natural language into SQL using provided schema context.
    """
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def generate_sql(self, question: str, schema_context: str) -> str:
        prompt = f"""You are a PostgreSQL expert. Using the provided schema, write a SQL query to answer the user's question.
Return ONLY the SQL query. No explanations, no markdown code blocks.

Rules:
- When asked for entity details (like customer names and emails), always select both the name and email columns (e.g., SELECT c.name, c.email) so the output is identifiable.

Schema:
{schema_context}

Question: {question}
SQL:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

# Singleton instance
query_agent = QueryAgent()
