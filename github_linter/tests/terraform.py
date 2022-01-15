""" Terraform-related tests """

from typing import Dict
import re

import sys

from loguru import logger
import hcl2 # type: ignore
import json5 as json
from semver.version import Version # type: ignore



from .. import RepoLinter



CATEGORY = "terraform"

# this is the terraform version that linter recommends if you don't set it in config
DEFAULT_MIN_VERSION = Version.parse("0.14.0")

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
    repo: RepoLinter,
    filename: str,
    ):
    """ loads the given filename using hcl2 """
    filecontent = repo.cached_get_file(filename)
    if not filecontent or not filecontent.decoded_content:
        logger.debug("Couldn't find file (or it was empty): {}", filename)
        return {}

    logger.debug("Found {}", filename)
    # logger.debug(filecontent.decoded_content.decode("utf-8"))
    return hcl2.loads(filecontent.decoded_content.decode("utf-8"))


def check_providers_tf_exists(
    repo: RepoLinter,
) -> None:
    """ checks the data for the pyproject.toml file """

    for filename in PROVIDER_FILE_LIST:
        hclfile = load_hclfile(repo, filename)
        if hclfile:
            return None
    repo.error(CATEGORY,
        f"Couldn't find a providers.tf file, looked in {','.join(PROVIDER_FILE_LIST)}"
    )
    return None

def check_providers_for_modules(
    repo: RepoLinter,
) -> None:
    """ Checks that there's providers listed under each "terraform" section in the providers.tf """
    provider_list = []
    found_files = []

    for filename in PROVIDER_FILE_LIST:
        hclfile = load_hclfile(repo, filename)
        if not hclfile:
            continue
        logger.debug(json.dumps(hclfile, indent=4, default=str))

        if "terraform" not in hclfile:
            repo.warning(
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
            repo.warning(
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
        repo.warning(
            CATEGORY,
            f"Found providers.tf files but no provider configuration was found. Files to check: {','.join(found_files)}",
        )
        return
    logger.debug("Found providers")

    version = Version.parse("1.2.3")
    logger.debug(version)
    # TODO: use semver

def check_terraform_version(
    repo: RepoLinter,
) -> None:
    """ Checks that there's a 'required_version' setting in the terraform section of providers.tf, which sets a minimum version of terraform itself """

    found_required_version = False
    found_version = Version.parse("0.0.0")

    required_version = DEFAULT_MIN_VERSION
    if "terraform" in repo.config:
        if "required_version" in repo.config["terraform"]:
            try:
                required_version = Version.parse(repo.config["terraform"]["required_version"])
                logger.debug("Configured required_version: {}", required_version)
            except ValueError as semver_parse_error:
                logger.error("Failed to parse linter config terraform.required_version: {}. Bailing", semver_parse_error)
                sys.exit(1)


    for filename in PROVIDER_FILE_LIST:
        hclfile = load_hclfile(repo, filename)
        if not hclfile:
            continue
        logger.debug(json.dumps(hclfile, indent=4, default=str))

        if "terraform" not in hclfile:
            repo.warning(
                CATEGORY,
                f"Couldn't find 'terraform' section in {filename}...",
            )
            continue


        for tf_config in hclfile["terraform"]:

            if "required_version" not in tf_config:
                # return logger.debug("{} not found in {}", "required_version", filename )
                continue

            found_required_version = True
            tmp_value = tf_config["required_version"].split(" ")[-1]
            logger.debug("Found required_version in {}: {}", filename, tmp_value)


            # add the trailing .0 that semver likes
            if not re.match(pattern=r"\d+\.\d+\.\d+", string=tmp_value):
                logger.debug("Adding a .0 to the version for semver")
                tmp_value = f"{tmp_value}.0"
            logger.debug("Parsing {}", tmp_value)
            parsed_value = Version.parse(tmp_value)
            # https://python-semver.readthedocs.io/en/latest/usage.html#comparing-versions
            found_version = max([parsed_value, found_version])

    if not found_required_version:
        return repo.error(CATEGORY, f"required_version not found in terraform config - set terraform.required_version to \">= {required_version}\"")

    if found_version < required_version:
        return repo.error(
            CATEGORY,
            f"required version too low, wanted {required_version}, found {found_version}")
    logger.debug("Terraform required_version is OK")
    return None
