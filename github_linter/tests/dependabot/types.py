""" types for gihtub_linter dependabot tests """

from typing import Any, Dict, List, Optional, TypedDict

import pydantic
import pytz

from ruyaml.scalarstring import DoubleQuotedScalarString

from .constants import DEPENDABOT_SCHEDULE_INTERVALS, PACKAGE_ECOSYSTEM


class DependabotSchedule(pydantic.BaseModel):
    """schedule"""

    interval: str
    day: Optional[str]
    time: Optional[DoubleQuotedScalarString]
    timezone: Optional[str]  # needs to be one of pytz.all_timezones

    @pydantic.validator("interval")
    def validate_interval(cls, value: str) -> str:
        """validates the schedule interval"""
        if value not in DEPENDABOT_SCHEDULE_INTERVALS:
            raise pydantic.ValidationError(
                f"interval needs to be in {','.join(DEPENDABOT_SCHEDULE_INTERVALS)}, got '{value}'",
                DependabotSchedule,
            )
        return value

    # TODO: write tests for this
    @pydantic.validator("timezone")
    def validate_timezone(
        cls, value: Optional[DoubleQuotedScalarString]
    ) -> Optional[DoubleQuotedScalarString]:
        """validator"""
        if value not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {value}")
        return DoubleQuotedScalarString(value)

    # TODO: write tests for this
    @pydantic.validator("time")
    def validate_time(
        cls, value: Optional[DoubleQuotedScalarString]
    ) -> Optional[DoubleQuotedScalarString]:
        """validator"""
        if value is not None:
            return DoubleQuotedScalarString(value)
        return value

    @pydantic.validator("day")
    def validate_day_value(cls, value: str, values: Dict[str, str]) -> str:
        """check you're specifying a valid day of the week"""
        if values.get("day"):
            if "interval" in values and values.get("day") not in [
                "monday" "tuesday" "wednesday" "thursday" "friday" "saturday" "sunday"
            ]:
                raise ValueError(f"Invalid day: {values['day']}")
        return value


class DefaultConfig(TypedDict):
    """config typing for module config"""

    config_filename: str
    schedule: Dict[str, Any]


class DependabotCommitMessage(pydantic.BaseModel):
    """configuration model for the config
    https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#commit-message

    """

    prefix: Optional[str]
    prefix_development: Optional[str] = pydantic.Field(alias="prefix-development")
    include: Optional[str]

    @pydantic.validator("include")
    def validate_include(cls, value: str) -> str:
        """checks for a valid entry"""
        if value != "scope":
            raise ValueError("Only 'scope' can be specified in 'include' field.")
        return value


# template = """
# version: 2
# updates:
# - package-ecosystem: pip
#   directory: "/"
#   schedule:
#     interval: daily
#     time: "06:00"
#     timezone: Australia/Brisbane
#   open-pull-requests-limit: 99
# """

# https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates


class DependabotUpdateConfig(pydantic.BaseModel):
    """an update config"""

    package_ecosystem: str = pydantic.Field(..., alias="package-ecosystem")
    directory: str = "/"
    schedule: DependabotSchedule
    allow: Optional[
        Dict[str, str]
    ]  # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#allow
    assignees: Optional[List[str]]
    commit_message: Optional[DependabotCommitMessage] = pydantic.Field(
        None, alias="commit-message"
    )
    ignore: Optional[List[str]]
    insecure_external_code_execution: Optional[str] = pydantic.Field(
        alias="insecure-external-code-execution"
    )
    labels: Optional[List[str]]
    milestone: Optional[int]
    open_pull_requests_limit: Optional[int] = pydantic.Field(
        alias="open-pull-requests-limit"
    )
    # noqa: E501 pylint: disable=line-too-long
    # TODO: this needs to be a thing - https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#pull-request-branch-nameseparator
    # pull-request-branch-name.separator
    rebase_strategy: Optional[str] = pydantic.Field(alias="rebase-strategy")
    # TODO: registries typing for DependabotUpdateConfig
    registries: Optional[Any]
    reviewers: Optional[List[str]]
    target_branch: Optional[str] = pydantic.Field(alias="target-branch")
    vendor: Optional[bool]
    versioning_strategy: Optional[str] = pydantic.Field(alias="versioning-strategy")

    # TODO: write tests for this
    @pydantic.validator("package_ecosystem")
    def validate_package_ecosystem(cls, value: str) -> str:
        """validates you're getting the right value"""
        if value not in PACKAGE_ECOSYSTEM:
            raise ValueError(f"invalid value for package_ecosystem '{value}'")
        return value

    # TODO: write tests for this
    @pydantic.validator("rebase_strategy")
    def validate_rebase_strategy(cls, value: str) -> str:
        """validates you're getting the right value"""
        if value not in ["disabled", "auto"]:
            raise ValueError("rebase-strategy needs to be either 'auto' or 'disabled'.")
        return value

    # TODO: write tests for this
    @pydantic.validator("rebase_strategy")
    def validate_execution_permissions(cls, value: str) -> str:
        """validates you're getting the right value"""
        if value not in ["deny", "allow"]:
            raise ValueError(
                "insecure-external-code-execution needs to be either 'allow' or 'deny'."
            )
        return value


class DependabotConfigFile(pydantic.BaseModel):
    """configuration file"""

    version: int
    updates: List[DependabotUpdateConfig]

    # pylint: disable=too-few-public-methods
    class Config:
        """meta config for class"""

        arbitrary_types_allowed = True
