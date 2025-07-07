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
group_index_mapping = {}  # For numeric sorting
current_group = 1
for pattern, count in pattern_counts.items():
    if count >= 5:
        print(f"\nCreating Group {current_group} for pattern: {pattern}")
        group_name = f'Group {current_group}'
        group_mapping[pattern] = group_name
        group_index_mapping[group_name] = current_group
        current_group += 1
    else:
        group_mapping[pattern] = ''

# Assign groups to URLs
urls_df['group'] = urls_df['pattern'].map(lambda x: group_mapping.get(x, ''))

# Create final dataframe with url and group
df = urls_df[['url', 'group']].copy()

# Add numeric group index for sorting (999999 for empty groups to put them at end)
df['group_index'] = df['group'].map(lambda x: group_index_mapping.get(x, 999999))

# First sort URLs alphabetically within each group
df = df.sort_values('url', ascending=True)

# Then sort by group index (1,2,3...) and maintain URL order
df = df.sort_values(['group_index', 'url'], ascending=[True, True])

# Remove helper column
df = df[['url', 'group']]

# Function to extract locale from URL
def extract_locale(url):
    # Remove protocol and www if present
    url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    # Split into domain and path
    parts = url.split('/', 1)
    if len(parts) < 2:
        return ''
    
    path = parts[1].strip('/')
    if not path:
        return ''
    
    # Check for 2-letter code at start of path
    # It should be either followed by a slash or a dot
    segments = path.split('/')
    first_segment = segments[0]
    
    # Check if path is exactly 2 letters (URL ends with locale)
    if len(path) == 2 and path.isalpha():
        return path.lower()
    
    # Check if first segment is exactly 2 letters and is followed by / or .
    if len(first_segment) == 2 and first_segment.isalpha():
        return first_segment.lower()
    
    # Also check if it's "xx.html" or similar
    if '.' in first_segment:
        possible_locale = first_segment.split('.')[0]
        if len(possible_locale) == 2 and possible_locale.isalpha():
            # Only count as locale if nothing follows except .html
            if first_segment == f"{possible_locale}.html" and len(segments) == 1:
                return possible_locale.lower()
    
    # Default to "en" if no other locale found
    return 'en'

# Add locale column after sorting is complete
df['locale'] = df['url'].apply(extract_locale)

# Save the result
os.makedirs('basic_scoping', exist_ok=True)
df.to_excel("basic_scoping/grouped_urls.xlsx", index=False)
print("✅ Excel exported: basic_scoping/grouped_urls.xlsx")