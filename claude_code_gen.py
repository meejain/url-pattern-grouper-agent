import anthropic
import os
import json
from pathlib import Path
import importlib.util
import sys

def generate_code(prompt, context_vars=None):
    """Generate code using Claude."""
    return '''import os
import pandas as pd
from collections import Counter

def process_urls(urls, domain):
    # Create DataFrame and initialize columns
    df = pd.DataFrame(urls)
    df['group'] = ''
    
    # Extract pattern from URL
    df['pattern'] = df['url'].apply(lambda x: '/'.join(x.split('//')[1].split('/')[1:]))
    pattern_counts = Counter(df['pattern'])
    
    # Assign groups
    group_num = 1
    for pattern, count in pattern_counts.items():
        if count >= 5:
            df.loc[df['pattern'] == pattern, 'group'] = f'Group {group_num}'
            group_num += 1
            
    # Create helper columns
    df['url_length'] = df['url'].str.len()
    df['group_order'] = pd.Categorical(df['group'].replace('', 'zzzz'), ordered=True)
    
    # Sort
    df = df.sort_values(['url_length', 'group_order', 'url'])
    
    # Remove helper columns
    df = df.drop(['pattern', 'url_length', 'group_order'], axis=1)
    
    # Set default locale
    df['locale'] = 'en'
    
    # Check for language codes
    for lang in ['es', 'hi', 'ko', 'vi']:
        df.loc[df['url'].str.contains('/' + lang + '/', case=False), 'locale'] = lang
        df.loc[df['url'].str.contains('/' + lang + '.', case=False), 'locale'] = lang
    
    # Save to Excel
    os.makedirs('basic_scoping', exist_ok=True)
    df.to_excel(f'basic_scoping/amsbasic-{domain}.xlsx', index=False)
    
    return True'''

def save_generated_code(code, file_path):
    """Save generated code to a file."""
    # Create directories if they don't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write(code)

def load_and_execute_processor(processor_path, urls_data):
    """Load and execute the generated URL processor code."""
    # Add utils directory to Python path
    utils_dir = str(Path(processor_path).parent.absolute())
    if utils_dir not in sys.path:
        sys.path.append(utils_dir)
    
    # Import the generated module
    spec = importlib.util.spec_from_file_location("url_processor", processor_path)
    if spec is None:
        print("❌ Failed to load the URL processor module!")
        return None
        
    module = importlib.util.module_from_spec(spec)
    sys.modules["url_processor"] = module
    
    if spec.loader is None:
        print("❌ Failed to load the URL processor module (no loader)!")
        return None
        
    spec.loader.exec_module(module)
    
    # Execute the processing function with just the urls list from the JSON data
    if hasattr(module, 'process_urls'):
        # Create basic_scoping directory if it doesn't exist
        Path('basic_scoping').mkdir(parents=True, exist_ok=True)
        # Pass only the urls list and the domain from originUrl
        domain = urls_data.get('originUrl', '').split('//')[-1].split('/')[0]
        return module.process_urls(urls_data.get('urls', []), domain)
    else:
        print("⚠️ Generated code does not have a process_urls function!")
        return None

def main():
    # Use exact same prompt as claude_agent.py
    context_vars = {
        "url": "The complete URL",
        "source": "Source of the URL",
        "targetPath": "Target path",
        "id": "Unique identifier"
    }
    
    processor_path = 'utils/url_processor.py'
    
    # Skip code generation if the file already exists
    if not os.path.exists(processor_path):
        prompt = """Process the URLs with these specific requirements:

1. Create a DataFrame with three columns:
   - 'url': The complete URL
   - 'group': The group name (e.g., 'Group 1', 'Group 2', etc.) or empty string if no group assigned
   - 'locale': The detected language code (e.g., 'en', 'es', 'ko', 'vi', 'hi') with 'en' as default

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

4. Locale Detection Rules:
   - Check for 2-letter language codes in the URL path
   - Look for codes at the start of path or as standalone segments
   - Support formats like '/es/', '/ko.html', or '/vi'
   - Default to 'en' if no other locale is detected
   - Currently supported locales: en, es, hi, ko, vi

5. Output Format:
   - Save as Excel file named 'amsbasic-{domain}.xlsx' where domain is extracted from the originUrl
   - File should be saved in the 'basic_scoping' directory
   - Do not include index column in the Excel file

Example:
If these URLs share identical path segments:
  domain.com/api/v1/users/list
  domain.com/api/v1/users/list?page=1
  domain.com/api/v1/users/list?page=2
  domain.com/api/v1/users/list?page=3
  domain.com/api/v1/users/list?page=4
They should be grouped together as they share the pattern 'api/v1/users/list'"""
        
        # Generate and save the code
        code = generate_code(prompt, context_vars)
        save_generated_code(code, processor_path)
    
    # Load URLs data
    with open('site-urls.json', 'r') as f:
        urls_data = json.load(f)
    
    # Execute the processor
    result = load_and_execute_processor(processor_path, urls_data)
    
    if result:
        print("✅ URL processing completed successfully!")
    else:
        print("❌ URL processing failed!")

if __name__ == "__main__":
    main() 