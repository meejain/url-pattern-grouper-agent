import anthropic
import json
import pandas as pd
from urllib.parse import urlparse
import os

def process_urls(urls, domain):
    # Load inventory.json
    with open("inventory.json") as f:
        inventory = json.load(f)
        blocks = inventory.get("blocks", [])

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

    # Create final dataframe with required columns
    df = urls_df[['url', 'source', 'group', 'locale', 'template', 'template_details']]

    # Add numeric group index for sorting (999999 for empty groups to put them at end)
    df['group_index'] = df['group'].map(lambda x: group_index_mapping.get(x, 999999))

    # First sort URLs alphabetically within each group
    df = df.sort_values('url', ascending=True)

    # Then sort by group index (1,2,3...) and maintain URL order
    df = df.sort_values(['group_index', 'url'], ascending=[True, True])

    # Remove helper columns
    df = df[['url', 'source', 'group', 'locale', 'template', 'template_details']]

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
        
        # 2. Locale Analysis
        f.write("2. LOCALE ANALYSIS\n")
        f.write("-" * 50 + "\n")
        locale_counts = df['locale'].value_counts()
        f.write(f"Total Locales: {len(locale_counts)}\n")
        for locale, count in locale_counts.items():
            percentage = (count / len(df)) * 100
            f.write(f"  {locale.upper()}: {count} pages ({percentage:.1f}%)\n")
        f.write("\n")
        
        # 3. Similar URL Pattern Analysis
        f.write("3. SIMILAR URL PATTERN ANALYSIS\n")
        f.write("-" * 50 + "\n")
        group_counts = df['group'].value_counts()
        grouped_pages = df[df['group'] != '']
        ungrouped_pages = df[df['group'] == '']
        
        f.write(f"Total URL Patterns Created: {len(group_counts) - 1}\n")  # Exclude empty group
        f.write(f"Grouped Pages: {len(grouped_pages)} ({(len(grouped_pages)/len(df))*100:.1f}%)\n")
        f.write(f"Ungrouped Pages: {len(ungrouped_pages)} ({(len(ungrouped_pages)/len(df))*100:.1f}%)\n\n")
        
        # 4. Detailed URL Pattern Analysis with Templates
        f.write("4. DETAILED URL PATTERN BREAKDOWN\n")
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
        
        # 5. Cross-Pattern Template Analysis
        f.write("\n\n5. CROSS-PATTERN TEMPLATE ANALYSIS\n")
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
        
        # 6. Ungrouped Pages Analysis
        f.write("6. UNGROUPED PAGES ANALYSIS\n")
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
        
        # 7. Key Insights and Recommendations
        f.write("\n\n7. KEY INSIGHTS & RECOMMENDATIONS\n")
        f.write("-" * 50 + "\n")
        
        # Calculate insights
        grouping_efficiency = (len(grouped_pages) / len(df)) * 100
        avg_group_size = len(grouped_pages) / (len(group_counts) - 1) if len(group_counts) > 1 else 0
        
        f.write(f"• Grouping Efficiency: {grouping_efficiency:.1f}% of pages are grouped\n")
        f.write(f"• Average Group Size: {avg_group_size:.1f} pages per group\n")
        f.write(f"• Template Diversity: {len(df['template'].unique())} unique template types\n")
        f.write(f"• Template Combination Diversity: {len(df['template_details'].unique())} unique combinations\n\n")
        
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