# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

github_linter is a Python tool for managing GitHub repositories in bulk. Its main job is to inspect repositories for policy or configuration drift, report what is wrong, and optionally apply repository-side fixes such as creating or updating files, workflows, and branch protection.

The project is built around a modular "test then fix" model:

- A module can define one or more `check_*` functions that inspect a repository and report problems.
- The same module can define one or more `fix_*` functions that make corrective changes when `--fix` is enabled.
- Modules can be run all at once, filtered by module name, or filtered down to specific checks/fixes.
- Modules can also declare language requirements so Python-only or Terraform-only checks do not run on unrelated repositories.

In practice, the tool is closer to a repository configuration manager than a passive linter. It can validate state, propose drift through warnings/errors, and push changes back to GitHub when fixes are enabled.

**MANDATORY** You are not finished with a task until running `just check` passes without warnings or errors.

## Development Commands

### Testing and Linting

- Run all precommit checks: `just check`
- Run linting: `just ruff`
- Run type checking: `just lint`
- Run tests: `just test`
- Run single test: `uv run pytest tests/test_<module>.py::<test_name>`

### Running the CLI

- Run the CLI: `uv run github-linter`
- Run with filters: `uv run python -m github_linter --repo <repo_name> --owner <owner_name>`
- Run specific module: `uv run python -m github_linter --module <module_name>`
- Run with fixes: `uv run python -m github_linter --fix`
- List available repos: `uv run python -m github_linter --list-repos`

### Web Interface

- Start web server: `./run_web.sh`

### Docker

- Build container: `just docker_build`
- Run web server in container: `just docker_run`

## Architecture

### Core flow

1. `github_linter/__main__.py` is the CLI entrypoint.
   - Parses repo, owner, module, check, and `--fix` flags.
   - Loads the available modules from `github_linter.tests`.
   - Selects repositories via the GitHub API.

2. `GithubLinter` in `github_linter/__init__.py` is the top-level orchestrator.
   - Loads config from `github_linter.json` or `~/.config/github_linter.json`.
   - Authenticates with both PyGithub and `github3.py`.
   - Builds the repo list, applies module selection, handles rate limiting, and stores the final report.

3. `RepoLinter` in `github_linter/repolinter.py` is the per-repository execution context.
   - Wraps one GitHub repository.
   - Caches file lookups.
   - Merges module default config into runtime config.
   - Records `errors`, `warnings`, and `fixes`.
   - Exposes helper methods for reading repo files, checking languages, and writing fixes back to GitHub.

4. Modules under `github_linter/tests/` provide the actual repository rules.
   - They are imported in `github_linter/tests/__init__.py`.
   - Each module declares `CATEGORY`, `LANGUAGES`, and `DEFAULT_CONFIG`.
   - Each module contributes `check_*` and optional `fix_*` functions.

5. File and workflow templates used by fixes live under `github_linter/fixes/`.
   - Fix functions typically read these templates and commit them into the target repository with `RepoLinter.create_or_update_file()`.

### Execution model

For each selected repository, the CLI creates a `RepoLinter` and runs each enabled module through `RepoLinter.run_module()`.

- Module config defaults are merged in before execution.
- Language filtering happens before a module runs.
- Every `check_*` function in the module is executed first.
- If `--fix` is enabled, every `fix_*` function is then executed as part of the same module pass.
- Check/fix execution can be narrowed with `--module` and `--check`.
- Skip exceptions such as archived/private/protected repositories are used as normal control flow and are swallowed by the runner.

This means a typical workflow is:

1. Run checks across all or some repositories.
2. Review the report.
3. Re-run with `--fix` to apply the module fixes that correspond to the same problem space.

The code does not enforce one exact `check_*` to `fix_*` pairing by name. Instead, checks and fixes are grouped by module and category, so a module usually contains the validation and remediation logic for the same repository concern.

### Available Modules

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

### Repository selection and filtering

- Repositories are selected from CLI flags and/or `linter.owner_list` in config.
- If no owner is supplied, the current authenticated user is used.
- `--module` limits which modules are enabled.
- `--check` filters the `check_*` and `fix_*` function names within enabled modules.
- `--list-repos` prints the resolved repo set without running modules.

### Module language filtering

Modules declare which languages they apply to via the `LANGUAGES` attribute:

- Use `["all"]` for modules that apply to every repository.
- Use specific languages such as `["python"]` or `["terraform"]` to restrict execution.
- Language detection comes from GitHub's repository language API, not local file inspection.

### Configuration

Configuration file locations (in priority order):

1. `./github_linter.json` (local directory)
2. `~/.config/github_linter.json` (user config)

Each module can define `DEFAULT_CONFIG`, which is merged into the active config before the module runs. That lets modules ship sane defaults while still allowing overrides in the JSON config file.

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
