
import os

file_path = r"e:\Projects\IntelliSense AI\notebook-lm-frontend\src\pages\StudentKnowledgePage.tsx"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Indices (0-based) for lines 550 and 551
idx1 = 549
idx2 = 550

print(f"Line {idx1+1}: {lines[idx1].rstrip()}")
print(f"Line {idx2+1}: {lines[idx2].rstrip()}")

# Check if content matches roughly what we expect
if "upload.error_reason" in lines[idx1] and "</span>" in lines[idx2]:
    print("Found target lines. Removing...")
    del lines[idx2] # Remove higher index first to avoid shifting lower index
    del lines[idx1]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully removed lines.")
else:
    print("Content did not match expectation. Aborting.")
