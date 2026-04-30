#!/usr/bin/env python3
"""Remove () from B column and title-case the result, then update cell references."""

import re
import os

SS_PATH = 'C:/Users/ADMINI~1/AppData/Local/Temp/xlsx_b_edit/xl/sharedStrings.xml'
SHEET_PATH = 'C:/Users/ADMINI~1/AppData/Local/Temp/xlsx_b_edit/xl/worksheets/sheet1.xml'
OUT_SS = 'C:/Users/ADMINI~1/AppData/Local/Temp/xlsx_b_edit/xl/sharedStrings.xml'
OUT_SHEET = 'C:/Users/ADMINI~1/AppData/Local/Temp/xlsx_b_edit/xl/worksheets/sheet1.xml'

def title_case(s):
    """Title case: first letter capital, rest lower."""
    if not s:
        return s
    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()

with open(SS_PATH, 'r', encoding='utf-8') as f:
    ss_content = f.read()

with open(SHEET_PATH, 'r', encoding='utf-8') as f:
    sheet_content = f.read()

all_si = re.findall(r'<si>.*?</si>', ss_content, re.DOTALL)

# Find B column cells with (Color) pattern
b_cells = re.findall(r'<c r="B(\d+)" t="s">\s*<v>(\d+)</v>', sheet_content)

updates = []  # (row_num, old_ss_idx, cleaned_text, color)
for row_num, ss_idx in b_cells:
    idx = int(ss_idx)
    if idx < len(all_si):
        t_match = re.search(r'<t[^>]*>([^<]+)</t>', all_si[idx])
        if t_match:
            text = t_match.group(1)
            m = re.search(r'\(([A-Za-z]+)\)\s*$', text)
            if m:
                color = m.group(1)
                cleaned_raw = re.sub(r'\s*\([A-Za-z]+\)\s*$', '', text)
                # Title case
                cleaned = title_case(cleaned_raw)
                updates.append((int(row_num), idx, cleaned, color))

print(f'Cells to update: {len(updates)}')
print()

# Build map of existing strings
text_to_idx = {}
for i, entry in enumerate(all_si):
    t_match = re.search(r'<t[^>]*>([^<]+)</t>', entry)
    if t_match:
        text_to_idx[t_match.group(1)] = i

# Determine new strings to add
new_strings = []
for row, old_idx, cleaned, color in updates:
    if cleaned not in text_to_idx:
        if cleaned not in new_strings:
            new_strings.append(cleaned)

print(f'New strings to add to sharedStrings: {len(new_strings)}')
for s in new_strings:
    print(f'  + "{s}"')
print()

# Build new sharedStrings with new entries appended
# Parse count attribute
count_m = re.search(r'<sst([^>]+)>', ss_content)
sst_attrs = count_m.group(1) if count_m else ''

old_count = re.search(r'uniqueCount="(\d+)"', sst_attrs)
old_unique = int(old_count.group(1)) if old_count else len(all_si)
new_unique = old_unique + len(new_strings)

# Get existing count
count_match = re.search(r'count="(\d+)"', sst_attrs)
old_count_num = int(count_match.group(1)) if count_match else old_unique
new_count = old_count_num + len(new_strings)

# Build new sharedStrings content
new_ss_lines = []
new_ss_lines.append(f'<sst count="{new_count}" uniqueCount="{new_unique}">')
for entry in all_si:
    new_ss_lines.append(entry)
for new_s in new_strings:
    new_ss_lines.append(f'<si><t>{new_s}</t></si>')
new_ss_lines.append('</sst>')
new_ss_content = '\n'.join(new_ss_lines)

# Build index map for new strings
for i, s in enumerate(new_strings):
    text_to_idx[s] = old_unique + i

print(f'Updated uniqueCount: {old_unique} -> {new_unique}')
print()

# Now update sheet XML: for each B cell needing update, replace its <v> with new index
new_sheet_content = sheet_content

# Track replacements
replaced = 0
for row_num, old_idx, cleaned, color in updates:
    new_idx = text_to_idx[cleaned]
    # Pattern: find <c r="B{row_num}" ...><v>{old_idx}</v>
    # We need to find the exact cell in the sheet and update its <v>
    pattern = rf'(<c r="B{row_num}" t="s">\s*<v>)\d+(</v>\s*</c>)'
    m = re.search(pattern, new_sheet_content)
    if m:
        new_sheet_content = re.sub(pattern, rf'\g<1>{new_idx}\g<2>', new_sheet_content)
        replaced += 1
        print(f'Row {row_num}: ss[{old_idx}] -> ss[{new_idx}] ("{cleaned}")')
    else:
        print(f'Row {row_num}: PATTERN NOT FOUND for old_idx {old_idx}')

print()
print(f'Total replacements: {replaced}')

# Write outputs
with open(OUT_SS, 'w', encoding='utf-8') as f:
    f.write(new_ss_content)

with open(OUT_SHEET, 'w', encoding='utf-8') as f:
    f.write(new_sheet_content)

print()
print('Files written.')
