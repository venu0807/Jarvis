import re

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'r') as f:
    lines = f.readlines()

# Fix broken f-string concatenations by joining consecutive f-string lines
# The pattern is:
# message=f"...\n"
#         f"...\n"
#         ...
#         f"...",
# We need to wrap in parentheses and use {NL} for newlines

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this line starts a broken f-string message block
    if 'message=f"' in line and line.strip().startswith('message=f"'):
        # Found the start of a broken f-string block
        # Collect all consecutive f-string lines
        block_lines = [line]
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            # Check if it's a continuation f-string line (indented, starts with f")
            if next_line.strip().startswith('f"') and next_line.strip().endswith('",') or \
               next_line.strip().startswith('f"') and next_line.strip().endswith('"') or \
               next_line.strip().startswith("'") and next_line.strip().endswith("',") or \
               next_line.strip().startswith("'") and next_line.strip().endswith("'"):
                block_lines.append(next_line)
                j += 1
            else:
                break
        
        # Now rebuild the block properly
        # Extract the indentation
        indent = len(line) - len(line.lstrip())
        base_indent = ' ' * indent
        inner_indent = ' ' * (indent + 4)
        
        # Build the fixed block
        fixed_block = [base_indent + 'message=(']
        
        for bl in block_lines:
            stripped = bl.strip()
            # Remove leading 'f"' or '"' or "'"
            if stripped.startswith('f"'):
                content = stripped[2:]
            elif stripped.startswith('"'):
                content = stripped[1:]
            elif stripped.startswith("'"):
                content = stripped[1:]
            else:
                content = stripped
            
            # Remove trailing '",' or '"' or "'," or "'"
            if content.endswith('",'):
                content = content[:-2]
            elif content.endswith('"'):
                content = content[:-1]
            elif content.endswith("',"):
                content = content[:-2]
            elif content.endswith("'"):
                content = content[:-1]
            
            # Replace literal \n with {NL}
            content = content.replace('\\n', '{NL}')
            
            # Determine if it's an f-string (contains {})
            if '{' in content and '}' in content:
                fixed_block.append(inner_indent + f'f"{content}"')
            else:
                fixed_block.append(inner_indent + f'"{content}"')
        
        fixed_block.append(base_indent + '),')
        new_lines.extend(fixed_block)
        i = j
    else:
        new_lines.append(line)
        i += 1

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed all broken f-string blocks using line-by-line parser')