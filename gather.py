import requests, os, json, argparse, re
from pathlib import Path
from datetime import datetime

def get_args():
    parser = argparse.ArgumentParser(description='Gather commits and issues from GitHub repositories')
    parser.add_argument('-t', '--token', help='GitHub token path', type=str, default='token.json')
    parser.add_argument('-r', '--repos', help='Path to the JSON file with the repositories', type=str, default='repos.json')
    parser.add_argument('-d', '--date', help='Path to the JSON file with the dates', type=str, default='dates.json')
    parser.add_argument('-o', '--output', help='Path to the output directory', type=str, default='commits-issues')
    return parser.parse_args()

def main():
    args = get_args()

    coauthor_pattern = re.compile(r'Co-authored-by: (.*) <.*>')

    ms_dates = [
        {'year': 2024, 'month': 3, 'day': 19, 'hour': 22, 'minute': 0, 'second': 0},
        {'year': 2024, 'month': 4, 'day': 30, 'hour': 22, 'minute': 0, 'second': 0},
        {'year': 2024, 'month': 5, 'day': 17, 'hour': 22, 'minute': 0, 'second': 0}
    ]
    for i, date in enumerate(ms_dates):
        year, month, day, hour, minute, second = date['year'], date['month'], date['day'], date['hour'], date['minute'], date['second']
        ms_dates[i]['year'] = f'{year:04d}'
        ms_dates[i]['month'] = f'{month:02d}'
        ms_dates[i]['day'] = f'{day:02d}'
        ms_dates[i]['hour'] = f'{hour:02d}'
        ms_dates[i]['minute'] = f'{minute:02d}'
        ms_dates[i]['second'] = f'{second:02d}'
    ms_dates = [datetime.fromisoformat('%s-%s-%sT%s:%s:%s+00:00' % (date['year'], date['month'], date['day'], date['hour'], date['minute'], date['second'])) for date in ms_dates]

    repos_path = Path(args.repos)
    if not repos_path.exists():
        with repos_path.open('w') as f:
            json.dump([], f)
        print('Please add your repositories to the (just created) `repos.json` file in the following format: "username/repo"')
        exit()
    with repos_path.open() as f:
        repo_l = json.load(f)

    data_path = Path(args.output)
    if not data_path.exists():
        os.mkdir(data_path)

    token_path = Path(args.token)
    token = None
    if not token_path.exists():
        token_needed = input('Do you need to access private repositories? (y/n): ')
        if token_needed == 'y':
            token = input('Enter your GitHub token: ')
            with token_path.open('w') as f:
                json.dump({'token': token}, f, ensure_ascii=False, indent=4)
    else:
        with token_path.open() as f:
            content = json.load(f)
            if 'token' not in content.keys():
                print('Please add your GitHub token to the `token.json` file in the following format: {"token": "your_token"}')
                exit()
            token = content['token']
    headers = { 'Accept': 'application/vnd.github.v3+json' }
    if token:
        headers['Authorization'] = 'Bearer {}'.format(token)

    for tuple_t in repo_l:
        user_t, repo_t = tuple_t.split('/')
        base_url = f'https://github.com/{tuple_t}/commit/'
        ms_l = [{'date': ms_date.strftime('%Y-%m-%d %H:%M:%S'), 'commits': {}, 'issues': {}, 'prs': {}} for ms_date in ms_dates]
        repo_url = 'https://api.github.com/repos/%s/%s' % (user_t, repo_t)
        repo_req = requests.get(repo_url, headers=headers)
        repo_res = repo_req.json()
        if 'message' in repo_res.keys() and repo_res['message'] == 'Not Found':
            continue
        page_n = 1
        repo_path = data_path / ('%s-%s.json' % (user_t, repo_t))
        while 1:
            commit_url = 'https://api.github.com/repos/%s/%s/commits?page=%s' % (user_t, repo_t, page_n)
            com_req = requests.get(commit_url, headers=headers)
            commits = com_req.json()
            if len(commits) == 0:
                break
            for commit in commits:
                date_t = commit['commit']['author']['date']
                date_t = datetime.fromisoformat(date_t.replace('Z', '+00:00'))
                if 'author' in commit.keys() and type(commit['author']) == dict and 'login' in commit['author'].keys():
                    author_t = commit['author']['login']
                elif 'commit' in commit.keys() and type(commit['commit']) == dict and 'author' in commit['commit'].keys() and type(commit['commit']['author']) == dict and 'name' in commit['commit']['author'].keys():
                    author_t = commit['commit']['author']['name']
                else:
                    author_t = 'unknown'
                message_t = commit['commit']['message']
                coauthors = coauthor_pattern.findall(message_t)
                hash_t = commit['sha']
                for i, ms_date in enumerate(ms_dates):
                    if date_t < ms_date:
                        for author_t in coauthors + [author_t]:
                            if author_t not in ms_l[i]['commits'].keys():
                                ms_l[i]['commits'][author_t] = { 'list': [], 'count': 0 }
                            ms_l[i]['commits'][author_t]['list'].append({ 'message': message_t, 'link': base_url + hash_t })
                            ms_l[i]['commits'][author_t]['count'] += 1
                        break
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            page_n += 1
        page_n = 1
        while 1:
            issue_url = 'https://api.github.com/repos/%s/%s/issues?state=all&page=%s' % (user_t, repo_t, page_n)
            iss_req = requests.get(issue_url, headers=headers)
            issues = iss_req.json()
            if len(issues) == 0:
                break
            for issue in issues:
                is_pr = 'pull_request' in issue.keys()
                key_t = 'prs' if is_pr else 'issues'
                date_t = issue['created_at']
                date_t = datetime.fromisoformat(date_t.replace('Z', '+00:00'))
                title_t = issue['title']
                desc_t = issue['body']
                label_cnt = len(issue['labels'])
                assignee_cnt = len(issue['assignees'])
                author_t = issue['user']['login']
                comments = []
                if issue['comments']:
                    comments_url = issue['comments_url']
                    comments_req = requests.get(comments_url, headers=headers)
                    comments_res = comments_req.json()
                    for comment in comments_res:
                        comments.append( { 'author': comment['user']['login'], 'body': comment['body'] } )
                for i, ms_date in enumerate(ms_dates):
                    if date_t < ms_date:
                        if author_t not in ms_l[i][key_t].keys():
                            ms_l[i][key_t][author_t] = { 'list': [], 'count': 0 }
                        d = { 'title': title_t, 'desc': desc_t, 'label_count': label_cnt, 'comments': comments, 'assignee_count': assignee_cnt, 'link': issue['html_url'], 'state': issue['state']}
                        ms_l[i][key_t][author_t]['list'].append(d)
                        ms_l[i][key_t][author_t]['count'] += 1
                        break
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            page_n += 1
        with repo_path.open('w') as f:
            json.dump(ms_l, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()