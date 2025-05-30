#!/usr/bin/env python3
# filepath: /Users/furkan1049/repos/furkanakkurt1335/gather-commits-issues-prs/gather.py
import requests, os, json, argparse, re, time, logging, sys
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
from dotenv import load_dotenv

# Function declarations first
def get_args():
    parser = argparse.ArgumentParser(description='Gather commits and issues from GitHub repositories')
    parser.add_argument('-r', '--repos', help='Path to the JSON file with the repositories', type=str, default='repos.json')
    parser.add_argument('-d', '--dates', help='Path to the JSON file with the milestone dates', type=str, default=None)
    parser.add_argument('-o', '--output', help='Path to the output directory', type=str, default='commits-issues-prs')
    parser.add_argument('-b', '--branch', help='Branch to gather data from', type=str)
    parser.add_argument('-s', '--since', help='Only gather data since this date (YYYY-MM-DD)', type=str)
    parser.add_argument('-u', '--usernames', help='Path to the JSON file mapping GitHub usernames to full names', type=str, default='github-usernames.json')
    parser.add_argument('-v', '--verbose', help='Verbose output (INFO level)', action='store_true')
    parser.add_argument('--debug', help='Debug output (DEBUG level)', action='store_true')
    return parser.parse_args()

def get_diff(url, headers, retry_count=3):
    """Get the diff information for a commit"""
    for attempt in range(retry_count):
        try:
            logging.debug(f"Fetching diff from {url} (attempt {attempt+1}/{retry_count})")
            commit_req = requests.get(url, headers=headers)
            commit_req.raise_for_status()
            commit_res = commit_req.json()
            filenames = {file['filename'] for file in commit_res['files']}
            total = commit_res['stats']['total']
            return {'filenames': filenames, 'total': total}
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            if attempt == retry_count - 1:
                logging.error(f"Error getting diff from {url}: {e}")
                return {'filenames': set(), 'total': 0}
            # Handle rate limiting
            if hasattr(e, 'response') and e.response and e.response.status_code == 403:
                reset_time = int(e.response.headers.get('X-RateLimit-Reset', 0))
                sleep_time = max(0, reset_time - time.time()) + 1
                if sleep_time > 0 and sleep_time < 300:  # Don't wait more than 5 minutes
                    logging.warning(f"Rate limit exceeded. Waiting for {sleep_time:.0f} seconds...")
                    time.sleep(sleep_time)
            logging.debug(f"Request failed: {e}. Retrying after exponential backoff.")
            time.sleep(2 ** attempt)  # Exponential backoff

def load_date_config(dates_file=None, since_date=None):
    """Load date configuration from file or use default/provided dates"""
    default_not_before_date = {'year': 2025, 'month': 2, 'day': 10, 'hour': 0, 'minute': 0, 'second': 0}
    default_ms_dates = [
        {'year': 2025, 'month': 5, 'day': 15, 'hour': 9, 'minute': 0, 'second': 0}
    ]

    not_before_date = default_not_before_date
    ms_dates = default_ms_dates

    if dates_file:
        path = Path(dates_file)
        if path.exists():
            logging.info(f"Loading date configuration from {dates_file}")
            with path.open() as f:
                date_config = json.load(f)
                if 'not_before_date' in date_config:
                    not_before_date = date_config['not_before_date']
                    logging.debug(f"Using custom not_before_date: {not_before_date}")
                if 'milestone_dates' in date_config:
                    ms_dates = date_config['milestone_dates']
                    logging.debug(f"Using custom milestone_dates: {ms_dates}")
        else:
            logging.warning(f"Date configuration file {dates_file} not found, using defaults")

    # Override with command line parameter if provided
    if since_date:
        try:
            date_parts = since_date.split('-')
            not_before_date = {
                'year': int(date_parts[0]),
                'month': int(date_parts[1]),
                'day': int(date_parts[2]),
                'hour': 0, 'minute': 0, 'second': 0
            }
            logging.info(f"Using since date from command line: {since_date}")
        except (ValueError, IndexError):
            logging.error(f"Invalid date format: {since_date}. Using default.")

    # Format dates
    not_before_d = {
        'year': f'{not_before_date["year"]:04d}',
        'month': f'{not_before_date["month"]:02d}',
        'day': f'{not_before_date["day"]:02d}',
        'hour': f'{not_before_date["hour"]:02d}',
        'minute': f'{not_before_date["minute"]:02d}',
        'second': f'{not_before_date["second"]:02d}'
    }

    formatted_ms_dates = []
    for date in ms_dates:
        formatted = {
            'year': f'{date["year"]:04d}',
            'month': f'{date["month"]:02d}',
            'day': f'{date["day"]:02d}',
            'hour': f'{date["hour"]:02d}',
            'minute': f'{date["minute"]:02d}',
            'second': f'{date["second"]:02d}'
        }
        formatted_ms_dates.append(formatted)

    return not_before_d, formatted_ms_dates

def get_full_name(username, username_mappings):
    """Get full name from GitHub username if available"""
    return username_mappings.get(username, username)

def setup_logger(args):
    """Configure the logger based on verbosity"""
    # Create logger
    logger = logging.getLogger('gather')
    logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter

    # Clear any existing handlers
    logger.handlers = []

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Ensure log directory exists
    log_path = Path('gather.log').resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with absolute path
    file_handler = logging.FileHandler(str(log_path), mode='w', encoding='utf-8')  # 'w' mode to start fresh each run
    if args.debug:
        file_handler.setLevel(logging.DEBUG)
    elif args.verbose:
        file_handler.setLevel(logging.INFO)
    else:
        file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    if args.debug:
        console_handler.setLevel(logging.DEBUG)
    elif args.verbose:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Configure root logger as well
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Disable propagation to avoid duplicate logs
    logger.propagate = False

    logger.info("Logging initialized at level: %s (console), %s (file)",
              logging.getLevelName(console_handler.level),
              logging.getLevelName(file_handler.level))
    
    return logger

def setup_github_auth(_):
    """Setup GitHub authentication headers"""
    headers = {'Accept': 'application/vnd.github.v3+json'}

    # Load .env file if it exists
    env_path = Path('.env')

    # Try to get token from environment variables (loads from .env if exists)
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')

    # If token not found, prompt user
    if not token:
        token_needed = input('Do you need to access private repositories? (y/N): ')
        if token_needed.lower() == 'y':
            token = input('Enter your GitHub token: ')
            # Save token to .env file
            with env_path.open('w') as env_file:
                env_file.write(f'GITHUB_TOKEN={token}\n')
            logging.info("Saved token to .env file")
            # Reload environment variables
            load_dotenv(override=True)

    if token:
        headers['Authorization'] = f'Bearer {token}'
        logging.info("Using GitHub token for authentication")
    else:
        logging.warning("No GitHub token provided, API rate limits may apply")

    return headers

def process_repos(repo_list, headers, args, not_before_d, ms_dates_formatted, username_mappings={}):
    """Process each repository to gather commits, issues, and PRs"""
    data_path = Path(args.output)
    data_path.mkdir(exist_ok=True)
    logging.info(f"Output directory: {data_path}")

    coauthor_pattern = re.compile(r'Co-authored-by: (.*) <.*>')
    gmt_str = '+03:00'

    not_before_date = datetime.fromisoformat(
        f'{not_before_d["year"]}-{not_before_d["month"]}-{not_before_d["day"]}T'
        f'{not_before_d["hour"]}:{not_before_d["minute"]}:{not_before_d["second"]}{gmt_str}'
    )
    logging.info(f"Not before date: {not_before_date}")

    ms_dates = [datetime.fromisoformat(
        f'{date["year"]}-{date["month"]}-{date["day"]}T'
        f'{date["hour"]}:{date["minute"]}:{date["second"]}{gmt_str}'
    ) for date in ms_dates_formatted]
    logging.info(f"Milestone dates: {', '.join(ms.strftime('%Y-%m-%d %H:%M:%S') for ms in ms_dates)}")

    for repo_tuple in tqdm(repo_list, desc="Processing repositories"):
        logging.info(f'Gathering data for {repo_tuple}')
        user_t, repo_t = repo_tuple.split('/')
        ms_l = [{'date': ms_date.strftime('%Y-%m-%d %H:%M:%S'), 'commits': {}, 'issues': {}, 'prs': {}} for ms_date in ms_dates]
        repo_url = f'https://api.github.com/repos/{user_t}/{repo_t}'

        # Verify repository exists and is accessible
        logging.debug(f"Verifying repository: {repo_url}")
        repo_req = requests.get(repo_url, headers=headers)
        if repo_req.status_code == 404:
            logging.error(f"Repository {repo_tuple} not found or inaccessible. Skipping.")
            continue
        repo_req.raise_for_status()
        repo_res = repo_req.json()

        repo_path = data_path / f'{user_t}-{repo_t}.json'
        prev_diffs = {}

        # Gather commits
        gather_commits(user_t, repo_t, headers, args, repo_path, not_before_date, ms_dates, ms_l,
                      coauthor_pattern, prev_diffs, username_mappings)

        # Gather issues and PRs
        gather_issues_and_prs(user_t, repo_t, headers, repo_path, not_before_date, ms_dates, ms_l, prev_diffs, username_mappings)

        # Sort and finalize data
        finalize_repo_data(ms_l, ms_dates, repo_path)
        logging.info(f'✓ Finished gathering all data for {repo_tuple}')

def gather_commits(user_t, repo_t, headers, args, repo_path, not_before_date, ms_dates, ms_l,
                  coauthor_pattern, prev_diffs, username_mappings={}):
    """Gather commits for a repository"""
    logging.info(f'  Gathering commits for {user_t}/{repo_t}...')
    page_n = 1

    with tqdm(desc="  Fetching commits", unit="page") as progress:
        while True:
            if args.branch:
                commits_url = f'https://api.github.com/repos/{user_t}/{repo_t}/commits?sha={args.branch}&page={page_n}'
            else:
                commits_url = f'https://api.github.com/repos/{user_t}/{repo_t}/commits?page={page_n}'

            try:
                logging.debug(f"Fetching commits from {commits_url}")
                commits_req = requests.get(commits_url, headers=headers)
                commits_req.raise_for_status()
                commits = commits_req.json()
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response:
                    if e.response.status_code == 403 and 'API rate limit exceeded' in e.response.text:
                        logging.warning('API rate limit exceeded. Try adding a GitHub token or wait an hour.')
                        reset_time = int(e.response.headers.get('X-RateLimit-Reset', 0))
                        wait_time = max(0, reset_time - time.time()) + 1
                        if wait_time < 300:  # Don't wait more than 5 minutes
                            logging.info(f"Waiting for {wait_time:.0f} seconds...")
                            time.sleep(wait_time)
                            continue
                    elif e.response.status_code == 401:
                        logging.error('Bad credentials, please check your token.')
                logging.error(f"Error fetching commits: {e}")
                break

            if not commits or not isinstance(commits, list):
                break

            seen_before = False
            progress.update(1)

            for commit in commits:
                try:
                    commit_url = commit['url']
                    date_t = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))

                    if date_t < not_before_date:
                        seen_before = True
                        break

                    date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

                    # Determine the author
                    if ('author' in commit and commit['author'] and 'login' in commit['author']):
                        author_t = commit['author']['login']
                    elif 'commit' in commit and 'author' in commit['commit'] and 'name' in commit['commit']['author']:
                        author_t = commit['commit']['author']['name']
                    else:
                        author_t = 'unknown'

                    # Get co-authors from commit message
                    message_t = commit['commit']['message']
                    coauthors = coauthor_pattern.findall(message_t)
                    html_url = commit['html_url']

                    # Get diff information
                    diff = get_diff(commit_url, headers)
                    sha = commit['sha']
                    prev_diffs[sha] = diff
                    diff = {'files': len(diff['filenames']), 'total': diff['total']}

                    # Add commit data to milestone lists
                    for i, ms_date in enumerate(ms_dates):
                        if date_t < ms_date:
                            for author_name in coauthors + [author_t]:
                                # Try to get the full name from mappings
                                full_name = get_full_name(author_name, username_mappings)

                                if author_name not in ms_l[i]['commits']:
                                    ms_l[i]['commits'][author_name] = {
                                        'count': 0,
                                        'list': [],
                                        'full_name': full_name
                                    }
                                ms_l[i]['commits'][author_name]['list'].append({
                                    'message': message_t,
                                    'date': date_str,
                                    'link': html_url,
                                    'diff': diff
                                })
                                ms_l[i]['commits'][author_name]['count'] += 1
                            break
                except Exception as e:
                    logging.error(f"Error processing commit {commit.get('sha', 'unknown')}: {e}")
                    continue

            # Save progress after each page
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            logging.debug(f"Saved commits progress after page {page_n}")

            if seen_before:
                logging.debug("Found commits before the cut-off date, stopping pagination")
                break

            page_n += 1
            logging.debug(f"Moving to commits page {page_n}")

def gather_issues_and_prs(user_t, repo_t, headers, repo_path, not_before_date, ms_dates, ms_l, prev_diffs, username_mappings={}):
    """Gather issues and PRs for a repository"""
    logging.info(f'  Gathering issues and PRs for {user_t}/{repo_t}...')
    page_n = 1

    with tqdm(desc="  Fetching issues/PRs", unit="page") as progress:
        while True:
            issue_url = f'https://api.github.com/repos/{user_t}/{repo_t}/issues?state=all&page={page_n}'

            try:
                logging.debug(f"Fetching issues from {issue_url}")
                iss_req = requests.get(issue_url, headers=headers)
                iss_req.raise_for_status()
                issues = iss_req.json()
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching issues: {e}")
                break

            if not issues or not isinstance(issues, list):
                break

            seen_before = False
            progress.update(1)

            for issue in issues:
                try:
                    is_pr = 'pull_request' in issue
                    key_t = 'prs' if is_pr else 'issues'
                    date_t = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))

                    if date_t < not_before_date:
                        seen_before = True
                        break

                    date_str = (date_t + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                    title_t = issue['title']
                    desc_t = issue.get('body', '')
                    label_l = [label['name'] for label in issue.get('labels', [])]
                    assignee_l = [assignee['login'] for assignee in issue.get('assignees', [])]
                    author_t = issue['user']['login']

                    # Gather comments
                    comments = []
                    if issue.get('comments', 0) > 0:
                        try:
                            comments_url = issue['comments_url']
                            comments_req = requests.get(comments_url, headers=headers)
                            comments_req.raise_for_status()
                            comments_res = comments_req.json()
                            comments = []
                            for comment in comments_res:
                                comment_author = comment['user']['login']
                                comment_author_full_name = get_full_name(comment_author, username_mappings)
                                comments.append({
                                    'author': comment_author,
                                    'author_full_name': comment_author_full_name,
                                    'body': comment.get('body', '')
                                })
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching comments: {e}")

                    html_url = issue['html_url']

                    # For PRs, get commit information
                    if is_pr:
                        try:
                            commits_url = issue['pull_request']['url'] + '/commits'
                            commits_req = requests.get(commits_url, headers=headers)
                            commits_req.raise_for_status()
                            commits_res = commits_req.json()

                            urls = {commit['sha']: commit['url'] for commit in commits_res}
                            diffs = []
                            for sha, url in urls.items():
                                if sha not in prev_diffs:
                                    diff = get_diff(url, headers)
                                    prev_diffs[sha] = diff
                                else:
                                    diff = prev_diffs[sha]
                                diffs.append(diff)

                            diff_d = {'files': set(), 'total': sum(diff['total'] for diff in diffs)}
                            for diff in diffs:
                                diff_d['files'].update(diff['filenames'])
                            diff_d['files'] = len(diff_d['files'])
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching PR commits: {e}")
                            diff_d = {'files': 0, 'total': 0}

                    # Add issue/PR to milestone lists
                    for i, ms_date in enumerate(ms_dates):
                        if date_t < ms_date:
                            # Try to get the full name from mappings
                            full_name = get_full_name(author_t, username_mappings)

                            if author_t not in ms_l[i][key_t]:
                                ms_l[i][key_t][author_t] = {
                                    'count': 0,
                                    'list': [],
                                    'full_name': full_name
                                }

                            # Also map assignees to full names if possible
                            assignee_full_names = []
                            for assignee in assignee_l:
                                assignee_full_names.append(get_full_name(assignee, username_mappings))

                            d = {
                                'title': title_t,
                                'desc': desc_t,
                                'date': date_str,
                                'labels': label_l,
                                'assignees': assignee_l,
                                'assignee_full_names': assignee_full_names,
                                'link': html_url,
                                'state': issue['state'],
                                'comments': comments
                            }

                            if is_pr:
                                d['diff'] = diff_d

                            ms_l[i][key_t][author_t]['list'].append(d)
                            ms_l[i][key_t][author_t]['count'] += 1
                            break
                except Exception as e:
                    logging.error(f"Error processing issue/PR #{issue.get('number', 'unknown')}: {e}")
                    continue

            # Save progress after each page
            with repo_path.open('w') as f:
                json.dump(ms_l, f, ensure_ascii=False, indent=4)
            logging.debug(f"Saved issues/PRs progress after page {page_n}")

            if seen_before:
                logging.debug("Found issues/PRs before the cut-off date, stopping pagination")
                break

            page_n += 1
            logging.debug(f"Moving to issues/PRs page {page_n}")

def finalize_repo_data(ms_l, ms_dates, repo_path):
    """Sort and finalize repository data"""
    logging.info(f"Finalizing data for {repo_path.name}")

    # Calculate stats
    for i, _ in enumerate(ms_dates):
        commit_count = sum(author_data['count'] for author_data in ms_l[i]['commits'].values())
        issue_count = sum(author_data['count'] for author_data in ms_l[i]['issues'].values())
        pr_count = sum(author_data['count'] for author_data in ms_l[i]['prs'].values())
        logging.info(f"Milestone {i+1}: {commit_count} commits, {issue_count} issues, {pr_count} PRs")

    # Sort by date
    logging.debug("Sorting entries by date")
    for i, _ in enumerate(ms_dates):
        for key_t in ['commits', 'issues', 'prs']:
            for author_t in ms_l[i][key_t]:
                ms_l[i][key_t][author_t]['list'] = sorted(
                    ms_l[i][key_t][author_t]['list'],
                    key=lambda x: x['date']
                )

    # Sort keys alphabetically
    logging.debug("Sorting authors alphabetically")
    for i, _ in enumerate(ms_dates):
        for key_t in ['commits', 'issues', 'prs']:
            ms_l[i][key_t] = dict(sorted(ms_l[i][key_t].items()))

    # Save final data
    logging.debug(f"Saving final data to {repo_path}")
    with repo_path.open('w') as f:
        json.dump(ms_l, f, ensure_ascii=False, indent=4)

def main():
    args = get_args()

    try:
        # Setup logger first, before any other operations
        logger = setup_logger(args)

        # Add virtual environment to path if it exists
        venv_path = Path(__file__).parent / '.venv'
        if venv_path.exists():
            venv_site_packages = list(venv_path.glob('lib/python*/site-packages'))
            if venv_site_packages:
                sys.path.insert(0, str(venv_site_packages[0]))
                logger.info(f"Using Python packages from virtual environment: {venv_site_packages[0]}")

        # Setup authentication
        headers = setup_github_auth(None)

        # Load date configuration
        not_before_d, ms_dates_formatted = load_date_config(args.dates, args.since)
        logging.info(f"Using not before date: {not_before_d} and milestone dates: {ms_dates_formatted}")
    except Exception as e:
        logging.error(f"Error during setup: {e}")
        sys.exit(1)
    # Ensure output directory exists
    data_path = Path(args.output)
    data_path.mkdir(exist_ok=True)
    logging.info(f"Output directory: {data_path}")
    logging.info("Starting data gathering...")

    # Load repositories list
    repos_path = Path(args.repos)
    if not repos_path.exists():
        with repos_path.open('w') as f:
            json.dump([], f)
        logging.error(f'Please add your repositories to the file `{args.repos}` in the format: ["username/repo"]')
        return

    with repos_path.open() as f:
        repo_list = json.load(f)

    if not repo_list:
        logging.error(f'No repositories found in {args.repos}. Please add repositories in the format: ["username/repo"]')
        return

    # Load GitHub username to full name mappings if available
    username_mappings = {}
    username_path = Path(args.usernames)
    if username_path.exists():
        try:
            with username_path.open('r', encoding='utf-8') as f:
                username_mappings = json.load(f)
            logging.info(f"Loaded {len(username_mappings)} username mappings from {args.usernames}")
        except Exception as e:
            logging.error(f"Error loading username mappings: {e}")
    else:
        logging.warning(f"Username mapping file {args.usernames} not found. Using GitHub usernames as is.")
        # Create an example username mapping structure to help users
        example_path = Path("github-usernames.example.json")
        if not example_path.exists():
            example = {
                "github-username": "Full Name",
                "another-username": "Another Person"
            }
            with example_path.open('w', encoding='utf-8') as f:
                json.dump(example, f, ensure_ascii=False, indent=4)
            logging.info(f"Created example mapping file at {example_path} for reference")

    # Process repositories
    process_repos(repo_list, headers, args, not_before_d, ms_dates_formatted, username_mappings)

    logging.info("Data gathering complete!")

if __name__ == '__main__':
    main()