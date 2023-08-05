""" testing dependabot """

# from github_linter.tests.dependabot import load_file

# def test_load_file():
#     """ tests loading the dependabot file """
#     load_file(None, {}, {})

from pytest import raises

from github_linter.tests.dependabot.types import DependabotSchedule


def test_schedule_bad_setting_monthly_with_day() -> None:
    """tests when you set a monthly schedule but also specify a day"""
    input_value = {"interval": "monthly", "day": "lol"}
    with raises(ValueError):
        DependabotSchedule.model_validate(input_value)


def test_schedule_setting_monthly() -> None:
    """tests when you set a monthly schedule"""
    input_value = {"interval": "monthly"}
    DependabotSchedule.model_validate(input_value)


def test_schedule_setting_daily() -> None:
    """tests when you set a monthly schedule but also specify a day"""
    input_value = {"interval": "daily"}
    DependabotSchedule.model_validate(input_value)


def test_schedule_setting_weekly() -> None:
    """tests when you set a weekly schedule"""
    input_value = {"interval": "weekly", "day": "monday"}
    DependabotSchedule.model_validate(input_value)
    input_value = {"interval": "weekly"}
    DependabotSchedule.model_validate(input_value)
