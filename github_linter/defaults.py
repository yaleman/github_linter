""" default linter configuration goes here """

from typing import List, TypedDict

class DefaultLinterConfig(TypedDict):
    """ typedef for DEFAULT_LINTER_CONFIG """
    check_forks: bool
    owner_list: List[str]

DEFAULT_LINTER_CONFIG: DefaultLinterConfig = {
    "check_forks" : False,
    "owner_list": []
}
