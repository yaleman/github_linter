""" testing pyproject """

from io import BytesIO

from github.ContentFile import ContentFile


class TestRepoFoo:
    """ just for testing """
    name = "foobar"

    # def get_contents(filename: str):
    #     """ kinda like a file, but not really """
    #     if filename == "README.md":
    #         readme = ContentFile("","","","",)
    #         readme._content.value = open("README.md", encoding="utf8").read()
    #         return readme
    #     return BytesIO()

from github_linter.tests.pyproject import validate_project_name, validate_readme_configured

def test_validate_project_name_fails_when_bad():
    """ if the name doesn't match, then we should yell """

    testproject = {
        "project" : {
            "name" : "zotbar"
        }
    }
    assert not validate_project_name(None, TestRepoFoo, testproject, {}, {})


def test_validate_project_name_fails_when_good():
    """ if the name matches we're good """

    testproject = {
        "project" : {
            "name" : "foobar"
        }
    }
    assert validate_project_name(None, TestRepoFoo, testproject, {}, {})

def test_validate_project_name_fails_when_good():
    """ if the name is missing we yell """

    testproject = {
        "project" : {
            # "name" : "foobar"
        }
    }
    assert not validate_project_name(None, TestRepoFoo, testproject, {}, {})

def test_validate_readme_configured_invalid():
    """ checks the readme is set and is invalid """
    class TestGithub:
        """ test instance """
        config = {
            "pyproject.toml" : {
            "readme" : "README.md"
            }
        }
    testproject = {
        "project" : {
            "name" : "zotbar",
            "readme" : "foobar"
        }
    }
    assert not validate_readme_configured(TestGithub, TestRepoFoo, testproject, {}, {})

def test_validate_readme_configured():
    """ checks the readme is set and is invalid """
    class TestGithub:
        """ test instance """
        config = {
            "pyproject.toml" : {
            "readme" : "README.md"
            }
        }
    testproject = {
        "project" : {
            "name" : "zotbar",
            "readme" : "README.md"
        }
    }
    assert validate_readme_configured(TestGithub, TestRepoFoo, testproject, {}, {})

