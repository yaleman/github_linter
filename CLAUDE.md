# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

github_linter is a Python tool for auditing GitHub repositories at scale. It scans repositories for common configuration issues, missing files, and standardization opportunities across multiple repos.

## Development Commands

### Testing and Linting

- Run all precommit checks: `make precommit`
- Run linting: `make ruff`
- Run type checking: `make types`
- Run tests: `make test`
- Run single test: `uv run pytest tests/test_<module>.py::<test_name>`

### Running the CLI

- Run the CLI: `uv run github-linter`
- Run with filters: `uv run python -m github_linter --repo <repo_name> --owner <owner_name>`
- Run specific module: `uv run python -m github_linter --module <module_name>`
- Run with fixes: `uv run python -m github_linter --fix`
- List available repos: `uv run python -m github_linter --list-repos`

### Web Interface

- Start web server: `uv run github-linter-web`
- Or use the script: `./run_web.sh`

### Docker

- Build container: `make docker_build`
- Run web server in container: `make docker_run`

## Architecture

### Core Components

1. **GithubLinter** (`github_linter/__init__.py`) - Main orchestrator that:
   - Handles GitHub authentication (via environment variable `GITHUB_TOKEN` or config file)
   - Manages rate limiting
   - Coordinates module execution across repositories
   - Generates reports

2. **RepoLinter** (`github_linter/repolinter.py`) - Per-repository handler that:
   - Manages file caching for the repository
   - Runs test modules against the repository
   - Tracks errors, warnings, and fixes
   - Provides utility methods for checking files and languages
   - Handles file creation/updates with protected branch awareness

3. **Test Modules** (`github_linter/tests/`) - Pluggable modules that check specific aspects:
   - Each module must define `CATEGORY`, `LANGUAGES`, and `DEFAULT_CONFIG`
   - Functions starting with `check_` are automatically discovered and run
   - Functions starting with `fix_` are run when `--fix` flag is used
   - Modules are loaded dynamically in `tests/__init__.py`

### Available Test Modules

- `branch_protection` - Validates and configures branch protection on default branches
- `codeowners` - Validates CODEOWNERS files
- `dependabot` - Validates Dependabot configuration
- `generic` - Checks for unwanted files, CODEOWNERS, FUNDING.yml
- `github_actions` - Validates GitHub Actions workflows
- `homebrew` - Homebrew-specific checks
- `issues` - Reports on open issues and PRs
- `mkdocs` - Ensures mkdocs projects have proper CI setup
- `pyproject` - Validates pyproject.toml (authors, naming, configuration)
- `security_md` - Checks for SECURITY.md
- `terraform` - Checks Terraform provider configurations

### Module Language Filtering

Modules declare which languages they apply to via the `LANGUAGES` attribute:

- Use `["all"]` for modules that apply to all repositories
- Use specific languages (e.g., `["python"]`, `["rust"]`) to run only on repos with those languages
- Language detection is based on GitHub's automatic language detection

### Configuration

Configuration file locations (in priority order):

1. `./github_linter.json` (local directory)
2. `~/.config/github_linter.json` (user config)

Each module can define `DEFAULT_CONFIG` which gets merged with user configuration.

#### Branch Protection Configuration

The `branch_protection` module supports both legacy branch protection rules and modern GitHub rulesets. It can check existing protection, create new protection, and migrate from legacy rules to rulesets.

```json
{
  "branch_protection": {
    "enable_protection": true,
    "allow_admin_bypass": true,
    "require_pull_request": true,
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_review": false,
    "use_rulesets": true,
    "migrate_to_rulesets": false,
    "warn_on_mismatch": true,
    "language_checks": {
      "Python": ["pytest", "ruff", "mypy"],
      "Rust": ["cargo-test", "clippy"],
      "JavaScript": ["test", "lint"],
      "TypeScript": ["test", "lint"],
      "Shell": ["shellcheck"],
      "Go": ["test", "lint"]
    }
  }
}
```

**Configuration Options:**

- `enable_protection` - Whether to enable branch protection checks (default: true)
- `allow_admin_bypass` - Allow repository admins to bypass protection requirements (default: true). For legacy protection, this sets `enforce_admins=false`. For rulesets, this adds repository admin role (ID 5) to `bypass_actors`.
- `require_pull_request` - Require pull request before merging (default: true)
- `required_approving_review_count` - Number of required PR approvals (default: 1)
- `dismiss_stale_reviews` - Dismiss stale reviews when new commits are pushed (default: true)
- `require_code_owner_review` - Require review from code owners (default: false)
- `use_rulesets` - Prefer GitHub rulesets over legacy branch protection (default: true)
- `migrate_to_rulesets` - Automatically migrate from legacy protection to rulesets when fixing (default: false)
- `warn_on_mismatch` - If protection exists but doesn't match config, warn instead of error (default: true)
- `language_checks` - Map of GitHub language names to required status check names. The module automatically determines which checks to require based on detected repository languages.

**Legacy vs Rulesets:**

- Legacy branch protection: Traditional branch protection API (one rule per branch)
- Rulesets: Modern GitHub protection (multiple rulesets aggregate, more features)
- The module detects which system is in use and can work with both
- With `use_rulesets: true`, new protection is created as rulesets
- With `migrate_to_rulesets: true`, the fix function will convert legacy protection to rulesets
- Both systems can coexist; the module checks both and reports on mismatches

**Implementation Notes:**

- Uses PyGithub's `_requester` API for rulesets since PyGithub doesn't natively support them yet
- Rulesets API requires GitHub API version 2022-11-28
- Rulesets provide more granular control and organization-wide enforcement

### Exception Handling

The codebase uses custom exceptions for flow control:

- `SkipOnArchived` - Skip check for archived repositories
- `SkipOnPrivate` - Skip check for private repositories
- `SkipOnPublic` - Skip check for public repositories
- `SkipOnProtected` - Skip check when default branch is protected
- `SkipNoLanguage` - Skip check when required language not present
- `NoChangeNeeded` - Indicates no action needed

These exceptions are caught in `RepoLinter.run_module()` and suppress the check/fix function gracefully.

## Adding New Test Modules

1. Create a new module under `github_linter/tests/`
2. Define required module-level attributes:
   - `CATEGORY: str` - Display name for reports
   - `LANGUAGES: List[str]` - Languages this module applies to (or `["all"]`)
   - `DEFAULT_CONFIG: Dict[str, Any]` - Default configuration
3. Implement check functions: `def check_<something>(repo: RepoLinter) -> None`
4. Implement fix functions: `def fix_<something>(repo: RepoLinter) -> None`
5. Import the module in `github_linter/tests/__init__.py`
6. Use `repo.error()`, `repo.warning()`, or `repo.fix()` to report results

## Testing Strategy

- Unit tests are in `/tests/` directory
- Tests requiring network/authentication are marked with `@pytest.mark.network`
- Run tests without network: `uv run pytest -m "not network"`
- The codebase uses both PyGithub and github3.py libraries

## Code Style

- Line length: 200 characters (configured in pyproject.toml)
- Type checking: strict mypy mode
- Linting: ruff with pylint-pydantic plugin
- Use pydantic for validation where appropriate
- Use loguru for logging

## Dependencies

- Main GitHub libraries: `pygithub`, `github3-py`
- Web framework: `fastapi`, `uvicorn`
- Configuration: `json5`, `pyyaml`, `tomli`, `python-hcl2`
- Type checking: `mypy` with strict mode
- Testing: `pytest`
