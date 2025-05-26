# gather-commits-issues-prs

A tool for gathering and presenting contributions (commits, issues, and pull requests) from GitHub repositories.

## Features

- Collects all commits, issues, and pull requests from specified GitHub repositories
- Filters contributions by date ranges
- Handles co-authored commits properly
- Calculates statistics for each contribution (e.g., lines changed, files modified)
- Generates detailed Markdown summaries of contributions by author
- Supports private repositories via GitHub tokens
- Customizable filters and thresholds

## Requirements

This project requires Python 3 and has the following dependencies:

- `bs4` (BeautifulSoup4): For HTML parsing
- `python-dotenv`: For managing environment variables (e.g., GitHub token)
- `requests`: For making API calls to GitHub
- `tqdm`: For progress bars in the terminal

## Installation

Clone this repository and install the dependencies:

```bash
git clone https://github.com/yourusername/gather-commits-issues-prs.git
cd gather-commits-issues-prs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### 1. Configure Repositories

Create or edit `repos.json` with the repositories you want to analyze:

```json
[
  "username/repository",
  "organization/repository"
]
```

### 2. Gather Data

Run the gather script to collect data from the specified repositories:

```bash
python gather.py
```

Options:
- `-r, --repos`: Path to JSON file listing repositories (default: `repos.json`)
- `-o, --output`: Directory for output data (default: `commits-issues-prs`)
- `-b, --branch`: Branch to analyze (default: main/default branch)
- `-s, --since`: Only gather data since this date in YYYY-MM-DD format

### GitHub Authentication

For private repositories, you'll need a GitHub token stored in a `.env` file:

1. Create a file named `.env` in the root directory of the project
2. Add your GitHub token in the following format:

    ```bash
    GITHUB_TOKEN=your_personal_access_token_here
    ```

3. If you don't have a `.env` file, the script will prompt you to enter a token if needed
4. The token will be automatically saved to the `.env` file for future use

The `.env` file is included in `.gitignore` to prevent accidentally committing your token.

#### Creating a GitHub Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" (classic)
3. Add a note (e.g., "gather-commits-issues-prs")
4. Select the following scopes:
   - `repo` (for accessing private repositories)
   - `read:user` (for user information)
5. Click "Generate token" and copy the token immediately
6. Add this token to your `.env` file as shown above

### 3. Generate Summaries

Generate Markdown summaries for contributors:

```bash
python present.py -g [GROUP_NUMBER] -y [YEAR] -o [OUTPUT_DIRECTORY] -u [USERNAMES_FILE]
```

Required parameters:
- `-g, --group`: Group number
- `-y, --year`: Year of the course/project
- `-o, --output-directory`: Directory to save the summary files
- `-u, --usernames`: Path to JSON file mapping GitHub usernames to full names

## Examples

### Gathering data for a specific repository

```bash
python gather.py -r custom-repos.json -o output-data
```

### Generating summaries for a group

```bash
python present.py -g 1 -y 2025 -o ./summaries -u github-usernames.json
```

## Output Format

The gathered data is saved as JSON files with the following structure:

- Commits: author, message, date, link, and statistics (files changed, lines modified)
- Issues: author, title, description, labels, assignees, comments, and state
- Pull Requests: same as issues plus commit information

## License

This project is licensed under the terms included in the LICENSE file.
