import argparse, json
from pathlib import Path

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Path to the input file', type=Path, required=True)
    parser.add_argument('-u', '--usernames', help='GitHub usernames', type=Path, required=True)
    return parser.parse_args()

def main():
    args = get_args()

    username_file = args.usernames
    with username_file.open() as f:
        usernames = json.load(f)

    input_file = args.input
    with input_file.open() as f:
        data = json.load(f)
    relevant_data = data[0]
    commits, issues, prs = relevant_data['commits'], relevant_data['issues'], relevant_data['prs']
    issue_comments = [comment for username in issues for issue in issues[username]['list'] for comment in issue['comments']]
    pr_comments = [comment for username in prs for pr in prs[username]['list'] for comment in pr['comments']]
    relevant_usernames = set(list(commits.keys()) + list(issues.keys()) + list(prs.keys()))
    for username in relevant_usernames:
        if username in usernames:
            full_name = usernames[username]
        else:
            full_name = username
        print(f'## {full_name}\n')
        print(f'### Commits\n')
        if username not in commits:
            print('No commits found\n')
        else:
            filtered_commits = [commit for commit in commits[username]['list'] if commit['diff']['total'] > 20 and not (commit['message'].startswith('Merge branch') or commit['message'].startswith('Merge pull request') or commit['message'].startswith('Merge remote-tracking branch'))]
            for i, commit in enumerate(filtered_commits):
                message, link = commit['message'], commit['link']
                print(f'{i+1}. {message.replace('\n', ' ; ')} - [Link]({link})')
            print()
        print(f'### Issues\n')
        if username not in issues:
            print('No issues found\n')
        else:
            filtered_issues = [issue for issue in issues[username]['list'] if issue['desc'] and len(issue['desc']) > 20]
            if not filtered_issues:
                print('No issues found\n')
            else:
                for i, issue in enumerate(filtered_issues):
                    title, link = issue['title'], issue['link']
                    print(f'{i+1}. {title.replace('\n', ' ; ')} - [Link]({link})')
                print()
            print(f'#### Comments\n')
            filtered_issue_comments = [comment for comment in issue_comments if comment['author'] == username]
            if not filtered_issue_comments:
                print('No comments found\n')
            else:
                for i, issue_comment in enumerate(filtered_issue_comments):
                    body = issue_comment['body']
                    print(f'{i+1}. {body}')
                print()
        print(f'### PRs\n')
        if username not in prs:
            print('No PRs found\n')
        else:
            filtered_prs = [pr for pr in prs[username]['list'] if pr['desc'] and len(pr['desc']) > 20]
            if not filtered_prs:
                print('No PRs found\n')
            else:
                for i, pr in enumerate(filtered_prs):
                    title, link = pr['title'], pr['link']
                    print(f'{i+1}. {title.replace('\n', ' ; ')} - [Link]({link})')
                print()
        print(f'#### Comments\n')
        filtered_pr_comments = [comment for comment in pr_comments if comment['author'] == username]
        if not filtered_pr_comments:
            print('No comments found\n')
        else:
            for i, pr_comment in enumerate(filtered_pr_comments):
                body = pr_comment['body']
                print(f'{i+1}. {body}')
            print()

if __name__ == '__main__':
    main()