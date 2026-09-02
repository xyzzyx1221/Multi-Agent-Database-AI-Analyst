import os
import matplotlib.pyplot as plt
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from typing import Any, List, Dict, Union

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

class VizReportAgent:
    """
    The 'Presentation' agent. Compiles multiple results into a report and generates charts.
    """
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def generate_report(self, question: str, task_results: List[Dict[str, Any]]) -> str:
        """
        Synthesizes multiple query results into a cohesive final report.
        """
        results_summary = ""
        for i, res in enumerate(task_results):
            results_summary += f"Task {i+1} Result: {res.get('result')}\n"

        prompt = f"""You are a Master Business Reporter. You have gathered multiple pieces of data to answer a complex user request.
Your job is to synthesize these results into a professional, structured executive report.

User Original Request: {question}
Gathered Data:
{results_summary}

Guidelines:
1. Create a structured report with headings (e.g., Executive Summary, Detailed Findings).
2. Do not just list the results; synthesize them into a narrative.
3. Highlight the most important trend or outlier.
4. If there are conflicts between the results, point them out.

Response format:
# Executive Report: <Topic>
## Summary
<Concise summary>
## Key Findings
- <Finding 1>
- <Finding 2>
## Conclusion
<Final thought>
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def generate_chart(self, task_id: int, data: Any, chart_type: str = "bar", filename: str = "chart.png"):
        """
        Simple chart generator. Expects data in a format that can be converted to a DataFrame.
        """
        try:
            if not data or not isinstance(data, list) or len(data) == 0:
                return "Chart generation failed: No data available"

            # Convert result list to DataFrame
            df = pd.DataFrame(data)
            
            # Ensure we have at least 2 columns for a chart
            if df.shape[1] < 2:
                return "Chart generation failed: Not enough columns for visualization"

            plt.figure(figsize=(10, 6))
            if chart_type == "bar":
                plt.bar(df.iloc[:, 0].astype(str), df.iloc[:, 1])
            elif chart_type == "line":
                plt.plot(df.iloc[:, 0].astype(str), df.iloc[:, 1])
            
            plt.title(f"Analysis Result for Task {task_id}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            chart_path = os.path.join("logs/traces", filename)
            plt.savefig(chart_path)
            plt.close('all') # Ensure all figures are closed to avoid corruption
            return chart_path
        except Exception as e:
            return f"Chart generation failed: {str(e)}"

# Singleton instance
viz_report_agent = VizReportAgent()
