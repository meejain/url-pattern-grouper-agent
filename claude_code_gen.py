import anthropic
import os
import json
from pathlib import Path

def generate_code(prompt, context_vars=None):
    """Generate code using Claude."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Build context similar to claude_agent.py
    context_vars_str = ""
    if context_vars:
        context_vars_str = "The variable `urls` is a list of dictionaries with:\n"
        for var_name, var_desc in context_vars.items():
            context_vars_str += f"- {var_name}\n"
    
    full_prompt = f"""
You are a helpful Python agent. {context_vars_str}

User instruction: {prompt}

IMPORTANT: Respond ONLY with the raw Python code, without any explanations, markdown formatting, or code block markers. The code should:
1. Process the list `urls`
2. Create a DataFrame `df` with exactly three columns: 'url', 'group', and 'locale'
3. Save the sorted DataFrame to Excel in 'basic_scoping' directory
"""
    
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=4000,
        temperature=0,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )
    
    return message.content

def save_generated_code(code, file_path):
    """Save generated code to a file."""
    # Create directories if they don't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write(code)

def main():
    # Use exact same prompt as claude_agent.py
    context_vars = {
        "url": "The complete URL",
        "source": "Source of the URL",
        "targetPath": "Target path",
        "id": "Unique identifier"
    }
    
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
    
    code = generate_code(prompt, context_vars)
    save_generated_code(code, 'utils/url_processor.py')
    
    print("✅ Code generation completed successfully!")

if __name__ == "__main__":
    main() 