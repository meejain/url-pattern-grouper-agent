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

2. Pattern Matching and Grouping Rules:
   - Split each URL into path segments (parts between slashes)
   - For each URL, create its pattern by joining all its path segments
   - Count how many URLs share each pattern
   - When 5 or more URLs have identical path segments (ignoring protocol and domain):
     * Create a new group named 'Group N' (where N increments for each group)
     * Assign all matching URLs to this group
   - URLs that don't have 5 or more matches should have an empty string as their group

3. Sorting Rules:
   - Homepage (shortest URL) at the top
   - Then group all URLs with assigned groups together
   - Within each group and for ungrouped URLs, sort alphabetically

Example:
If these URLs share identical path segments:
  domain.com/api/v1/users/list
  domain.com/api/v1/users/list?page=1
  domain.com/api/v1/users/list?page=2
  domain.com/api/v1/users/list?page=3
  domain.com/api/v1/users/list?page=4
They should be grouped together as they share the pattern 'api/v1/users/list'

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