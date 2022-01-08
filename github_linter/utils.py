""" utility functions """

from typing import Dict, List

def add_result(result_object: Dict[str, List[str]], category: str, value: str) -> None:
    """ adds an result to the target object"""
    if category not in result_object:
        result_object[category] = []
    result_object[category].append(value)
