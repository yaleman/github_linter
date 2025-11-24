"""Branch protection checks and fixes using both legacy rules and modern rulesets"""

from typing import Any, Dict, List, Optional, Set

from github.BranchProtection import BranchProtection
from github.GithubException import GithubException, UnknownObjectException
from loguru import logger
from pydantic import BaseModel
from ruyaml import YAML

from ..repolinter import RepoLinter

CATEGORY = "branch_protection"
LANGUAGES = ["all"]


class DefaultConfig(BaseModel):
    """Configuration for branch protection module"""

    enable_protection: bool = True  # Whether to enable protection
    allow_admin_bypass: bool = True  # Allow admin bypass
    require_pull_request: bool = True  # Require PR before merging
    required_approving_review_count: int = 0  # Number of required approvals
    dismiss_stale_reviews: bool = True  # Dismiss stale reviews on push
    require_code_owner_review: bool = False  # Require code owner review
    use_rulesets: bool = True  # Prefer rulesets over legacy branch protection
    migrate_to_rulesets: bool = True  # Migrate legacy protection to rulesets

    # Mapping of language to required status check names
    language_checks: Dict[str, List[str]] = {
        "Python": ["pylint", "pytest", "mypy"],
        "Docker": ["build_container"],
        # "Rust": ["cargo-test", "clippy"],
        # "JavaScript": ["test", "lint"],
        # "TypeScript": ["test", "lint"],
        # "Shell": ["shellcheck"],
        # "Go": ["test", "lint"],
    }

    # Whether to warn (instead of error) if protection exists but doesn't match
    warn_on_mismatch: bool = True


DEFAULT_CONFIG = DefaultConfig()


def _get_required_checks_for_repo(repo: RepoLinter, config: Dict[str, Any]) -> List[str]:
    """
    Get the list of required status checks based on repository languages.

    Args:
        repo: RepoLinter instance
        config: Module configuration

    Returns:
        List of required status check names
    """
    required_checks: List[str] = []
    repo_languages = list(repo.repository.get_languages().keys())

    language_checks = config.get("language_checks", {})

    for language in repo_languages:
        if language in language_checks:
            checks = language_checks[language]
            for check in checks:
                if check not in required_checks:
                    required_checks.append(check)

    logger.debug(
        "Required checks for {} (languages: {}): {}",
        repo.repository.full_name,
        ", ".join(repo_languages),
        ", ".join(required_checks) if required_checks else "none",
    )

    return required_checks


def _get_available_checks_for_repo(repo: RepoLinter) -> Set[str]:
    """
    Get the list of available status checks by parsing workflow files.

    This function attempts to discover actual check names that would run on pull requests
    by parsing GitHub Actions workflow files in .github/workflows/ directory.

    Args:
        repo: RepoLinter instance

    Returns:
        Set of available check names (job names from workflows)
    """
    available_checks: Set[str] = set()

    try:
        # Get all workflow files from .github/workflows/
        workflow_path = ".github/workflows"
        contents = repo.repository.get_contents(workflow_path)

        # Handle single file or list of files
        if not isinstance(contents, list):
            contents = [contents]

        for content_file in contents:
            # Only process YAML files
            if not content_file.name.endswith(('.yml', '.yaml')):
                continue

            try:
                # Parse the workflow file
                file_content = content_file.decoded_content.decode('utf-8')
                yaml_parser = YAML(pure=True)
                workflow_data = yaml_parser.load(file_content)

                if not isinstance(workflow_data, dict):
                    logger.debug("Workflow file {} has invalid structure", content_file.name)
                    continue

                # Extract job names from the 'jobs' section
                jobs = workflow_data.get('jobs', {})
                if isinstance(jobs, dict):
                    for job_name in jobs.keys():
                        available_checks.add(job_name)
                        logger.debug("Found check '{}' in workflow {}", job_name, content_file.name)

            except Exception as exc:
                logger.debug("Failed to parse workflow file {}: {}", content_file.name, exc)
                continue

        logger.debug(
            "Available checks for {}: {}",
            repo.repository.full_name,
            ", ".join(sorted(available_checks)) if available_checks else "none",
        )

    except UnknownObjectException:
        logger.debug("No .github/workflows directory found for {}", repo.repository.full_name)
    except GithubException as exc:
        logger.debug("Error accessing workflows for {}: {}", repo.repository.full_name, exc)
    except Exception as exc:
        logger.error("Unexpected error getting available checks for {}: {}", repo.repository.full_name, exc)

    return available_checks


def _validate_required_checks(
    repo: RepoLinter,
    required_checks: List[str],
    available_checks: Set[str],
) -> None:
    """
    Validate that required status checks actually exist in the repository.

    Compares the configured required checks against the available checks discovered
    from workflow files. If there are mismatches, generates a warning with suggestions.

    Args:
        repo: RepoLinter instance
        required_checks: List of check names required by configuration
        available_checks: Set of check names found in workflow files
    """
    if not required_checks:
        # No required checks, nothing to validate
        return

    # Find checks that are required but not available
    missing_checks = set(required_checks) - available_checks

    if missing_checks:
        # Generate a helpful warning message
        warning_parts = [
            f"Required status checks not found in workflow files: {', '.join(sorted(missing_checks))}"
        ]

        # Suggest available checks if any exist
        if available_checks:
            warning_parts.append(f"Available checks in workflows: {', '.join(sorted(available_checks))}")
        else:
            warning_parts.append("No workflow files found in .github/workflows/")

        warning_parts.append(
            "These checks will be required for branch protection but may never pass if workflows don't exist. "
            "Update the 'language_checks' configuration or create matching workflow jobs."
        )

        repo.warning(
            CATEGORY,
            " | ".join(warning_parts),
        )

        logger.debug(
            "Validation failed for {}: required={}, available={}, missing={}",
            repo.repository.full_name,
            sorted(required_checks),
            sorted(available_checks),
            sorted(missing_checks),
        )


def _get_rulesets(repo: RepoLinter) -> List[Dict[str, Any]]:
    """
    Get repository rulesets using PyGithub's internal _requester.

    Fetches full ruleset details by first getting the list, then fetching
    each ruleset individually to get complete rule and condition information.

    Args:
        repo: RepoLinter instance

    Returns:
        List of rulesets with full details (empty if none exist or API call fails)
    """
    try:
        # First, get the list of rulesets (summary view)
        list_url = f"{repo.repository.url}/rulesets"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        _, response = repo.repository._requester.requestJsonAndCheck("GET", list_url, headers=headers)
        ruleset_summaries = response if isinstance(response, list) else []

        logger.debug(
            "Fetched {} ruleset summaries for {}",
            len(ruleset_summaries),
            repo.repository.full_name,
        )

        # Now fetch full details for each ruleset
        full_rulesets: List[Dict[str, Any]] = []
        for summary in ruleset_summaries:
            ruleset_id = summary.get("id")
            if not ruleset_id:
                logger.warning("Ruleset missing ID, skipping: {}", summary)
                continue

            try:
                detail_url = f"{repo.repository.url}/rulesets/{ruleset_id}"
                _, detail_response = repo.repository._requester.requestJsonAndCheck("GET", detail_url, headers=headers)
                if isinstance(detail_response, dict):
                    full_rulesets.append(detail_response)
                    logger.debug(
                        "Fetched full details for ruleset '{}' (id={}): has {} rules, conditions={}",
                        detail_response.get("name"),
                        ruleset_id,
                        len(detail_response.get("rules", [])) if detail_response.get("rules") else 0,
                        "present" if detail_response.get("conditions") else "None",
                    )
            except GithubException as exc:
                logger.error("Error fetching ruleset {}: {}", ruleset_id, exc)
                continue

        return full_rulesets
    except GithubException as exc:
        if exc.status == 404:
            logger.debug("No rulesets found for {}", repo.repository.full_name)
            return []
        else:
            logger.error("Error fetching rulesets for {}: {}", repo.repository.full_name, exc)
            return []
    except Exception as exc:
        logger.error("Unexpected error fetching rulesets: {}", exc)
        return []


def _get_admin_bypass_actors() -> List[Dict[str, Any]]:
    """
    Get bypass actors list to allow repository admins to bypass rulesets.

    Returns:
        List with repository admin role configured as bypass actor
    """
    return [
        {
            "actor_id": 5,  # Repository admin role ID
            "actor_type": "RepositoryRole",
            "bypass_mode": "always",
        }
    ]


def _create_ruleset(
    repo: RepoLinter,
    name: str,
    require_pr: bool,
    required_approving_review_count: int,
    dismiss_stale_reviews: bool,
    require_code_owner_review: bool,
    required_checks: List[str],
    bypass_actors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a repository ruleset using PyGithub's internal _requester.

    Args:
        repo: RepoLinter instance
        name: Ruleset name
        require_pr: Whether to require pull requests
        required_approving_review_count: Number of required approvals
        dismiss_stale_reviews: Whether to dismiss stale reviews on push
        require_code_owner_review: Whether to require code owner review
        required_checks: List of required status check names
        bypass_actors: List of actors who can bypass the ruleset

    Returns:
        Created ruleset data, or None if creation failed
    """
    rules: List[Dict[str, Any]] = []

    # Add pull request rule if requested
    if require_pr:
        pr_rule: Dict[str, Any] = {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": required_approving_review_count,
                "dismiss_stale_reviews_on_push": dismiss_stale_reviews,
                "require_code_owner_review": require_code_owner_review,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
            },
        }
        rules.append(pr_rule)

    # Add status checks rule if there are any checks
    if required_checks:
        status_check_rule: Dict[str, Any] = {
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [{"context": check} for check in required_checks],
                "strict_required_status_checks_policy": False,
            },
        }
        rules.append(status_check_rule)

    # Build the ruleset payload
    ruleset_data = {
        "name": name,
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": [f"refs/heads/{repo.repository.default_branch}"], "exclude": []}},
        "rules": rules,
        "bypass_actors": bypass_actors or [],
    }

    try:
        url = f"{repo.repository.url}/rulesets"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        _, response = repo.repository._requester.requestJsonAndCheck(
            "POST",
            url,
            headers=headers,
            input=ruleset_data,
        )
        return response if isinstance(response, dict) else None
    except GithubException as exc:
        logger.error(
            "Failed to create ruleset for {}: {}",
            repo.repository.full_name,
            exc.data.get("message", str(exc)) if hasattr(exc, "data") and isinstance(exc.data, dict) else str(exc),
        )
        return None
    except Exception as exc:
        logger.error("Unexpected error creating ruleset: {}", exc)
        return None


def _get_branch_protection(repo: RepoLinter) -> Optional[BranchProtection]:
    """
    Get branch protection for the default branch.

    Args:
        repo: RepoLinter instance

    Returns:
        BranchProtection object if protection exists, None otherwise
    """
    try:
        branch = repo.repository.get_branch(repo.repository.default_branch)
        protection = branch.get_protection()
        return protection
    except GithubException as exc:
        if exc.status == 404:
            logger.debug(
                "No branch protection found for {} on branch {}",
                repo.repository.full_name,
                repo.repository.default_branch,
            )
            return None
        else:
            logger.error(
                "Error getting branch protection for {}: {}",
                repo.repository.full_name,
                exc,
            )
            raise


def _delete_branch_protection(repo: RepoLinter) -> bool:
    """
    Delete legacy branch protection for the default branch.

    Args:
        repo: RepoLinter instance

    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        branch = repo.repository.get_branch(repo.repository.default_branch)
        branch.remove_protection()
        logger.info(
            "Deleted legacy branch protection for {} on branch {}",
            repo.repository.full_name,
            repo.repository.default_branch,
        )
        return True
    except GithubException as exc:
        if exc.status == 404:
            logger.debug(
                "No branch protection to delete for {} on branch {}",
                repo.repository.full_name,
                repo.repository.default_branch,
            )
            return True  # Already gone, consider it successful
        else:
            logger.error(
                "Error deleting branch protection for {}: {}",
                repo.repository.full_name,
                exc,
            )
            return False


def _check_protection_matches_config(
    protection: BranchProtection,
    enforce_admins: bool,
    require_pr: bool,
    required_approving_review_count: int,
    required_checks: List[str],
) -> tuple[bool, List[str]]:
    """
    Check if existing protection matches desired configuration.

    Args:
        protection: Existing BranchProtection object
        enforce_admins: Whether admin bypass should be enabled
        require_pr: Whether PR is required
        required_approving_review_count: Number of required approvals
        required_checks: List of required status check names

    Returns:
        Tuple of (matches, list of differences)
    """
    differences: List[str] = []

    # Check enforce_admins setting
    # Note: protection.enforce_admins may be a boolean or an object with enabled attribute
    if hasattr(protection.enforce_admins, "enabled"):
        current_enforce_admins = getattr(protection.enforce_admins, "enabled", False)
    else:
        current_enforce_admins = bool(protection.enforce_admins)

    if current_enforce_admins != enforce_admins:
        differences.append(f"enforce_admins: current={current_enforce_admins}, expected={enforce_admins}")

    # Check pull request requirements
    if require_pr:
        if not protection.required_pull_request_reviews:
            differences.append("pull request reviews not required")
        else:
            current_approvals = protection.required_pull_request_reviews.required_approving_review_count
            if current_approvals != required_approving_review_count:
                differences.append(f"required approvals: current={current_approvals}, expected={required_approving_review_count}")

    # Check required status checks
    if protection.required_status_checks:
        current_checks = []
        if hasattr(protection.required_status_checks, "checks") and protection.required_status_checks.checks:
            # Newer API format
            current_checks = [check.context for check in protection.required_status_checks.checks]
        elif hasattr(protection.required_status_checks, "contexts") and protection.required_status_checks.contexts:
            # Legacy API format
            current_checks = list(protection.required_status_checks.contexts)

        # Compare sets to ignore order
        if set(current_checks) != set(required_checks):
            missing = set(required_checks) - set(current_checks)
            extra = set(current_checks) - set(required_checks)
            if missing:
                differences.append(f"missing required checks: {', '.join(missing)}")
            if extra:
                differences.append(f"extra checks not in config: {', '.join(extra)}")
    elif required_checks:
        differences.append(f"no status checks configured, expected: {', '.join(required_checks)}")

    return len(differences) == 0, differences


def _check_ruleset_matches_config(
    ruleset: Dict[str, Any],
    require_pr: bool,
    required_approving_review_count: int,
    required_checks: List[str],
    allow_admin_bypass: bool,
) -> tuple[bool, List[str]]:
    """
    Check if existing ruleset matches desired configuration.

    Args:
        ruleset: Ruleset data from API
        require_pr: Whether PR is required
        required_approving_review_count: Number of required approvals
        required_checks: List of required status check names
        allow_admin_bypass: Whether repository admins should be able to bypass

    Returns:
        Tuple of (matches, list of differences)
    """
    differences: List[str] = []

    rules = ruleset.get("rules", [])

    # Check for PR rule
    pr_rule = next((r for r in rules if r.get("type") == "pull_request"), None)
    if require_pr:
        if not pr_rule:
            differences.append("pull request rule not found")
        else:
            params = pr_rule.get("parameters", {})
            current_approvals = params.get("required_approving_review_count", 0)
            if current_approvals != required_approving_review_count:
                differences.append(f"required approvals: current={current_approvals}, expected={required_approving_review_count}")

    # Check for status checks rule
    status_rule = next((r for r in rules if r.get("type") == "required_status_checks"), None)
    if required_checks:
        if not status_rule:
            differences.append("required status checks rule not found")
        else:
            params = status_rule.get("parameters", {})
            current_checks_data = params.get("required_status_checks", [])
            current_checks = [check.get("context", "") for check in current_checks_data]

            if set(current_checks) != set(required_checks):
                missing = set(required_checks) - set(current_checks)
                extra = set(current_checks) - set(required_checks)
                if missing:
                    differences.append(f"missing required checks: {', '.join(missing)}")
                if extra:
                    differences.append(f"extra checks not in config: {', '.join(extra)}")

    # Check bypass actors for admin bypass
    bypass_actors = ruleset.get("bypass_actors", [])
    has_admin_bypass = any(actor.get("actor_type") == "RepositoryRole" and actor.get("actor_id") == 5 for actor in bypass_actors)
    if allow_admin_bypass and not has_admin_bypass:
        differences.append("admin bypass not configured (repository admin role not in bypass_actors)")
    elif not allow_admin_bypass and has_admin_bypass:
        differences.append("admin bypass enabled but config has allow_admin_bypass=False")

    return len(differences) == 0, differences


def check_default_branch_protection(repo: RepoLinter) -> None:
    """
    Check if branch protection is enabled on the default branch.

    Checks both legacy branch protection and modern rulesets.

    Verifies:
    - Branch protection or rulesets exist
    - Admin bypass is configured correctly (legacy only)
    - Pull request requirements
    - Required status checks match repository languages
    """
    repo.skip_on_archived()

    config = repo.config.get("branch_protection", {})
    if not config.get("enable_protection", True):
        logger.debug("Branch protection checks disabled in config for {}", repo.repository.full_name)
        return

    use_rulesets = config.get("use_rulesets", True)
    require_pr = config.get("require_pull_request", True)
    required_approving_review_count = config.get("required_approving_review_count", 1)
    # Note: enforce_admins=False means admins CAN bypass, enforce_admins=True means they CANNOT
    # So we invert allow_admin_bypass to get the correct enforce_admins value
    allow_admin_bypass = config.get("allow_admin_bypass", True)
    enforce_admins = not allow_admin_bypass
    required_checks = _get_required_checks_for_repo(repo, config)

    # Validate that required checks exist in workflow files
    available_checks = _get_available_checks_for_repo(repo)
    _validate_required_checks(repo, required_checks, available_checks)

    # Check for rulesets first if enabled
    rulesets = _get_rulesets(repo) if use_rulesets else []
    protection = _get_branch_protection(repo)

    if not rulesets and protection is None:
        repo.error(
            CATEGORY,
            f"No protection configured on default branch '{repo.repository.default_branch}' (neither rulesets nor legacy branch protection)",
        )
        return

    # If we have both, check rulesets first
    if rulesets:
        # Find ruleset targeting the default branch
        # Note: conditions can be None in the list API response, in which case
        # we need to assume the ruleset applies to all branches (including default)
        default_branch_rulesets = [
            rs
            for rs in rulesets
            if rs.get("target") == "branch"
            and (
                rs.get("conditions") is None  # No conditions = applies to all branches
                or any(
                    f"refs/heads/{repo.repository.default_branch}" in incl or repo.repository.default_branch in incl
                    for incl in (rs.get("conditions") or {}).get("ref_name", {}).get("include", [])
                )
            )
        ]

        logger.debug(
            "Filtered rulesets for default branch '{}': found {} out of {} total rulesets",
            repo.repository.default_branch,
            len(default_branch_rulesets),
            len(rulesets),
        )

        if default_branch_rulesets:
            for ruleset in default_branch_rulesets:
                matches, differences = _check_ruleset_matches_config(
                    ruleset,
                    require_pr,
                    required_approving_review_count,
                    required_checks,
                    allow_admin_bypass,
                )

                if not matches:
                    warn_on_mismatch = config.get("warn_on_mismatch", True)
                    message = f"Ruleset '{ruleset.get('name')}' on '{repo.repository.default_branch}' doesn't match config: {'; '.join(differences)}"

                    if warn_on_mismatch:
                        repo.warning(CATEGORY, message)
                    else:
                        repo.error(CATEGORY, message)

    # Also check legacy branch protection if it exists
    if protection is not None:
        migrate_to_rulesets = config.get("migrate_to_rulesets", False)

        # Warn about using legacy protection if rulesets are preferred and no rulesets exist
        if use_rulesets and not rulesets:
            if migrate_to_rulesets:
                repo.warning(
                    CATEGORY,
                    f"Repository uses legacy branch protection on '{repo.repository.default_branch}' - migration enabled, run with --fix to migrate to rulesets",
                )
            else:
                repo.warning(
                    CATEGORY,
                    f"Repository uses legacy branch protection on '{repo.repository.default_branch}' - consider enabling migration with 'migrate_to_rulesets: true' in config",
                )

        matches, differences = _check_protection_matches_config(
            protection,
            enforce_admins,
            require_pr,
            required_approving_review_count,
            required_checks,
        )

        if not matches:
            warn_on_mismatch = config.get("warn_on_mismatch", True)
            message = f"Legacy branch protection on '{repo.repository.default_branch}' doesn't match config: {'; '.join(differences)}"

            if warn_on_mismatch:
                repo.warning(CATEGORY, message)
            else:
                repo.error(CATEGORY, message)


def check_legacy_protection_cleanup(repo: RepoLinter) -> None:
    """
    Check if legacy branch protection should be removed when rulesets exist.

    When migrate_to_rulesets is enabled and rulesets are already in place,
    this check warns if legacy branch protection still exists and should be cleaned up.
    """
    repo.skip_on_archived()

    config = repo.config.get("branch_protection", {})
    if not config.get("enable_protection", True):
        return

    migrate_to_rulesets = config.get("migrate_to_rulesets", False)
    use_rulesets = config.get("use_rulesets", True)

    # Only check if migration is enabled
    if not migrate_to_rulesets or not use_rulesets:
        return

    rulesets = _get_rulesets(repo)
    protection = _get_branch_protection(repo)

    # If we have rulesets AND legacy protection, warn that legacy should be removed
    if rulesets and protection is not None:
        # Find rulesets targeting the default branch
        # Note: conditions can be None in the list API response, in which case
        # we need to assume the ruleset applies to all branches (including default)
        default_branch_rulesets = [
            rs
            for rs in rulesets
            if rs.get("target") == "branch"
            and (
                rs.get("conditions") is None  # No conditions = applies to all branches
                or any(
                    f"refs/heads/{repo.repository.default_branch}" in incl or repo.repository.default_branch in incl
                    for incl in (rs.get("conditions") or {}).get("ref_name", {}).get("include", [])
                )
            )
        ]

        logger.debug(
            "check_legacy_protection_cleanup: Filtered rulesets for default branch '{}': found {} out of {} total rulesets",
            repo.repository.default_branch,
            len(default_branch_rulesets),
            len(rulesets),
        )

        if default_branch_rulesets:
            repo.warning(
                CATEGORY,
                f"Legacy branch protection still exists on '{repo.repository.default_branch}' alongside rulesets - run with --fix to remove legacy protection",
            )


def fix_default_branch_protection(repo: RepoLinter) -> None:
    """
    Enable branch protection on the default branch if not already enabled.

    Configures:
    - Admin bypass (allow admins to bypass protection) - legacy only
    - Pull request requirements
    - Required status checks based on repository languages

    Prefers rulesets over legacy branch protection when use_rulesets is enabled.
    Can migrate from legacy protection to rulesets if migrate_to_rulesets is enabled.

    Note: This will NOT modify existing protection rules per the warn_on_mismatch setting.
    """
    repo.skip_on_archived()

    config = repo.config.get("branch_protection", {})
    if not config.get("enable_protection", True):
        logger.debug("Branch protection disabled in config for {}", repo.repository.full_name)
        return

    use_rulesets = config.get("use_rulesets", True)
    migrate_to_rulesets = config.get("migrate_to_rulesets", False)
    require_pr = config.get("require_pull_request", True)
    required_approving_review_count = config.get("required_approving_review_count", 1)
    dismiss_stale_reviews = config.get("dismiss_stale_reviews", True)
    require_code_owner_review = config.get("require_code_owner_review", False)
    # Note: enforce_admins=False means admins CAN bypass, enforce_admins=True means they CANNOT
    # So we invert allow_admin_bypass to get the correct enforce_admins value
    allow_admin_bypass = config.get("allow_admin_bypass", True)
    enforce_admins = not allow_admin_bypass
    required_checks = _get_required_checks_for_repo(repo, config)

    # Validate that required checks exist in workflow files
    available_checks = _get_available_checks_for_repo(repo)
    _validate_required_checks(repo, required_checks, available_checks)

    rulesets = _get_rulesets(repo) if use_rulesets else []
    protection = _get_branch_protection(repo)

    # If migration is requested and we have legacy protection but no rulesets
    if migrate_to_rulesets and protection is not None and not rulesets and use_rulesets:
        logger.info("Migrating {} from legacy branch protection to rulesets", repo.repository.full_name)
        bypass_actors = _get_admin_bypass_actors() if allow_admin_bypass else None
        result = _create_ruleset(
            repo,
            f"Protect {repo.repository.default_branch}",
            require_pr,
            required_approving_review_count,
            dismiss_stale_reviews,
            require_code_owner_review,
            required_checks,
            bypass_actors,
        )
        if result:
            # Delete the legacy branch protection after successful ruleset creation
            if _delete_branch_protection(repo):
                repo.fix(
                    CATEGORY,
                    f"Migrated '{repo.repository.default_branch}' from legacy branch protection to ruleset '{result.get('name')}' and removed legacy protection",
                )
            else:
                repo.fix(
                    CATEGORY,
                    f"Created ruleset '{result.get('name')}' for '{repo.repository.default_branch}' but failed to remove legacy protection (manual cleanup required)",
                )
            return
        else:
            repo.error(CATEGORY, f"Failed to migrate '{repo.repository.default_branch}' to rulesets")
            return

    # If we already have rulesets or protection, skip
    if rulesets or protection is not None:
        logger.debug(
            "Protection already exists for {} on branch '{}', skipping fix",
            repo.repository.full_name,
            repo.repository.default_branch,
        )
        return

    # No protection exists, create it
    if use_rulesets:
        # Create a ruleset
        bypass_actors = _get_admin_bypass_actors() if allow_admin_bypass else None
        result = _create_ruleset(
            repo,
            f"Protect {repo.repository.default_branch}",
            require_pr,
            required_approving_review_count,
            dismiss_stale_reviews,
            require_code_owner_review,
            required_checks,
            bypass_actors,
        )
        if result:
            rules_desc = []
            if require_pr:
                rules_desc.append(f"require {required_approving_review_count} approval(s)")
            if required_checks:
                rules_desc.append(f"required checks: {', '.join(required_checks)}")

            repo.fix(
                CATEGORY,
                f"Created ruleset '{result.get('name')}' for '{repo.repository.default_branch}' with {'; '.join(rules_desc) if rules_desc else 'basic protection'}",
            )
        else:
            repo.error(CATEGORY, f"Failed to create ruleset for '{repo.repository.default_branch}'")
    else:
        # Use legacy branch protection
        try:
            branch = repo.repository.get_branch(repo.repository.default_branch)

            # Build parameters for edit_protection
            protection_params: Dict[str, Any] = {
                "enforce_admins": enforce_admins,
            }

            # Add PR requirements if requested
            if require_pr:
                protection_params["required_approving_review_count"] = required_approving_review_count
                protection_params["dismiss_stale_reviews"] = dismiss_stale_reviews
                protection_params["require_code_owner_reviews"] = require_code_owner_review

            # Add status checks if any
            if required_checks:
                protection_params["strict"] = False
                protection_params["checks"] = list(required_checks)

            branch.edit_protection(**protection_params)

            rules_desc = []
            if enforce_admins:
                rules_desc.append("admin bypass")
            if require_pr:
                rules_desc.append(f"require {required_approving_review_count} approval(s)")
            if required_checks:
                rules_desc.append(f"required checks: {', '.join(required_checks)}")

            repo.fix(
                CATEGORY,
                f"Enabled legacy branch protection on '{repo.repository.default_branch}' with {'; '.join(rules_desc) if rules_desc else 'basic protection'}",
            )

        except GithubException as exc:
            logger.error(
                "Failed to enable branch protection for {} on branch '{}': {}",
                repo.repository.full_name,
                repo.repository.default_branch,
                exc,
            )
            repo.error(
                CATEGORY,
                f"Failed to enable branch protection: {exc.data.get('message', str(exc)) if hasattr(exc, 'data') and isinstance(exc.data, dict) else str(exc)}",
            )


def fix_legacy_protection_cleanup(repo: RepoLinter) -> None:
    """
    Remove legacy branch protection when rulesets exist.

    This fix function runs when migrate_to_rulesets is enabled and both
    rulesets and legacy branch protection exist. It removes the legacy
    protection to complete the migration.
    """
    repo.skip_on_archived()

    config = repo.config.get("branch_protection", {})
    if not config.get("enable_protection", True):
        return

    migrate_to_rulesets = config.get("migrate_to_rulesets", False)
    use_rulesets = config.get("use_rulesets", True)

    # Only fix if migration is enabled
    if not migrate_to_rulesets or not use_rulesets:
        return

    rulesets = _get_rulesets(repo)
    protection = _get_branch_protection(repo)

    # If we have rulesets AND legacy protection, remove the legacy protection
    if rulesets and protection is not None:
        # Find rulesets targeting the default branch
        # Note: conditions can be None in the list API response, in which case
        # we need to assume the ruleset applies to all branches (including default)
        default_branch_rulesets = [
            rs
            for rs in rulesets
            if rs.get("target") == "branch"
            and (
                rs.get("conditions") is None  # No conditions = applies to all branches
                or any(
                    f"refs/heads/{repo.repository.default_branch}" in incl or repo.repository.default_branch in incl
                    for incl in (rs.get("conditions") or {}).get("ref_name", {}).get("include", [])
                )
            )
        ]

        logger.debug(
            "fix_legacy_protection_cleanup: Filtered rulesets for default branch '{}': found {} out of {} total rulesets",
            repo.repository.default_branch,
            len(default_branch_rulesets),
            len(rulesets),
        )

        if not default_branch_rulesets:
            logger.warning(
                "fix_legacy_protection_cleanup: No rulesets match default branch '{}'. Skipping legacy protection cleanup. "
                "This might indicate a bug in the filter logic.",
                repo.repository.default_branch,
            )
            return

        if default_branch_rulesets:
            if _delete_branch_protection(repo):
                repo.fix(
                    CATEGORY,
                    f"Removed legacy branch protection from '{repo.repository.default_branch}' (rulesets already in place)",
                )
            else:
                repo.error(
                    CATEGORY,
                    f"Failed to remove legacy branch protection from '{repo.repository.default_branch}'",
                )
