
""" Terraform-related tests """
from typing import Dict

from loguru import logger
import hcl2 # type: ignore
import json5 as json
import semver # type: ignore



from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..utils import DICTLIST, add_result


CATEGORY = "terraform"

LANGUAGES = [
    "HCL",
]

PROVIDER_FILE_LIST = [
    "providers.tf",
    "terraform/providers.tf",
    "terraform.tf",
    "terraform/terraform.tf",
]

# TODO: Try and find old versions of the AWS plugin, needs to be at least 3.41.0
# - https://newreleases.io/project/github/hashicorp/terraform-provider-aws/release/v3.41.0
# - https://aws.amazon.com/blogs/compute/coming-soon-expansion-of-aws-lambda-states-to-all-functions/

# HCLFILETYPE = Dict[str, List[Dict[str, str]]]

AWS_MIN_VERSION = "3.41.0"

def load_hclfile(
    github_object: GithubLinter,
    filename: str,
    ):
    """ loads the given filename using hcl2 """
    filecontent = github_object.cached_get_file(filename)
    if not filecontent or not filecontent.decoded_content:
        logger.debug("Couldn't find file (or it was empty): {}", filename)
        return {}

    logger.debug("Found {}", filename)
    # logger.debug(filecontent.decoded_content.decode("utf-8"))
    return hcl2.loads(filecontent.decoded_content.decode("utf-8"))


def check_providers_tf_exists(
    github_object: GithubLinter,
    errors_list: DICTLIST,
    _: DICTLIST,
) -> None:
    """ checks the data for the pyproject.toml file """
    if not github_object.current_repo:
        raise RepositoryNotSet

    for filename in PROVIDER_FILE_LIST:
        hclfile = load_hclfile(github_object, filename)
        if hclfile:
            return None
    add_result(
        errors_list,
        CATEGORY,
        f"Couldn't find a providers.tf file, looked in {','.join(PROVIDER_FILE_LIST)}"
    )
    return None

def check_providers_for_modules(
    github_object: GithubLinter,
    errors_list: DICTLIST,
    warnings_list: DICTLIST,
) -> None:
    """ Checks that there's providers listed under each "terraform" section in the providers.tf """
    provider_list = []
    found_files = []

    for filename in PROVIDER_FILE_LIST:
        hclfile = load_hclfile(github_object, filename)
        if not hclfile:
            continue
        logger.debug(json.dumps(hclfile, indent=4, default=str))

        if "terraform" not in hclfile:
            add_result(
                warnings_list,
                CATEGORY,
                f"Couldn't find 'terraform' section in {filename}...",
            )
            continue

        required_providers: Dict[str, Dict[str,str]] = {}
        for entry in hclfile["terraform"]:
            if "required_providers" in entry:
                required_providers = entry["required_providers"]
                break

        if not required_providers:
            add_result(
                warnings_list,
                CATEGORY,
                f"Couldn't find 'terraform.required_providers' section in {filename}...",
            )
            continue

        found_files.append(filename)

        # # make a list of the providers
        for provider in required_providers:
            for provider_name in provider:
                provider_list.append(provider_name)
            logger.debug(json.dumps(provider))
    logger.debug("Provider list: {}", provider_list)
    if not provider_list:
        add_result(
            errors_list,
            CATEGORY,
            f"Found providers.tf files but no provider configuration was found. Files to check: {','.join(found_files)}",
        )
        return
    logger.debug("Found providers")

    version = semver.parse("1.2.3")
    logger.debug(version)
    # TODO: use semver
