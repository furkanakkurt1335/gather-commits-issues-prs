import requests, os, json, argparse, re
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

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
    gmt_str = '+03:00'
    for i, date in enumerate(ms_dates):
        year, month, day, hour, minute, second = date['year'], date['month'], date['day'], date['hour'], date['minute'], date['second']
        ms_dates[i]['year'] = f'{year:04d}'
        ms_dates[i]['month'] = f'{month:02d}'
        ms_dates[i]['day'] = f'{day:02d}'
        ms_dates[i]['hour'] = f'{hour:02d}'
        ms_dates[i]['minute'] = f'{minute:02d}'
        ms_dates[i]['second'] = f'{second:02d}'
    ms_dates = [datetime.fromisoformat('%s-%s-%sT%s:%s:%s%s' % (date['year'], date['month'], date['day'], date['hour'], date['minute'], date['second'], gmt_str)) for date in ms_dates]

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

    diff_pattern = re.compile(r'Showing (\d+) changed files? with (\d+) additions? and (\d+) deletions?\.')
    for tuple_t in repo_l:
        user_t, repo_t = tuple_t.split('/')
        base_url = f'https://github.com/{tuple_t}/commit/'
        diff_url = base_url + '{hash}?diff=unified&w=1'
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
                date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                if 'author' in commit.keys() and type(commit['author']) == dict and 'login' in commit['author'].keys():
                    author_t = commit['author']['login']
                elif 'commit' in commit.keys() and type(commit['commit']) == dict and 'author' in commit['commit'].keys() and type(commit['commit']['author']) == dict and 'name' in commit['commit']['author'].keys():
                    author_t = commit['commit']['author']['name']
                else:
                    author_t = 'unknown'
                message_t = commit['commit']['message']
                coauthors = coauthor_pattern.findall(message_t)
                hash_t = commit['sha']
                diff_url_t = diff_url.format(hash=hash_t)
                diff_req = requests.get(diff_url_t, headers=headers)
                soup = BeautifulSoup(diff_req.text, 'html.parser')
                text = re.sub(r'\s+', ' ', soup.text) # rm whitespaces
                diff = diff_pattern.search(text)
                if diff:
                    diff = { 'files': diff.group(1), 'additions': diff.group(2), 'deletions': diff.group(3) }
                else:
                    diff = 'unknown'
                for i, ms_date in enumerate(ms_dates):
                    if date_t < ms_date:
                        for author_t in coauthors + [author_t]:
                            if author_t not in ms_l[i]['commits'].keys():
                                ms_l[i]['commits'][author_t] = { 'count': 0, 'list': [] }
                            ms_l[i]['commits'][author_t]['list'].append({ 'message': message_t, 'date': date_str, 'link': base_url + hash_t, 'diff': diff})
                            ms_l[i]['commits'][author_t]['count'] += 1
                        break
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            page_n += 1
        print('Finished gathering commits for %s' % tuple_t)
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
                date_t = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                title_t = issue['title']
                desc_t = issue['body']
                labels = issue['labels']
                label_l = [label['name'] for label in labels]
                assignees = issue['assignees']
                assignee_l = [assignee['login'] for assignee in assignees]
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
                            ms_l[i][key_t][author_t] = { 'count': 0, 'list': [] }
                        d = { 'title': title_t, 'desc': desc_t, 'date': date_str, 'labels': label_l, 'assignees': assignee_l, 'link': issue['html_url'], 'state': issue['state'], 'comments': comments }
                        ms_l[i][key_t][author_t]['list'].append(d)
                        ms_l[i][key_t][author_t]['count'] += 1
                        break
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            page_n += 1
        print('Finished gathering issues and PRs for %s' % tuple_t)
        with repo_path.open('w') as f:
            json.dump(ms_l, f, ensure_ascii=False, indent=4)
        print('Finished gathering all data for %s' % tuple_t)

if __name__ == '__main__':
    main()