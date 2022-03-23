""" github_linter dependabot tests constants """

from typing import Dict, List

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
