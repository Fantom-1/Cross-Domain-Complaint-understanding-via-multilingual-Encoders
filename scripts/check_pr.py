import requests
import json

headers = {'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'Mozilla/5.0'}
repo = 'Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders'

# 1. PR details
r_pr = requests.get(f'https://api.github.com/repos/{repo}/pulls/1', headers=headers)
if r_pr.status_code == 200:
    pr_data = r_pr.json()
    print(f"PR #1 Title: {pr_data['title']}")
    print(f"State: {pr_data['state']}, Merged: {pr_data.get('merged')}")
    print(f"Body: {pr_data['body']}")
    print("="*50)

# 2. Issue comments (main conversation comments)
r1 = requests.get(f'https://api.github.com/repos/{repo}/issues/1/comments', headers=headers)
print('=== Issue Comments ===')
if r1.status_code == 200:
    comments = r1.json()
    print(f"Total issue comments: {len(comments)}")
    for c in comments:
        print(f"User: {c['user']['login']} | Created: {c['created_at']}")
        print(c['body'])
        print('-'*40)
else:
    print('Failed to get issue comments:', r1.status_code, r1.text)

# 3. PR Review comments (inline diff comments)
r2 = requests.get(f'https://api.github.com/repos/{repo}/pulls/1/comments', headers=headers)
print('=== Review Comments (Inline) ===')
if r2.status_code == 200:
    inline_comments = r2.json()
    print(f"Total inline review comments: {len(inline_comments)}")
    for c in inline_comments:
        print(f"User: {c['user']['login']} | Path: {c.get('path')} | Line: {c.get('line')}")
        print(c['body'])
        print('-'*40)
else:
    print('Failed to get review comments:', r2.status_code, r2.text)

# 4. PR Reviews list
r3 = requests.get(f'https://api.github.com/repos/{repo}/pulls/1/reviews', headers=headers)
print('=== Reviews ===')
if r3.status_code == 200:
    reviews = r3.json()
    print(f"Total reviews: {len(reviews)}")
    for r in reviews:
        print(f"User: {r['user']['login']} | State: {r['state']} | Submitted: {r.get('submitted_at')}")
        print(r['body'])
        print('-'*40)
else:
    print('Failed to get reviews:', r3.status_code, r3.text)

