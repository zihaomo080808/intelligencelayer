"""
Validate JavaScript file for common issues
"""
import re
import os

def validate_js_file(file_path):
    """Check JavaScript file for common issues."""
    issues = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for curly brace balance
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            issues.append(f"Unbalanced curly braces: {open_braces} open vs {close_braces} close")
            
        # Check for parenthesis balance
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens != close_parens:
            issues.append(f"Unbalanced parentheses: {open_parens} open vs {close_parens} close")
            
        # Check for bracket balance
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        if open_brackets != close_brackets:
            issues.append(f"Unbalanced brackets: {open_brackets} open vs {close_brackets} close")
            
        # Check for missing semicolons (simple check)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if (line and 
                not line.startswith('//') and 
                not line.endswith('{') and 
                not line.endswith('}') and
                not line.endswith(';') and
                not line.endswith(',') and
                not line.endswith('(') and
                not line.endswith('[') and
                not line.endswith(':') and
                not line.startswith('import') and
                not line.startswith('if') and
                not line.startswith('else') and
                not line.startswith('for') and
                not line.startswith('while') and
                not line.startswith('function')):
                issues.append(f"Line {i+1} might be missing a semicolon: {line}")
                
        return issues
    except Exception as e:
        return [f"Error validating file: {str(e)}"]

if __name__ == "__main__":
    js_file = os.path.join('chat_ui', 'static', 'js', 'chat.js')
    issues = validate_js_file(js_file)
    
    if issues:
        print(f"Found {len(issues)} potential issues:")
        for issue in issues:
            print(f" - {issue}")
    else:
        print("No issues found!")