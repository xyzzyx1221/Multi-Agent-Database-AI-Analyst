import os
from groq import Groq
from dotenv import load_dotenv
from tools.sql_validator import validator

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

class GuardrailAgent:
    """
    The 'Judge' agent. Validates SQL for safety, intent, and cost.
    """
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def validate_sql(self, sql: str, question: str) -> tuple[bool, str]:
        """
        Analyzes the SQL to ensure it matches the user's intent and is safe.
        Returns (is_safe, reasoning/error).
        """
        # 1. Hard-coded tool validation (Syntax & Forbidden Keywords)
        is_valid, error = validator.validate(sql)
        if not is_valid:
            return False, f"Structural Validation Failed: {error}"

        # 2. Hard-coded Write Detection (Crucial for Human-in-the-loop)
        # We check for keywords that modify data. If found, we MUST trigger confirmation.
        upper_sql = sql.upper().strip()
        # Remove markdown code blocks if present (e.g., ```sql ... ```)
        if upper_sql.startswith("```"):
            upper_sql = upper_sql.replace("```SQL", "").replace("```", "").strip()
        
        if any(kw in upper_sql[:20] for kw in ["INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT"]):
            return False, "NEEDS_CONFIRMATION: This is a write operation. Human confirmation required."

        # 3. LLM-based Intent Validation
        # Check if the SQL actually matches what the user asked
        prompt = f"""You are a Senior SQL Security Auditor. Your role is to categorize the provided SQL query into one of three categories based ONLY on its action. You must be extremely strict.

User Question: {question}
SQL: {sql}

### CATEGORIZATION RULES:
1. **SAFE**: The query is a pure READ operation.
   - Queries that start with `SELECT` or `WITH` (CTEs) that end in a `SELECT` are SAFE.
   - If the query only retrieves data without changing any database state, it is SAFE.

2. **NEEDS_CONFIRMATION**: The query is a DATA-MODIFICATION operation.
   - Any query that changes, adds, or removes data. This includes keywords like: `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `UPSERT`, `REPLACE`.
   - Even if the user requested the change, you MUST flag this for human approval.

3. **UNSAFE**: The query is MALICIOUS or DESTRUCTIVE.
   - Queries using `DROP`, `TRUNCATE`, `GRANT`, `REVOKE`, or attempting SQL injection.
   - These are completely forbidden and should be flagged as UNSAFE.

### EXAMPLES:
- "SELECT * FROM customers" -> SAFE
- "WITH summary AS (...) SELECT * FROM summary" -> SAFE
- "UPDATE customers SET tier = 'VIP' WHERE id = 1" -> NEEDS_CONFIRMATION
- "INSERT INTO logs (msg) VALUES ('test')" -> NEEDS_CONFIRMATION
- "DROP TABLE customers" -> UNSAFE
- "TRUNCATE TABLE logs" -> UNSAFE

Response Format:
SAFE: <brief reasoning>
UNSAFE: <brief reasoning>
NEEDS_CONFIRMATION: <brief reasoning>
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        decision = response.choices[0].message.content.strip()
        
        if decision.startswith("UNSAFE"):
            return False, decision
        elif decision.startswith("NEEDS_CONFIRMATION"):
            return False, f"Confirmation Required: {decision}"
        
        return True, "SQL is safe to execute."

# Singleton instance
guardrail_agent = GuardrailAgent()
