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

I have a working implementation in claude_agent.py that processes URLs correctly. I need you to create a comprehensive URL processing function that includes advanced form and iframe detection.

Here's the working implementation from claude_agent.py:

{claude_agent_code}

Your task:
1. Create a function called `process_urls(urls, domain)` that:
   - Takes a list of URL dictionaries and domain string as parameters
   - Returns True on success
   - Implements comprehensive form and iframe detection with multithreading
   - Creates customer folder structure dynamically
   - Generates both Excel output and detailed analysis report
   - Copies source files to customer folder

2. Include all necessary imports:
   - requests, beautifulsoup4 for web scraping
   - concurrent.futures for multithreading
   - urllib3, warnings for SSL handling
   - pandas, json, os, shutil for data processing
   - pathlib for file operations

3. Core functionality requirements:
   - URL pattern matching and grouping (5+ URLs with same pattern)
   - Template identification from inventory.json using block names
   - Locale detection (en, es, hi, ko, vi)
   - Form detection and categorization
   - Iframe detection (only those containing forms)
   - Multithreaded scraping with proper error handling
   - Comprehensive analysis report generation

4. Advanced scraping capabilities:
   - Detect and categorize forms: Search, Login/Registration, Newsletter, Contact/Lead, Other
   - Detect iframes but only track those containing forms
   - Check iframe source URLs for form content
   - Categorize iframe sources: Video, Maps, Social Media, reCAPTCHA, External Content, Internal Content
   - Handle SSL warnings and connection errors gracefully
   - Use ThreadPoolExecutor with max 5 concurrent workers

5. Dynamic customer folder structure:
   - Read customerName from site-urls.json
   - Create basic_scoping/{{customerName}}/ folder
   - Remove existing customer folder if exists
   - Save all outputs to customer folder

6. Output requirements:
   - Excel file with 18 columns including form/iframe data
   - Comprehensive analysis report with insights
   - Copy source JSON files to customer folder
   - Progress tracking during scraping

IMPORTANT MODIFICATIONS FROM OLD VERSION:
- Use block["name"] field for template_details, filter out "unknown" names
- Only track iframes that contain forms - ignore all other iframes
- Generate both Excel and comprehensive analysis report
- Create dynamic customer folder structure
- Handle errors gracefully with proper status tracking
- Suppress SSL warnings for scraping

CRITICAL FIXES:
- Use `df['url'].apply(extract_locale)` NOT `df[['url']].apply(extract_locale, axis=1)`
- The extract_locale function should receive a single URL string, not a DataFrame row
- Make sure to remove helper columns like 'group_index' before saving to Excel

IMPORTANT: 
- Respond ONLY with the raw Python code, no explanations or markdown
- The function should process URLs, scrape content, and generate comprehensive outputs
- Include proper error handling and progress tracking
- Use the exact DataFrame column structure as specified in the requirements

User instruction: {prompt}
"""
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8000,
        temperature=0,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )
    
    # Extract the actual code content from the message
    content = message.content
    if isinstance(content, list) and len(content) > 0:
        # Get the first text block that has text content
        for block in content:
            try:
                content = block.text
                break
            except AttributeError:
                continue
        else:
            content = str(content[0])
    
    # Ensure content is a string
    if not isinstance(content, str):
        content = str(content)
    
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
        "id": "Unique identifier",
        "template": "Template name based on block instances (e.g., 'Template 1', 'Template 2', etc.)",
        "template_details": "Comma-separated list of all block target values where this URL appears as an instance",
        "has_forms": "Boolean indicating if the page contains forms",
        "form_count": "Number of forms found on the page", 
        "form_types": "Types of forms found (Search, Login/Registration, Newsletter, Contact/Lead, Other)",
        "form_details": "Detailed information about each form found",
        "has_iframes": "Boolean indicating if the page contains iframes with forms",
        "iframe_count": "Number of iframes containing forms",
        "iframe_sources": "Types of iframe sources (Video, Maps, Social Media, reCAPTCHA, External Content, Internal Content)",
        "iframe_details": "Detailed information about each iframe containing forms",
        "iframe_forms_count": "Total number of forms found within iframes",
        "iframe_with_forms_count": "Number of iframes that contain forms",
        "iframe_forms_details": "Detailed information about forms found within iframes",
        "scrape_status": "Status of the scraping attempt (Success, Timeout, Error, etc.)"
    }
    
    processor_path = 'utils/url_processor.py'
    
    # Skip code generation if the file already exists
    if not os.path.exists(processor_path):
        prompt = """Process the URLs with these comprehensive requirements:

1. DEPENDENCIES AND SETUP:
   - Import required libraries: requests, beautifulsoup4, pandas, json, os, urllib3, warnings
   - Import concurrent.futures for multithreading
   - Suppress SSL warnings: urllib3.disable_warnings() and warnings.filterwarnings('ignore')
   - Create customer folder structure based on customerName from site-urls.json
   - Use shutil for file operations

2. FORM AND IFRAME DETECTION:
   - Scrape each URL to detect forms and iframes using multithreaded approach (5 concurrent workers)
   - Use proper headers and error handling with timeouts
   - FORM DETECTION: Find all <form> elements and categorize them:
     * Search: forms with search-related inputs
     * Login/Registration: forms with email/password inputs
     * Newsletter: forms with email input and ≤3 total inputs
     * Contact/Lead: forms with ≥4 inputs
     * Other: all other forms
   - IFRAME DETECTION: Find all <iframe> elements but ONLY track those containing forms
     * Scrape each iframe's src URL to check for forms
     * Only count/categorize iframes that have forms in their content
     * Categorize iframe sources: Video, Maps, Social Media, reCAPTCHA, External Content, Internal Content
     * Track forms found within iframes separately

3. DATAFRAME CREATION:
   Create a DataFrame with these columns (in order):
   - 'url': The complete URL
   - 'source': Source of the URL (from the source field)
   - 'group': The group name (e.g., 'Group 1', 'Group 2', etc.) or empty string if no group assigned
   - 'locale': The detected language code (e.g., 'en', 'es', 'ko', 'vi', 'hi') with 'en' as default
   - 'template': Template name based on block instances (e.g., 'Template 1', 'Template 2', etc.)
   - 'template_details': Comma-separated list of all block names where this URL appears as an instance
   - 'has_forms': Boolean indicating if the page contains forms
   - 'form_count': Number of forms found on the page
   - 'form_types': Types of forms found (comma-separated)
   - 'form_details': Detailed information about each form found
   - 'has_iframes': Boolean indicating if the page contains iframes with forms
   - 'iframe_count': Number of iframes containing forms
   - 'iframe_sources': Types of iframe sources (comma-separated)
   - 'iframe_details': Detailed information about each iframe containing forms
   - 'iframe_forms_count': Total number of forms found within iframes
   - 'iframe_with_forms_count': Number of iframes that contain forms
   - 'iframe_forms_details': Detailed information about forms found within iframes
   - 'scrape_status': Status of the scraping attempt (Success, Timeout, Error, etc.)

4. PATTERN MATCHING AND GROUPING RULES:
   - Split each URL into path segments (parts between slashes)
   - For each URL, create its pattern by joining all its path segments
   - Count how many URLs share each pattern
   - SPECIAL RULE: URLs with locale + filename pattern should NOT be grouped
     * If first segment is exactly 2 letters AND there are only 2 segments total (e.g., /fr/espace-medias)
     * Return unique identifier to prevent grouping these URLs
     * This prevents locale + filename URLs from being grouped together
   - When 5 or more URLs have identical path segments (ignoring protocol and domain):
     * Create a new group named 'Group N' (where N increments for each group)
     * Assign all matching URLs to this group
   - URLs that don't have 5 or more matches should have an empty string as their group

5. TEMPLATE IDENTIFICATION RULES:
   - Load the inventory.json file which contains a "blocks" section
   - Each block has an "instances" array containing objects with "url" field
   - Each block has a "name" field (use this for template_details, NOT "target")
   - Filter out blocks with name "unknown"
   - For each URL in the dataset:
     * Find all blocks where this URL appears in the "instances" array
     * Collect the "name" field values of all such blocks (excluding "unknown")
     * Store these names as comma-separated string in 'template_details' column
     * Group URLs that have the same set of names into templates
     * Assign template names like 'Template 1', 'Template 2', etc.
     * URLs with the same combination of names get the same template name
   - This identifies URLs with similar layouts/structure

6. SORTING RULES:
   - Homepage (shortest URL) at the top
   - Then group all URLs with assigned groups together
   - Within each group and for ungrouped URLs, sort alphabetically

7. LOCALE DETECTION RULES:
   - Check for 2-letter language codes in the URL path
   - Look for codes at the start of path or as standalone segments
   - Support formats like '/es/', '/ko.html', or '/vi'
   - Default to 'en' if no other locale is detected
   - Currently supported locales: en, es, hi, ko, vi

8. CUSTOMER FOLDER STRUCTURE:
   - Read customerName from site-urls.json dynamically
   - Create folder: basic_scoping/{customerName}/
   - Remove existing customer folder if it exists
   - Save all outputs to customer folder

9. OUTPUT FORMAT:
   - Save as Excel file named 'amsbasic-{domain}.xlsx' in customer folder
   - Generate comprehensive analysis report as '{domain}_analysis_report.txt' in customer folder
   - Copy source files (site-urls.json, inventory.json) to customer folder
   - Analysis report should include:
     * Site information and page counts
     * Form and iframe detection analysis (only iframes with forms)
     * Locale analysis breakdown
     * URL pattern analysis with template details
     * Cross-pattern template analysis
     * Ungrouped pages analysis
     * Key insights and recommendations
   - Do not include index column in the Excel file

10. MULTITHREADING AND PERFORMANCE:
    - Use ThreadPoolExecutor with max 5 concurrent workers for URL scraping
    - Implement proper error handling and timeouts
    - Show progress during scraping
    - Handle SSL/certificate errors gracefully

CRITICAL REQUIREMENTS:
- Use block["name"] field for template_details, filter out "unknown" names
- Only track iframes that contain forms - ignore all other iframes
- Use proper multithreading for URL scraping
- Generate both Excel and comprehensive analysis report
- Create dynamic customer folder structure
- Handle errors gracefully with proper status tracking
- Suppress SSL warnings for scraping"""
        
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