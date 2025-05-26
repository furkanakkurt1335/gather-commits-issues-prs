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
- `-u, --usernames`: Path to JSON file mapping GitHub usernames to full names (default: `github-usernames.json`)

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

### GitHub Username Mapping

To map GitHub usernames to full names, the tool supports CSV data import:

1. Use the included `csv_to_usernames_json.py` script to convert CSV data to JSON:

   ```bash
   python csv_to_usernames_json.py path/to/student_data.csv -o github-usernames.json
   ```

2. The CSV should have columns for `First name`, `Last name`, and `GitHub username`
3. This creates a JSON file mapping GitHub usernames to full names
4. `gather.py` will use this mapping to include full names alongside GitHub usernames in the output data

The resulting JSON structure looks like this:

```json
{
    "github-username": "Full Name", 
    "another-username": "Another Person"
}
```

For convenience, a simple script is provided that converts CSV data and gathers repository data:

```bash
# Convert CSV to username mappings and gather data
./run_with_usernames.sh path/to/student_data.csv
```

This script will:

1. Convert the CSV data to GitHub username mappings
2. Use those mappings when gathering repository data

#### Creating a GitHub Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" (classic)
3. Add a note (e.g., "gather-commits-issues-prs")
4. Select the following scopes:
   - `repo` (for accessing private repositories)
   - `read:user` (for user information)
5. Click "Generate token" and copy the token immediately
6. Add this token to your `.env` file as shown above

## Examples

### Gathering data for a specific repository

```bash
python gather.py -r custom-repos.json -o output-data
```

### Gathering data with username mappings

```bash
python gather.py -r repos.json -u github-usernames.json
```

## Output Format

The gathered data is saved as JSON files with the following structure:

- Commits: author (with full name if available), message, date, link, and statistics (files changed, lines modified)
- Issues: author (with full name if available), title, description, labels, assignees, comments, and state
- Pull Requests: same as issues plus commit information

When GitHub username mappings are provided, the output includes both the GitHub username and the full name for each contributor, making the data more readable and easier to identify contributors.

## License

This project is licensed under the terms included in the LICENSE file.
