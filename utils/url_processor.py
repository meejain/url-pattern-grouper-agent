import anthropic
import json
import pandas as pd
from urllib.parse import urlparse
import os

def process_urls(urls, domain):
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

    # Create groups for patterns with 5 or more occurrences
    group_mapping = {}
    group_index_mapping = {}  # For numeric sorting
    current_group = 1
    for pattern, count in urls_df['pattern'].value_counts().items():
        if count >= 5:
            group_name = f'Group {current_group}'
            group_mapping[pattern] = group_name
            group_index_mapping[group_name] = current_group
            current_group += 1
        else:
            group_mapping[pattern] = ''

    # Assign groups to URLs
    urls_df['group'] = urls_df['pattern'].map(lambda x: group_mapping.get(x, ''))

    # Create final dataframe with url, source, group
    df = urls_df[['url', 'source', 'group']].copy()

    # Add numeric group index for sorting (999999 for empty groups to put them at end)
    df['group_index'] = df['group'].map(lambda x: group_index_mapping.get(x, 999999))

    # First sort URLs alphabetically within each group
    df = df.sort_values('url', ascending=True)

    # Then sort by group index (1,2,3...) and maintain URL order
    df = df.sort_values(['group_index', 'url'], ascending=[True, True])

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

    # Get domain name from the originUrl
    output_filename = f"amsbasic-{domain}.xlsx"

    # Save the result
    os.makedirs('basic_scoping', exist_ok=True)
    df.to_excel(f"basic_scoping/{output_filename}", index=False)
    print(f"✅ Excel exported: basic_scoping/{output_filename}")
    return True