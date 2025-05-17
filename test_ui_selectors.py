"""
Test script to check if all DOM selectors in chat.js are present in index.html
"""
import re
import os

def extract_dom_selectors(js_content):
    """Extract DOM element selectors from JavaScript code."""
    # Find getElementById calls
    id_selectors = set(re.findall(r'document\.getElementById\([\'"]([^\'"]+)[\'"]\)', js_content))
    
    # Find querySelector calls
    query_selectors = set(re.findall(r'querySelector\([\'"]([^\'"]+)[\'"]\)', js_content))
    
    # Find querySelectorAll calls
    query_all_selectors = set(re.findall(r'querySelectorAll\([\'"]([^\'"]+)[\'"]\)', js_content))
    
    # Find direct element references
    direct_refs = set(re.findall(r'const\s+(\w+)\s*=\s*document\.', js_content))
    
    return {
        'ids': id_selectors,
        'query_selectors': query_selectors,
        'query_all_selectors': query_all_selectors,
        'direct_refs': direct_refs
    }

def check_html_for_selectors(html_content, selectors):
    """Check if selectors are present in HTML content."""
    missing_ids = []
    
    # Check for ids
    for id_selector in selectors['ids']:
        if f'id="{id_selector}"' not in html_content and f"id='{id_selector}'" not in html_content:
            missing_ids.append(id_selector)
    
    # Add more checks for query selectors if needed
    
    return {
        'missing_ids': missing_ids
    }

def validate_ui_selectors():
    """Validate that all selectors in JS exist in HTML."""
    js_path = os.path.join('chat_ui', 'static', 'js', 'chat.js')
    html_path = os.path.join('chat_ui', 'templates', 'index.html')
    
    try:
        with open(js_path, 'r') as f:
            js_content = f.read()
        
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        selectors = extract_dom_selectors(js_content)
        results = check_html_for_selectors(html_content, selectors)
        
        print(f"Found {len(selectors['ids'])} ID selectors in JavaScript")
        
        if results['missing_ids']:
            print(f"WARNING: {len(results['missing_ids'])} IDs referenced in JS are missing from HTML:")
            for id_selector in results['missing_ids']:
                print(f"  - {id_selector}")
        else:
            print("All ID selectors found in HTML. UI should be correctly connected.")
        
        return results
    except Exception as e:
        print(f"Error validating UI selectors: {str(e)}")
        return None

if __name__ == "__main__":
    validate_ui_selectors()