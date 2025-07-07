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

prompt = """Analyze URLs to find common path patterns and create two sections in the DataFrame:
1. Common Patterns (5 or more URLs):
   - Extract the common URL pattern
   - Count total URLs in that pattern
   - List all URLs that match the pattern
2. Unique/Unmatched URLs:
   - Create a separate group called 'unique_patterns'
   - Include all URLs that don't fit into any common pattern
   - List these URLs with their full paths

Create a DataFrame with columns: 'pattern', 'count', 'urls', 'is_common_pattern'.
Sort common patterns by count in descending order.
Export to Excel with clear formatting."""

# Build system prompt
full_context = f"""
You are a helpful Python agent. The variable `urls` is a list of dictionaries with:
- url
- source
- targetPath
- id

User instruction: {prompt}

IMPORTANT: Respond ONLY with the raw Python code, without any explanations, markdown formatting, or code block markers. The code should process the list `urls`, store the result in a DataFrame `df`, and save an Excel file named 'grouped_urls.xlsx'.
"""

response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1024,
    temperature=0,
    messages=[{"role": "user", "content": full_context}]
)

code = next(block.text for block in response.content if block.type == "text").strip()
print("Claude's generated code:\n", code)

# Execute Claude's returned code
exec(code)

# Save result if df exists
local_vars = locals()
if 'df' in local_vars:
    local_vars['df'].to_excel("grouped_urls.xlsx", index=False)
    print("✅ Excel exported: grouped_urls.xlsx")