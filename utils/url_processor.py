import anthropic
import json
import pandas as pd
from urllib.parse import urlparse
import os
import requests
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import warnings

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def scrape_url_for_content(url, timeout=8):
    """Scrape a URL to detect forms and iframes and gather their information"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        forms = soup.find_all('form')
        iframes = soup.find_all('iframe')
        
        # If neither forms nor iframes found
        if not forms and not iframes:
            return {
                'has_forms': False,
                'form_count': 0,
                'form_types': '',
                'form_details': '',
                'has_iframes': False,
                'iframe_count': 0,
                'iframe_sources': '',
                'iframe_details': '',
                'iframe_forms_count': 0,
                'iframe_with_forms_count': 0,
                'iframe_forms_details': '',
                'status': 'No forms or iframes found'
            }
        
        # Process forms
        form_details = []
        form_types = set()
        
        for form in forms:
            method = form.get('method', 'GET').upper()
            action = form.get('action', '')
            form_id = form.get('id', '')
            form_class = form.get('class', '')
            
            # Count input types
            inputs = form.find_all(['input', 'textarea', 'select'])
            input_types = [inp.get('type', 'text') for inp in form.find_all('input')]
            
            # Determine form type based on inputs and attributes
            if 'search' in str(form).lower() or any('search' in str(inp).lower() for inp in inputs):
                form_types.add('Search')
            elif any(inp_type in ['email', 'password'] for inp_type in input_types):
                form_types.add('Login/Registration')
            elif any(inp_type in ['email'] for inp_type in input_types) and len(inputs) <= 3:
                form_types.add('Newsletter')
            elif len(inputs) >= 4:
                form_types.add('Contact/Lead')
            else:
                form_types.add('Other')
            
            form_detail = f"{method} form"
            if action:
                form_detail += f" (action: {action[:50]}{'...' if len(action) > 50 else ''})"
            if form_id:
                form_detail += f" (id: {form_id})"
            
            form_details.append(form_detail)
        
        # Process iframes and check for forms within them
        iframe_details = []
        iframe_sources = set()
        iframe_forms_found = 0
        iframe_with_forms = []
        
        for iframe in iframes:
            src = iframe.get('src', '')
            iframe_id = iframe.get('id', '')
            title = iframe.get('title', '')
            width = iframe.get('width', '')
            height = iframe.get('height', '')
            
            # Check if iframe URL contains forms
            iframe_has_forms = False
            if src:
                # Normalize URL for iframe scraping
                iframe_url = src
                if src.startswith('//'):
                    iframe_url = 'https:' + src
                elif src.startswith('/'):
                    # Relative URL - construct full URL from main page
                    from urllib.parse import urljoin
                    iframe_url = urljoin(url, src)
                
                # Only scrape iframe if it's a valid HTTP(S) URL and not a data URL
                if iframe_url.startswith(('http://', 'https://')) and 'data:' not in iframe_url:
                    try:
                        # Quick check for forms in iframe (shorter timeout)
                        iframe_response = requests.get(iframe_url, headers=headers, timeout=5, verify=False, allow_redirects=True)
                        iframe_response.raise_for_status()
                        iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                        iframe_forms = iframe_soup.find_all('form')
                        if iframe_forms:
                            iframe_has_forms = True
                            iframe_forms_found += len(iframe_forms)
                            iframe_with_forms.append({
                                'url': iframe_url,
                                'form_count': len(iframe_forms),
                                'iframe_id': iframe_id or 'no-id'
                            })
                    except:
                        # Silently fail if iframe can't be scraped
                        pass
            
            # Categorize iframe sources
            if src:
                if 'youtube' in src.lower() or 'vimeo' in src.lower():
                    iframe_sources.add('Video')
                elif 'google' in src.lower() and 'maps' in src.lower():
                    iframe_sources.add('Maps')
                elif 'facebook' in src.lower() or 'twitter' in src.lower() or 'instagram' in src.lower():
                    iframe_sources.add('Social Media')
                elif 'recaptcha' in src.lower():
                    iframe_sources.add('reCAPTCHA')
                elif src.startswith('//') or src.startswith('http'):
                    iframe_sources.add('External Content')
                else:
                    iframe_sources.add('Internal Content')
            else:
                iframe_sources.add('No Source')
            
            iframe_detail = f"iframe"
            if src:
                iframe_detail += f" (src: {src[:50]}{'...' if len(src) > 50 else ''})"
            if iframe_id:
                iframe_detail += f" (id: {iframe_id})"
            if title:
                iframe_detail += f" (title: {title[:30]}{'...' if len(title) > 30 else ''})"
            if width and height:
                iframe_detail += f" ({width}x{height})"
            if iframe_has_forms:
                iframe_detail += " [FORMS DETECTED]"
            
            iframe_details.append(iframe_detail)
        
        return {
            'has_forms': len(forms) > 0,
            'form_count': len(forms),
            'form_types': ', '.join(sorted(form_types)) if form_types else '',
            'form_details': ' | '.join(form_details) if form_details else '',
            'has_iframes': len(iframes) > 0,
            'iframe_count': len(iframes),
            'iframe_sources': ', '.join(sorted(iframe_sources)) if iframe_sources else '',
            'iframe_details': ' | '.join(iframe_details) if iframe_details else '',
            'iframe_forms_count': iframe_forms_found,
            'iframe_with_forms_count': len(iframe_with_forms),
            'iframe_forms_details': ' | '.join([f"{item['url']} ({item['form_count']} forms)" for item in iframe_with_forms]) if iframe_with_forms else '',
            'status': 'Success'
        }
        
    except requests.exceptions.Timeout:
        return {
            'has_forms': False,
            'form_count': 0,
            'form_types': '',
            'form_details': '',
            'has_iframes': False,
            'iframe_count': 0,
            'iframe_sources': '',
            'iframe_details': '',
            'iframe_forms_count': 0,
            'iframe_with_forms_count': 0,
            'iframe_forms_details': '',
            'status': 'Timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'has_forms': False,
            'form_count': 0,
            'form_types': '',
            'form_details': '',
            'has_iframes': False,
            'iframe_count': 0,
            'iframe_sources': '',
            'iframe_details': '',
            'iframe_forms_count': 0,
            'iframe_with_forms_count': 0,
            'iframe_forms_details': '',
            'status': 'Connection Error'
        }
    except requests.exceptions.HTTPError as e:
        return {
            'has_forms': False,
            'form_count': 0,
            'form_types': '',
            'form_details': '',
            'has_iframes': False,
            'iframe_count': 0,
            'iframe_sources': '',
            'iframe_details': '',
            'iframe_forms_count': 0,
            'iframe_with_forms_count': 0,
            'iframe_forms_details': '',
            'status': f'HTTP {e.response.status_code}'
        }
    except Exception as e:
        return {
            'has_forms': False,
            'form_count': 0,
            'form_types': '',
            'form_details': '',
            'has_iframes': False,
            'iframe_count': 0,
            'iframe_sources': '',
            'iframe_details': '',
            'iframe_forms_count': 0,
            'iframe_with_forms_count': 0,
            'iframe_forms_details': '',
            'status': f'Error: {str(e)[:50]}'
        }

def scrape_urls_for_content(urls, max_workers=3):
    """Scrape multiple URLs for forms and iframes using threading"""
    print(f"🕷️  Starting form and iframe detection for {len(urls)} URLs...")
    print(f"   Using {max_workers} concurrent workers with rate limiting...")
    
    results = {}
    completed = 0
    successful = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scraping tasks
        future_to_url = {executor.submit(scrape_url_for_content, url): url for url in urls}
        
        # Process completed tasks
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results[url] = result
                completed += 1
                
                if result['status'] == 'Success':
                    successful += 1
                
                # Progress update every 25 URLs
                if completed % 25 == 0:
                    success_rate = (successful / completed) * 100
                    print(f"  📊 Progress: {completed}/{len(urls)} URLs ({success_rate:.1f}% success rate)")
                    
                # Rate limiting - small delay between requests
                time.sleep(0.05)
                
            except Exception as e:
                results[url] = {
                    'has_forms': False,
                    'form_count': 0,
                    'form_types': '',
                    'form_details': '',
                    'has_iframes': False,
                    'iframe_count': 0,
                    'iframe_sources': '',
                    'iframe_details': '',
                    'iframe_forms_count': 0,
                    'iframe_with_forms_count': 0,
                    'iframe_forms_details': '',
                    'status': 'Processing Error'
                }
                completed += 1
    
    success_rate = (successful / len(urls)) * 100
    print(f"✅ Form and iframe detection completed!")
    print(f"   📊 Final Results: {completed}/{len(urls)} URLs processed")
    print(f"   📊 Success Rate: {success_rate:.1f}% ({successful} successful)")
    return results

def process_urls(urls, domain):
    # Load inventory.json
    with open("inventory.json") as f:
        inventory = json.load(f)
        blocks = inventory.get("blocks", [])

    # Create initial dataframe
    urls_df = pd.DataFrame(urls)

    # Scrape URLs for form and iframe detection
    content_results = scrape_urls_for_content(urls_df['url'].tolist())
    
    # Add form and iframe detection results to dataframe
    urls_df['has_forms'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('has_forms', False))
    urls_df['form_count'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('form_count', 0))
    urls_df['form_types'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('form_types', ''))
    urls_df['form_details'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('form_details', ''))
    urls_df['has_iframes'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('has_iframes', False))
    urls_df['iframe_count'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_count', 0))
    urls_df['iframe_sources'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_sources', ''))
    urls_df['iframe_details'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_details', ''))
    urls_df['iframe_forms_count'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_forms_count', 0))
    urls_df['iframe_with_forms_count'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_with_forms_count', 0))
    urls_df['iframe_forms_details'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('iframe_forms_details', ''))
    urls_df['scrape_status'] = urls_df['url'].map(lambda x: content_results.get(x, {}).get('status', 'Not processed'))

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

    # Create groups for patterns with 5 or more occurrences, except for locale + filename URLs
    group_mapping = {}
    group_index_mapping = {}  # For numeric sorting
    current_group = 1
    for pattern, count in urls_df['pattern'].value_counts().items():
        if count >= 5 and not (len(pattern.split('/')) == 2 and pattern.split('/')[0].isalpha() and len(pattern.split('/')[0]) == 2):
            print(f"\nCreating Group {current_group} for pattern: {pattern}")
            group_name = f'Group {current_group}'
            group_mapping[pattern] = group_name
            group_index_mapping[group_name] = current_group
            current_group += 1
        else:
            group_mapping[pattern] = ''

    # Assign groups to URLs
    urls_df['group'] = urls_df['pattern'].map(lambda x: group_mapping.get(x, ''))

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

    # Add locale column
    urls_df['locale'] = urls_df['url'].apply(extract_locale)

    # Function to find template details for a URL
    def get_template_details(url):
        template_details = []
        for block in blocks:
            if "instances" in block and block["instances"]:
                for instance in block["instances"]:
                    if "url" in instance and instance["url"] == url:
                        # Use only the name field
                        if "name" in block:
                            name = block["name"]
                            # Skip "unknown" names and avoid duplicates
                            if name != "unknown" and name not in template_details:
                                template_details.append(name)
                        break
        return ', '.join(template_details)

    # Add template details column
    urls_df['template_details'] = urls_df['url'].apply(get_template_details)

    # Group URLs by template details and assign template names
    template_mapping = {}
    template_index_mapping = {}
    current_template = 1
    for details in urls_df['template_details'].unique():
        if details:
            template_name = f'Template {current_template}'
            template_mapping[details] = template_name
            template_index_mapping[template_name] = current_template
            current_template += 1
        else:
            template_mapping[details] = ''

    # Assign template names to URLs
    urls_df['template'] = urls_df['template_details'].map(lambda x: template_mapping.get(x, ''))

    # Create final dataframe with required columns including form and iframe data
    df = urls_df[['url', 'source', 'group', 'locale', 'template', 'template_details', 
                  'has_forms', 'form_count', 'form_types', 'form_details', 
                  'has_iframes', 'iframe_count', 'iframe_sources', 'iframe_details',
                  'iframe_forms_count', 'iframe_with_forms_count', 'iframe_forms_details', 'scrape_status']]

    # Add numeric group index for sorting (999999 for empty groups to put them at end)
    df['group_index'] = df['group'].map(lambda x: group_index_mapping.get(x, 999999))

    # First sort URLs alphabetically within each group
    df = df.sort_values('url', ascending=True)

    # Then sort by group index (1,2,3...) and maintain URL order
    df = df.sort_values(['group_index', 'url'], ascending=[True, True])

    # Remove helper columns but keep form and iframe data
    df = df[['url', 'source', 'group', 'locale', 'template', 'template_details', 
             'has_forms', 'form_count', 'form_types', 'form_details', 
             'has_iframes', 'iframe_count', 'iframe_sources', 'iframe_details',
             'iframe_forms_count', 'iframe_with_forms_count', 'iframe_forms_details', 'scrape_status']]

    # Get domain name from the originUrl
    output_filename = f"amsbasic-{domain}.xlsx"

    # Generate analysis report and get customer folder
    report_filename, customer_folder = generate_analysis_report(df, domain, output_filename)
    
    # Save the Excel result to customer folder
    excel_path = f"{customer_folder}/{output_filename}"
    df.to_excel(excel_path, index=False)
    print(f"✅ Excel exported: {excel_path}")

    return True

def generate_analysis_report(df, domain, output_filename):
    """Generate comprehensive analysis report from the DataFrame"""
    from collections import defaultdict, Counter
    import shutil
    import json
    
    # Read customer name from site-urls.json
    try:
        with open('site-urls.json', 'r') as f:
            site_data = json.load(f)
        customer_name = site_data.get('customerName', 'Unknown Customer')
    except Exception as e:
        print(f"⚠️  Warning: Could not read customer name from site-urls.json: {e}")
        customer_name = "Unknown Customer"
    
    # Create customer folder structure (remove existing if present)
    customer_folder = f"basic_scoping/{customer_name}"
    if os.path.exists(customer_folder):
        shutil.rmtree(customer_folder)
        print(f"🗑️  Removed existing folder: {customer_folder}")
    os.makedirs(customer_folder, exist_ok=True)
    print(f"📁 Created customer folder: {customer_folder}")
    
    # Create report filename in customer folder
    report_filename = f"{customer_folder}/{output_filename.replace('.xlsx', '_analysis.txt')}"
    
    with open(report_filename, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("URL PATTERN GROUPER ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # 1. Main site URL and basic info
        f.write("1. BASIC INFORMATION\n")
        f.write("-" * 50 + "\n")
        f.write(f"Customer: {customer_name}\n")
        f.write(f"Main Site URL: https://{domain}\n")
        f.write(f"Total Pages Analyzed: {len(df)}\n")
        f.write(f"Analysis Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 2. Form and Iframe Analysis
        f.write("2. FORM & IFRAME DETECTION ANALYSIS\n")
        f.write("-" * 50 + "\n")
        content_stats = {
            'total_pages': len(df),
            'pages_with_forms': len(df[df['has_forms'] == True]),
            'pages_without_forms': len(df[df['has_forms'] == False]),
            'pages_with_iframes': len(df[df['has_iframes'] == True]),
            'pages_without_iframes': len(df[df['has_iframes'] == False]),
            'pages_with_iframe_forms': len(df[df['iframe_forms_count'] > 0]),
            'total_iframe_forms': df['iframe_forms_count'].sum(),
            'pages_with_both': len(df[(df['has_forms'] == True) & (df['has_iframes'] == True)]),
            'pages_with_neither': len(df[(df['has_forms'] == False) & (df['has_iframes'] == False)]),
            'successful_scrapes': len(df[df['scrape_status'] == 'Success']),
            'failed_scrapes': len(df[df['scrape_status'] != 'Success'])
        }
        
        f.write(f"Total Pages Scraped: {content_stats['total_pages']}\n")
        f.write(f"Successful Scrapes: {content_stats['successful_scrapes']} ({(content_stats['successful_scrapes']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Failed Scrapes: {content_stats['failed_scrapes']} ({(content_stats['failed_scrapes']/content_stats['total_pages'])*100:.1f}%)\n\n")
        
        f.write("FORM ANALYSIS:\n")
        f.write(f"Pages with Forms: {content_stats['pages_with_forms']} ({(content_stats['pages_with_forms']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Pages without Forms: {content_stats['pages_without_forms']} ({(content_stats['pages_without_forms']/content_stats['total_pages'])*100:.1f}%)\n\n")
        
        f.write("IFRAME ANALYSIS:\n")
        f.write(f"Pages with Iframes: {content_stats['pages_with_iframes']} ({(content_stats['pages_with_iframes']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Pages without Iframes: {content_stats['pages_without_iframes']} ({(content_stats['pages_without_iframes']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Pages with Forms in Iframes: {content_stats['pages_with_iframe_forms']} ({(content_stats['pages_with_iframe_forms']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Total Forms Found in Iframes: {content_stats['total_iframe_forms']}\n\n")
        
        f.write("COMBINED ANALYSIS:\n")
        f.write(f"Pages with Both Forms & Iframes: {content_stats['pages_with_both']} ({(content_stats['pages_with_both']/content_stats['total_pages'])*100:.1f}%)\n")
        f.write(f"Pages with Neither Forms nor Iframes: {content_stats['pages_with_neither']} ({(content_stats['pages_with_neither']/content_stats['total_pages'])*100:.1f}%)\n\n")
        
        # Form type analysis
        if content_stats['pages_with_forms'] > 0:
            form_types_analysis = df[df['has_forms'] == True]['form_types'].value_counts()
            f.write("Form Types Distribution:\n")
            for form_type, count in form_types_analysis.head(10).items():
                if form_type:
                    percentage = (count / content_stats['pages_with_forms']) * 100
                    f.write(f"  {form_type}: {count} pages ({percentage:.1f}%)\n")
            
            # Form count analysis
            form_count_analysis = df[df['has_forms'] == True]['form_count'].value_counts().sort_index()
            f.write(f"\nForms per Page Distribution:\n")
            for count, pages in form_count_analysis.items():
                percentage = (pages / content_stats['pages_with_forms']) * 100
                f.write(f"  {count} form{'s' if count != 1 else ''}: {pages} pages ({percentage:.1f}%)\n")
        
        # Iframe type analysis
        if content_stats['pages_with_iframes'] > 0:
            iframe_sources_analysis = df[df['has_iframes'] == True]['iframe_sources'].value_counts()
            f.write(f"\nIframe Sources Distribution:\n")
            for iframe_source, count in iframe_sources_analysis.head(10).items():
                if iframe_source:
                    percentage = (count / content_stats['pages_with_iframes']) * 100
                    f.write(f"  {iframe_source}: {count} pages ({percentage:.1f}%)\n")
            
            # Iframe count analysis
            iframe_count_analysis = df[df['has_iframes'] == True]['iframe_count'].value_counts().sort_index()
            f.write(f"\nIframes per Page Distribution:\n")
            for count, pages in iframe_count_analysis.items():
                percentage = (pages / content_stats['pages_with_iframes']) * 100
                f.write(f"  {count} iframe{'s' if count != 1 else ''}: {pages} pages ({percentage:.1f}%)\n")
        
        # Scraping status analysis
        status_analysis = df['scrape_status'].value_counts()
        f.write(f"\nScraping Status Breakdown:\n")
        for status, count in status_analysis.items():
            percentage = (count / content_stats['total_pages']) * 100
            f.write(f"  {status}: {count} pages ({percentage:.1f}%)\n")
        f.write("\n")
        
        # 3. Locale Analysis
        f.write("3. LOCALE ANALYSIS\n")
        f.write("-" * 50 + "\n")
        locale_counts = df['locale'].value_counts()
        f.write(f"Total Locales: {len(locale_counts)}\n")
        for locale, count in locale_counts.items():
            percentage = (count / len(df)) * 100
            f.write(f"  {locale.upper()}: {count} pages ({percentage:.1f}%)\n")
        f.write("\n")
        
        # 4. Similar URL Pattern Analysis
        f.write("4. SIMILAR URL PATTERN ANALYSIS\n")
        f.write("-" * 50 + "\n")
        group_counts = df['group'].value_counts()
        grouped_pages = df[df['group'] != '']
        ungrouped_pages = df[df['group'] == '']
        
        f.write(f"Total URL Patterns Created: {len(group_counts) - 1}\n")  # Exclude empty group
        f.write(f"Grouped Pages: {len(grouped_pages)} ({(len(grouped_pages)/len(df))*100:.1f}%)\n")
        f.write(f"Ungrouped Pages: {len(ungrouped_pages)} ({(len(ungrouped_pages)/len(df))*100:.1f}%)\n\n")
        
        # 5. Detailed URL Pattern Analysis with Templates
        f.write("5. DETAILED URL PATTERN BREAKDOWN\n")
        f.write("-" * 50 + "\n")
        
        # Track template combinations across groups
        template_cross_group = defaultdict(list)
        
        for group in group_counts.index:
            if group != '' and group_counts[group] >= 5:  # Only significant groups
                group_data = df[df['group'] == group]
                template_counts = group_data['template'].value_counts()
                template_detail_counts = group_data['template_details'].value_counts()
                
                # Convert "Group 1" to "URL Pattern 1"
                pattern_name = group.replace("Group", "URL Pattern")
                f.write(f"\n{pattern_name}\n")
                f.write(f"  Total Pages: {len(group_data)}\n")
                f.write(f"  Template Groups:\n")
                
                for template, count in template_counts.items():
                    if template != '':
                        f.write(f"    {template}: {count} pages\n")
                        template_cross_group[template].append((group, count))
                
                f.write(f"  Top Template Details:\n")
                for details, count in template_detail_counts.head(3).items():
                    if details and str(details) != 'nan':
                        f.write(f"    \"{details}\": {count} pages\n")
        
        # 6. Cross-Pattern Template Analysis
        f.write("\n\n6. CROSS-PATTERN TEMPLATE ANALYSIS\n")
        f.write("-" * 50 + "\n")
        f.write("Template groups appearing in multiple URL patterns with >5 pages:\n\n")
        
        cross_group_templates = []
        for template, groups in template_cross_group.items():
            if len(groups) > 1:  # Appears in multiple groups
                total_pages = sum(count for _, count in groups)
                if total_pages > 5:
                    cross_group_templates.append((template, groups, total_pages))
        
        if cross_group_templates:
            cross_group_templates.sort(key=lambda x: x[2], reverse=True)
            for template, groups, total_pages in cross_group_templates:
                f.write(f"{template} (Total: {total_pages} pages)\n")
                for group, count in groups:
                    pattern_name = group.replace("Group", "URL Pattern")
                    f.write(f"  - {pattern_name}: {count} pages\n")
                f.write(f"  INSIGHT: Pages with '{template}' template are similar across {len(groups)} URL patterns\n\n")
        else:
            f.write("No significant cross-pattern template patterns found.\n\n")
        
        # 7. Ungrouped Pages Analysis
        f.write("7. UNGROUPED PAGES ANALYSIS\n")
        f.write("-" * 50 + "\n")
        f.write(f"Total Ungrouped Pages: {len(ungrouped_pages)}\n")
        
        if len(ungrouped_pages) > 0:
            ungrouped_templates = ungrouped_pages['template'].value_counts()
            ungrouped_template_details = ungrouped_pages['template_details'].value_counts()
            
            f.write(f"Template Groups in Ungrouped Pages:\n")
            for template, count in ungrouped_templates.items():
                if template != '':
                    f.write(f"  {template}: {count} pages\n")
            
            f.write(f"\nUnique Template Combinations: {len(ungrouped_template_details)}\n")
            f.write(f"Most Common Template Details in Ungrouped Pages:\n")
            for details, count in ungrouped_template_details.head(5).items():
                if details and str(details) != 'nan':
                    f.write(f"  \"{details}\": {count} pages\n")
        
        # 8. Key Insights and Recommendations
        f.write("\n\n8. KEY INSIGHTS & RECOMMENDATIONS\n")
        f.write("-" * 50 + "\n")
        
        # Calculate insights
        grouping_efficiency = (len(grouped_pages) / len(df)) * 100
        avg_group_size = len(grouped_pages) / (len(group_counts) - 1) if len(group_counts) > 1 else 0
        
        f.write(f"• Grouping Efficiency: {grouping_efficiency:.1f}% of pages are grouped\n")
        f.write(f"• Average Group Size: {avg_group_size:.1f} pages per group\n")
        f.write(f"• Template Diversity: {len(df['template'].unique())} unique template types\n")
        f.write(f"• Template Combination Diversity: {len(df['template_details'].unique())} unique combinations\n")
        f.write(f"• Form Coverage: {(content_stats['pages_with_forms']/len(df))*100:.1f}% of pages have forms\n")
        f.write(f"• Iframe Coverage: {(content_stats['pages_with_iframes']/len(df))*100:.1f}% of pages have iframes\n")
        f.write(f"• Iframe Forms Coverage: {(content_stats['pages_with_iframe_forms']/len(df))*100:.1f}% of pages have forms within iframes\n")
        f.write(f"• Total Iframe Forms: {content_stats['total_iframe_forms']} forms found within iframes\n")
        f.write(f"• Scraping Success Rate: {(content_stats['successful_scrapes']/len(df))*100:.1f}%\n\n")
        
        if grouping_efficiency < 50:
            f.write("⚠️  LOW GROUPING EFFICIENCY: Consider lowering the minimum group size threshold\n")
        elif grouping_efficiency > 80:
            f.write("✅ HIGH GROUPING EFFICIENCY: Excellent pattern recognition\n")
        
        if len(cross_group_templates) > 3:
            f.write("🔄 HIGH TEMPLATE OVERLAP: Many similar templates across groups - consider template consolidation\n")
        
        if len(ungrouped_pages) > len(grouped_pages) * 0.5:
            f.write("📊 HIGH UNGROUPED DIVERSITY: Many unique pages - good for content variation analysis\n")
        
        # Most common locales
        primary_locale = locale_counts.index[0]
        f.write(f"🌍 PRIMARY LOCALE: {primary_locale.upper()} ({locale_counts[primary_locale]} pages)\n")
        
        if len(locale_counts) > 1:
            f.write(f"🌐 MULTILINGUAL SITE: {len(locale_counts)} locales detected\n")
        
        # Content-specific insights
        if content_stats['pages_with_forms'] > 0:
            form_conversion_rate = (content_stats['pages_with_forms'] / len(df)) * 100
            if form_conversion_rate > 20:
                f.write(f"📝 HIGH FORM COVERAGE: {form_conversion_rate:.1f}% of pages have forms - excellent for lead generation\n")
            elif form_conversion_rate < 5:
                f.write(f"📝 LOW FORM COVERAGE: Only {form_conversion_rate:.1f}% of pages have forms - consider adding more conversion opportunities\n")
            else:
                f.write(f"📝 MODERATE FORM COVERAGE: {form_conversion_rate:.1f}% of pages have forms\n")
        
        if content_stats['pages_with_iframes'] > 0:
            iframe_coverage_rate = (content_stats['pages_with_iframes'] / len(df)) * 100
            if iframe_coverage_rate > 30:
                f.write(f"🖼️  HIGH IFRAME USAGE: {iframe_coverage_rate:.1f}% of pages have iframes - rich content integration\n")
            elif iframe_coverage_rate < 10:
                f.write(f"🖼️  LOW IFRAME USAGE: Only {iframe_coverage_rate:.1f}% of pages have iframes\n")
            else:
                f.write(f"🖼️  MODERATE IFRAME USAGE: {iframe_coverage_rate:.1f}% of pages have iframes\n")
        
        if content_stats['pages_with_iframe_forms'] > 0:
            iframe_form_rate = (content_stats['pages_with_iframe_forms'] / len(df)) * 100
            if iframe_form_rate > 10:
                f.write(f"📝 HIGH IFRAME FORM USAGE: {iframe_form_rate:.1f}% of pages have forms within iframes - embedded conversion opportunities\n")
            elif iframe_form_rate > 0:
                f.write(f"📝 IFRAME FORMS DETECTED: {iframe_form_rate:.1f}% of pages have forms within iframes ({content_stats['total_iframe_forms']} total forms)\n")
        
        if content_stats['failed_scrapes'] > len(df) * 0.1:
            f.write(f"⚠️  HIGH SCRAPING FAILURE RATE: {(content_stats['failed_scrapes']/len(df))*100:.1f}% failed - check site accessibility\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n")
    
    # Copy source JSON files to customer folder
    try:
        shutil.copy2("site-urls.json", f"{customer_folder}/site-urls.json")
        shutil.copy2("inventory.json", f"{customer_folder}/inventory.json")
        print(f"✅ Source files copied to customer folder")
    except Exception as e:
        print(f"⚠️  Warning: Could not copy source files: {e}")
    
    print(f"✅ Analysis report generated: {report_filename}")
    return report_filename, customer_folder