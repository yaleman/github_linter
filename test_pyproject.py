""" testing pyproject """

# from io import BytesIO

# from github.ContentFile import ContentFile
# from github_linter.tests.pyproject import validate_project_name, validate_readme_configured


# pylint: disable=too-few-public-methods
# class TestRepoFoo:
#     """ just for testing """
#     name = "foobar"

    # def get_contents(filename: str):
    #     """ kinda like a file, but not really """
    #     if filename == "README.md":
    #         readme = ContentFile("","","","",)
    #         readme._content.value = open("README.md", encoding="utf8").read()
    #         return readme
    #     return BytesIO()

# pylint: disable=too-few-public-methods
# class TestGithub:
#     """ test instance """
#     config = {
#         "pyproject.toml" : {
#         "readme" : "README.md"
#         }
#     }

# def test_validate_project_name_fails_when_bad():
#     """ if the name doesn't match, then we should yell """

#     testproject = {
#         "project" : {
#             "name" : "zotbar"
#         }
#     }
#     assert not validate_project_name(None, TestRepoFoo, testproject, {}, {})


# def test_validate_project_name_good():
#     """ if the name matches we're good """
#     testproject = {
#         "name" : "foobar"
#     }
#     assert validate_project_name(None, TestRepoFoo, testproject, {}, {})

# def test_validate_project_name_fails_when_missing():
#     """ if the name is missing we yell """

#     testproject = {
#             # "name" : "foobar"
#     }
#     assert not validate_project_name(None, TestRepoFoo, testproject, {}, {})

# def test_validate_readme_configured_invalid():
#     """ checks the readme is set and is invalid """
#     testproject = {
#         "name" : "zotbar",
#         "readme" : "foobar"
#     }

#     errors_object = {}
#     warnings_object = {}
#     result = validate_readme_configured(TestGithub, TestRepoFoo, testproject, errors_object, warnings_object)
#     assert  errors_object
#     assert not warnings_object
#     assert not result

# def test_validate_readme_configured():
#     """ checks the readme is set and is invalid """

#     testproject = {
#             "name" : "zotbar",
#             "readme" : "README.md"
#     }
#     errors_object = {}
#     warnings_object = {}
#     result = validate_readme_configured(TestGithub, testproject, errors_object, warnings_object)
#     assert not errors_object
#     assert not warnings_object
#     assert result
