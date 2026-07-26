"""default linter configuration goes here"""

from typing import TypedDict


class DefaultLinterConfig(TypedDict):
    """typedef for DEFAULT_LINTER_CONFIG"""

    github: dict[str, str] | None
    check_forks: bool
    owner_list: list[str]
    fix_branch: str | None


DEFAULT_LINTER_CONFIG: DefaultLinterConfig = {
    "github": {},
    "check_forks": False,
    "owner_list": [],
    "fix_branch": None,
}
