import os
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
    
    return True