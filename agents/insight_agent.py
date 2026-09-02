import os
from groq import Groq
from dotenv import load_dotenv
from typing import Any, List, Dict

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

class InsightAgent:
    """
    The 'Analyst' agent. Interprets raw database rows into plain-language insights.
    """
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def generate_insight(self, question: str, results: Any, schema_context: str) -> str:
        """
        Analyzes the data and provides a human-friendly summary and flags anomalies.
        """
        if not results:
            return "I found no data matching your request."

        results_summary = ""
        if isinstance(results, list):
            for i, res in enumerate(results):
                if isinstance(res, dict):
                    results_summary += f"Task {i+1} ({res.get('task', 'Unknown')}): {res.get('result')}\n"
                else:
                    results_summary += f"Result {i+1}: {res}\n"
        else:
            results_summary = str(results)

        prompt = f"""You are a Senior Business Analyst. Your job is to interpret raw database results and provide a clear, concise, and professional answer to the user.

User Question: {question}
Database Results:
{results_summary}
Schema Context: {schema_context}

Guidelines:
1. Factual Accuracy: Base your response strictly on the provided Database Results. Never hallucinate or assume NULLs, missing data, or anomalies if valid data is present.
2. Don't just list the rows. Summarize the key finding clearly.
3. Use currency symbols (e.g., $) for monetary values.
4. **ANOMALY DETECTION**: Only flag an anomaly if there is a genuine data error (e.g., negative totals, extreme outliers, or explicit NULL/error values in the result set). Do not manufacture anomalies.
5. Be direct and avoid fluff.

Response format:
[Insight]: <The plain-language, comprehensive answer addressing all parts of the user question>
[Analysis]: <Any deeper observation or anomaly flagged>
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

# Singleton instance
insight_agent = InsightAgent()
