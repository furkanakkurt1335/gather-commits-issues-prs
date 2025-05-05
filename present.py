import argparse, json
from pathlib import Path

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--group', help='Group number', type=int, required=True)
    parser.add_argument('-y', '--year', help='Year of the course', type=int, required=True)
    parser.add_argument('-o', '--output-directory', help='Path to the output directory', type=Path, required=True)
    parser.add_argument('-u', '--usernames', help='GitHub usernames', type=Path, required=True)
    return parser.parse_args()

def main():
    args = get_args()
    group = args.group
    year = args.year

    script_dir = Path(__file__).parent
    input_dir = script_dir / 'commits-issues-prs'
    repo_name = f'bounswe-bounswe{year}group{group}'
    input_file = input_dir / f'{repo_name}.json'
    with input_file.open() as f:
        data = json.load(f)
    relevant_data = data[0]
    commits, issues, prs = relevant_data['commits'], relevant_data['issues'], relevant_data['prs']
    issue_comments = [comment for username in issues for issue in issues[username]['list'] for comment in issue['comments']]
    pr_comments = [comment for username in prs for pr in prs[username]['list'] for comment in pr['comments']]
    relevant_usernames = set(list(commits.keys()) + list(issues.keys()) + list(prs.keys()))
    output_directory = script_dir / 'summaries' / repo_name
    output_directory.mkdir(exist_ok=True)

    username_file = args.usernames
    with username_file.open() as f:
        usernames = json.load(f)
    threshold = 0
    for username in relevant_usernames:
        if username in usernames:
            full_name = usernames[username]
        else:
            full_name = username
        output_file = output_directory / f'{full_name}.md'
        output_str = f'# {full_name}\n\n'
        output_str += f'## Commits\n\n'
        if username not in commits:
            output_str += 'No commits found\n\n'
        else:
            filtered_commits = [commit for commit in commits[username]['list'] if commit['diff']['total'] > threshold and not (commit['message'].startswith('Merge branch') or commit['message'].startswith('Merge pull request') or commit['message'].startswith('Merge remote-tracking branch'))]
            for i, commit in enumerate(filtered_commits):
                message, link = commit['message'], commit['link']
                output_str += f'{i+1}. {message.replace("\n", " ; ")} - [Link]({link})\n'
            output_str += '\n'
        output_str += f'## Issues\n\n'
        if username not in issues:
            output_str += 'No issues found\n\n'
        else:
            filtered_issues = [issue for issue in issues[username]['list'] if issue['desc'] and len(issue['desc']) > threshold]
            if not filtered_issues:
                output_str += 'No issues found\n\n'
            else:
                for i, issue in enumerate(filtered_issues):
                    title, link = issue['title'], issue['link']
                    output_str += f'{i+1}. {title.replace("\n", " ; ")} - [Link]({link})\n'
                output_str += '\n'
            output_str += f'### Comments\n\n'
            filtered_issue_comments = [comment for comment in issue_comments if comment['author'] == username]
            if not filtered_issue_comments:
                output_str += 'No comments found\n\n'
            else:
                for i, issue_comment in enumerate(filtered_issue_comments):
                    body = issue_comment['body']
                    output_str += f'{i+1}. {body}\n'
                output_str += '\n'
        output_str += f'## PRs\n\n'
        if username not in prs:
            output_str += 'No PRs found\n\n'
        else:
            filtered_prs = [pr for pr in prs[username]['list'] if pr['desc'] and len(pr['desc']) > threshold]
            if not filtered_prs:
                output_str += 'No PRs found\n\n'
            else:
                for i, pr in enumerate(filtered_prs):
                    title, link = pr['title'], pr['link']
                    output_str += f'{i+1}. {title.replace("\n", " ; ")} - [Link]({link})\n'
                output_str += '\n'
        output_str += f'### Comments\n\n'
        filtered_pr_comments = [comment for comment in pr_comments if comment['author'] == username]
        if not filtered_pr_comments:
            output_str += 'No comments found\n\n'
        else:
            for i, pr_comment in enumerate(filtered_pr_comments):
                body = pr_comment['body']
                output_str += f'{i+1}. {body}\n'
            output_str += '\n'
        with output_file.open('w') as f:
            f.write(output_str)

if __name__ == '__main__':
    main()