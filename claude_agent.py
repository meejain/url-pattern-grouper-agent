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

# Direct implementation instead of using Claude for code generation
from urllib.parse import urlparse

# Create initial dataframe
urls_df = pd.DataFrame(urls)

# Function to get path segments for grouping
def get_path_segments(url):
    # Remove protocol and www if present
    url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    # Split into domain and path
    parts = url.split('/', 1)
    if len(parts) < 2:
        return ''
    
    path = parts[1].strip('/')
    segments = path.split('/')
    
    if len(segments) > 1:
        # Return all segments except the last one (file name)
        return '/'.join(segments[:-1])
    return path if path else ''

# Create patterns and count them
urls_df['pattern'] = urls_df['url'].apply(get_path_segments)

# Print patterns and their counts for debugging
print("\nPattern counts:")
pattern_counts = urls_df['pattern'].value_counts()
for pattern, count in pattern_counts.items():
    print(f"{pattern}: {count} URLs")

# Create groups for patterns with 5 or more occurrences
group_mapping = {}
current_group = 1
for pattern, count in pattern_counts.items():
    if count >= 5:
        print(f"\nCreating Group {current_group} for pattern: {pattern}")
        group_mapping[pattern] = f'Group {current_group}'
        current_group += 1
    else:
        group_mapping[pattern] = ''

# Assign groups to URLs
urls_df['group'] = urls_df['pattern'].map(lambda x: group_mapping.get(x, ''))

# Create final dataframe with just url and group
df = urls_df[['url', 'group']].copy()

# First sort all URLs alphabetically (A to Z)
df = df.sort_values('url', ascending=True)

# Then sort by group (Group 1, 2, 3..., then ungrouped)
# Maintain alphabetical order within each group
df = df.sort_values(['group', 'url'], ascending=[True, True], na_position='last')

# Final dataframe with just url and group
df = df[['url', 'group']]

# Save the result
os.makedirs('basic_scoping', exist_ok=True)
df.to_excel("basic_scoping/grouped_urls.xlsx", index=False)
print("✅ Excel exported: basic_scoping/grouped_urls.xlsx")