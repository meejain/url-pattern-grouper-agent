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

prompt = """Process the URLs with these specific requirements:

1. Create a DataFrame with only two columns:
   - 'url': The complete URL
   - 'group': The group name (e.g., 'Group 1', 'Group 2', etc.) or empty string if no group assigned

2. Grouping Rules:
   - Compare complete URL paths (all segments until the end)
   - If 5 or more URLs share the exact same path pattern, assign them to a group
   - Name groups sequentially: 'Group 1', 'Group 2', etc.
   - URLs without a common pattern (< 5 matches) should have an empty string in the group column

3. Sorting Rules:
   - Homepage (shortest URL) should be at the top
   - Then sort by group (grouped URLs together)
   - Within each group and for ungrouped URLs, maintain alphabetical sorting

Export to Excel with clear formatting."""

# Build system prompt
full_context = f"""
You are a helpful Python agent. The variable `urls` is a list of dictionaries with:
- url
- source
- targetPath
- id

User instruction: {prompt}

IMPORTANT: Respond ONLY with the raw Python code, without any explanations, markdown formatting, or code block markers. The code should:
1. Process the list `urls`
2. Create a DataFrame `df` with exactly two columns: 'url' and 'group'
3. Save the sorted DataFrame to 'grouped_urls.xlsx'
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
    os.makedirs('basic_scoping', exist_ok=True)
    local_vars['df'].to_excel("basic_scoping/grouped_urls.xlsx", index=False)
    print("✅ Excel exported: basic_scoping/grouped_urls.xlsx")