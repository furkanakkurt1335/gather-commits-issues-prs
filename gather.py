import requests, os, json

split_date_l = ['2023-02-01', '2023-03-01', '2023-04-01', '2023-05-01', '2023-06-01', '2023-07-01'] # Year-Month-Day

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

repos_path = os.path.join(THIS_DIR, 'repos.json')
if not os.path.exists(repos_path):
    with open(repos_path, 'w') as f:
        json.dump(list(), f)
    print('Please add your repositories to the (just created) `repos.json` file in the following format: "username/repo"')
    exit()
with open(repos_path, 'r') as f:
    repo_l = json.load(f)

data_path = os.path.join(THIS_DIR, 'commits-issues')
if not os.path.exists(data_path):
    os.mkdir(data_path)

tokens_path = os.path.join(THIS_DIR, 'tokens.json')
token = None
if not os.path.exists(tokens_path):
    token_needed = input('Do you need to access private repositories? (y/n): ')
    if token_needed == 'y':
        token = input('Enter your GitHub token: ')
        with open(tokens_path, 'w') as f:
            json.dump({"token": token}, f, ensure_ascii=False, indent=4)
else:
    with open(tokens_path, 'r') as f:
        token = json.load(f)['token']
headers = { 'Accept': 'application/vnd.github.v3+json' }
if token:
    headers['Authorization'] = 'Bearer {}'.format(token)

for tuple_t in repo_l:
    user_t, repo_t = tuple_t.split('/')
    ms_d = dict()
    for i in range(1, len(split_date_l)):
        ms_d[i] = { 'date': split_date_l[i-1], 'commits': dict(), 'issues': dict() }
    repo_url = 'https://api.github.com/repos/%s/%s' % (user_t, repo_t)
    repo_req = requests.get(repo_url, headers=headers)
    repo_res = repo_req.json()
    if 'message' in repo_res.keys() and repo_res['message'] == 'Not Found':
        continue
    page_n = 1
    while 1:
        commit_url = 'https://api.github.com/repos/%s/%s/commits?page=%s' % (user_t, repo_t, page_n)
        com_req = requests.get(commit_url, headers=headers)
        commits = com_req.json()
        if len(commits) == 0:
            break
        for commit in commits:
            date_t = commit['commit']['author']['date']
            if 'author' in commit.keys() and type(commit['author']) == dict and 'login' in commit['author'].keys():
                author_t = commit['author']['login']
            elif 'commit' in commit.keys() and type(commit['commit']) == dict and 'author' in commit['commit'].keys() and type(commit['commit']['author']) == dict and 'name' in commit['commit']['author'].keys():
                author_t = commit['commit']['author']['name']
            else:
                author_t = 'unknown'
            message_t = commit['commit']['message']
            for i in range(1, len(split_date_l)):
                ms_date = split_date_l[i]
                if date_t < ms_date:
                    if author_t not in ms_d[i]['commits'].keys():
                        ms_d[i]['commits'][author_t] = { 'messages': list(), 'count': 0 }
                    ms_d[i]['commits'][author_t]['messages'].append(message_t)
                    ms_d[i]['commits'][author_t]['count'] += 1
                    break
        page_n += 1
    page_n = 1
    while 1:
        issue_url = 'https://api.github.com/repos/%s/%s/issues?state=all&page=%s' % (user_t, repo_t, page_n)
        iss_req = requests.get(issue_url, headers=headers)
        issues = iss_req.json()
        if len(issues) == 0:
            break
        for issue in issues:
            date_t = issue['created_at']
            title_t = issue['title']
            desc_t = issue['body']
            label_cnt = len(issue['labels'])
            assignee_cnt = len(issue['assignees'])
            author_t = issue['user']['login']
            comments = list()
            if issue['comments']:
                comments_url = issue['comments_url']
                comments_req = requests.get(comments_url, headers=headers)
                comments_res = comments_req.json()
                for comment in comments_res:
                    comments.append( { 'author': comment['user']['login'], 'body': comment['body'] } )
            for i in range(1, len(split_date_l)):
                ms_date = split_date_l[i]
                if date_t < ms_date:
                    if author_t not in ms_d[i]['issues'].keys():
                        ms_d[i]['issues'][author_t] = { 'list': list(), 'count': 0 }
                    ms_d[i]['issues'][author_t]['list'].append({ 'title': title_t, 'desc': desc_t, 'label_count': label_cnt, 'comments': comments, 'assignee_count': assignee_cnt })
                    ms_d[i]['issues'][author_t]['count'] += 1
                    break
        page_n += 1
    with open(os.path.join(data_path, '%s-%s.json' % (user_t, repo_t)), 'w') as f:
        json.dump(ms_d, f, ensure_ascii=False, indent=4)
