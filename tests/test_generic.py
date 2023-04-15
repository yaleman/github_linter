""" testing pyproject """

from utils import generate_test_repo


from github_linter.tests.docs import generate_contributing_file
from github_linter.tests.generic import FundingDict, generate_funding_file, parse_funding_file



EXAMPLE_INPUT_FILE_ONE = """# These are supported funding model platforms

github: # Replace with up to 4 GitHub Sponsors-enabled usernames e.g., [user1, user2]
patreon: # Replace with a single Patreon username
open_collective: # Replace with a single Open Collective username
ko_fi: # Replace with a single Ko-fi username
tidelift: # Replace with a single Tidelift platform-name/package-name e.g., npm/babel
community_bridge: # Replace with a single Community Bridge project-name e.g., cloud-foundry
liberapay: # Replace with a single Liberapay username
issuehunt: # Replace with a single IssueHunt username
otechie: # Replace with a single Otechie username
custom: ["https://www.paypal.me/asdfasdfasdfsdf"] # Replace with up to 4 custom sponsorship URLs e.g., ['link1', 'link2']"""

EXAMPLE_OUTPUT_FILE_ONE = """custom: [https://www.paypal.me/asdfasdfasdfsdf]   # Replace with up to 4 custom sponsorship URLs e.g., ['link1', 'link2']
"""

def test_parse_funding_file() -> None:
    """ basic test """

    result = parse_funding_file(EXAMPLE_INPUT_FILE_ONE)
    assert "github" in result
    assert "custom" in result
    if isinstance(result["custom"], list):
        assert len(result["custom"]) == 1
    assert result["otechie"] is None

def test_generate_funding_file() -> None:
    """ tests output matches input """
    result = parse_funding_file(EXAMPLE_INPUT_FILE_ONE)
    test_parse_funding_file()
    output = generate_funding_file(result)
    assert output == EXAMPLE_OUTPUT_FILE_ONE

def test_generate_funding_file_simple_with_quote() -> None:
    """ tests generator """
    result = parse_funding_file("# test funding file\ngithub: yaleman") # need to put the leading newline to make it not be a list... because YAML?
    test_parse_funding_file()
    output = generate_funding_file(result)
    assert output == "github: yaleman\n"

def test_generate_funding_file_simple() -> None:
    """ tests generator """
    result: FundingDict = parse_funding_file(" github: yaleman") # need to put the leading newline to make it not be a list... because YAML?
    test_parse_funding_file()
    output = generate_funding_file(result)
    assert output == "github: yaleman\n"

def test_generate_contributing_file() -> None:
    """ testing thing """

    filecontents =  generate_contributing_file(generate_test_repo())
    assert filecontents
    assert "testuser/test1" in filecontents
