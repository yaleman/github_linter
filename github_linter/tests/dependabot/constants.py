""" github_linter dependabot tests constants """

from typing import Dict, List


DEPENDABOT_SCHEDULE_INTERVALS = [
    "daily",
    "weekly",  # monday by default, or schedule.day if you want to change it
    "monthly",  # first of the month
]

PACKAGE_ECOSYSTEM: Dict[str, List[str]] = {
    "bundler": [],
    "cargo": ["rust"],
    "composer": [],
    "docker": [],
    "mix": [],
    "elm": [],
    "gitsubmodule": [],
    "github-actions": [],
    "gomod": [],
    "gradle": [],
    "maven": [],
    "npm": [],
    "nuget": [],
    "pip": ["python"],
    "terraform": ["HCL"],
}
