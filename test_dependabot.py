""" testing dependabot """

from github_linter.dependabot import dependabot_load_file

def test_load_file():
    """ tests loading the dependabot file """
    dependabot_load_file(None, {}, {})
