""" Terraform-related tests """

from loguru import logger
# from github.Repository import Repository
from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..utils import DICTLIST # , add_result


CATEGORY = "terraform"

LANGAUGES = [
    "HCL",
]

# TODO: Try and find old versions of the AWS plugin, needs to be at least 3.41.0
# - https://newreleases.io/project/github/hashicorp/terraform-provider-aws/release/v3.41.0
# - https://aws.amazon.com/blogs/compute/coming-soon-expansion-of-aws-lambda-states-to-all-functions/

def check_providers_tf_exists(
    github_object: GithubLinter,
    _: DICTLIST,
    __: DICTLIST,
) -> None:
    """ checks the data for the pyproject.toml file """
    if not github_object.current_repo:
        raise RepositoryNotSet

    for filename in [
        "providers.tf",
        "terraform/providers.tf",
    ]:
        filecontent = github_object.cached_get_file(filename)
        if not filecontent or not filecontent.decoded_content:
            continue

        logger.debug("Found {}", filename)
        logger.debug(filecontent.decoded_content.decode("utf-8"))
