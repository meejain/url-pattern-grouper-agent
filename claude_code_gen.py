import anthropic
import os
import json
from pathlib import Path
import importlib.util
import sys

def generate_code(prompt, context_vars=None):
    """Generate code using Claude."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Read the working implementation from claude_agent.py
    with open('claude_agent.py', 'r') as f:
        claude_agent_code = f.read()
    
    # Build context similar to claude_agent.py
    context_vars_str = ""
    if context_vars:
        context_vars_str = "The variable `urls` is a list of dictionaries with:\n"
        for var_name, var_desc in context_vars.items():
            context_vars_str += f"- {var_name}\n"
    
    full_prompt = f"""
You are a helpful Python agent. {context_vars_str}

I have a working implementation in claude_agent.py that processes URLs correctly. I need you to convert this working code into a proper function format.

Here's the working implementation from claude_agent.py:

{claude_agent_code}

Your task:
1. Extract the core URL processing logic from the claude_agent.py file
2. Convert it into a function called `process_urls(urls, domain)` that:
   - Takes a list of URL dictionaries and domain string as parameters
   - Returns True on success
   - Saves the Excel file as 'basic_scoping/amsbasic-{{domain}}.xlsx'
3. Include all necessary imports at the top
4. Keep the exact same logic for pattern matching, grouping, sorting, and locale detection
5. Make sure to handle the input parameters correctly

IMPORTANT: 
- Use the EXACT same logic from claude_agent.py - don't change the algorithms
- Just wrap it in a function format
- Respond ONLY with the raw Python code, no explanations or markdown
- The function should process the URLs and save to Excel, then return True

User instruction: {prompt}
"""
    
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4000,
        temperature=0,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )
    
    # Extract the actual code content from the message
    content = message.content
    if isinstance(content, list) and len(content) > 0:
        # Get the first text block
        content = content[0].text if hasattr(content[0], 'text') else str(content[0])
    
    # Remove markdown code block markers if present
    if content.startswith('```python'):
        content = content[9:]  # Remove ```python
    if content.startswith('```'):
        content = content[3:]   # Remove ```
    if content.endswith('```'):
        content = content[:-3]  # Remove trailing ```
    
    return content.strip()

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