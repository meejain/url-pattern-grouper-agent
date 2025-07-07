import anthropic
import json
import pandas as pd
from urllib.parse import urlparse
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Load site-urls.json
with open("site-urls.json") as f:
    raw_data = json.load(f)
    urls = raw_data.get("urls", [])

prompt = os.getenv("PROMPT", "Group URLs by first 2 path segments and assign group if ≥5.")

# Build system prompt
full_context = f"""
You are a helpful Python agent. The variable `urls` is a list of dictionaries with:
- url
- source
- targetPath
- id

User instruction: {prompt}

Respond ONLY with Python code that processes the list `urls`, stores the result in a DataFrame `df`, and optionally saves an Excel file named 'grouped_urls.xlsx'.
"""

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    temperature=0,
    messages=[{"role": "user", "content": full_context}]
)

code = next(block.text for block in response.content if block.type == "text").strip("```python").strip("```").strip()
print("Claude's generated code:\n", code)

# Execute Claude's returned code
exec(code)

# Save result if df exists
local_vars = locals()
if 'df' in local_vars:
    local_vars['df'].to_excel("grouped_urls.xlsx", index=False)
    print("✅ Excel exported: grouped_urls.xlsx")