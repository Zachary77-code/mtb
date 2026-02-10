
import os
import sys

filepath = os.path.join(r'd:\MTB', 'src', 'agents', 'plan_agent.py')

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find insertion point: line with 'if __name__'
insert_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith('if __name__'):
        insert_idx = i
        break

if insert_idx is None:
    print('ERROR: Could not find if __name__ marker')
    sys.exit(1)

print(f'Found if __name__ at line {insert_idx + 1}')

# Read the new methods from a separate file
methods_file = os.path.join(r'd:\MTB', 'temp_new_methods.py')
with open(methods_file, 'r', encoding='utf-8') as f:
    new_methods = f.read()

# Insert before the if __name__ line
new_lines = lines[:insert_idx] + [new_methods + '\n\n'] + lines[insert_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'SUCCESS: Inserted methods before line {insert_idx + 1}')
print(f'New total lines: {len(new_lines)}')
