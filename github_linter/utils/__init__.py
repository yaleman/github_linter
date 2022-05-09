""" utility functions """

from json import JSONDecodeError
from typing import Any, Dict, Optional

import os.path
from pathlib import Path
import sys

from jinja2 import Environment, PackageLoader, select_autoescape
import jinja2.exceptions
import json5 as json
from loguru import logger



from ..defaults import DEFAULT_LINTER_CONFIG


def get_fix_file_path(category: str, filename: str) -> Path:
    """ gets a Path object for a filename within the fixes dir for the given category """
    if __file__.rsplit("/", maxsplit=1)[-1] == "__init__.py":
        module_parent = Path(__file__).parent.parent
    else:
        module_parent = Path(__file__).parent
    logger.debug(f"module parent: {module_parent}")
    fixes_path = module_parent / f"fixes/{category}/{filename}"
    if not fixes_path.exists():
        base_filename = Path(filename).name
        fixes_path = module_parent / f"fixes/{category}/{base_filename}"
        if not fixes_path.exists():
            logger.error(
                "Fix file {} in category {} not found, bailing. I looked in {}",
                filename,
                category,
                fixes_path,
            )
            sys.exit(1)
    return fixes_path

# I'm doing type: ignore here because it depends
# on the downstream modules, which can be anything.
def load_config() -> Dict[Optional[str], Any]:
    """ loads config """
    for configfile in [
        Path("./github_linter.json"),
        Path(os.path.expanduser("~/.config/github_linter.json")),
    ]:

        configfile = configfile.expanduser().resolve()

        if not configfile.exists():
            logger.debug("Path {} doesn't exist.", configfile)
            continue
        if not configfile.is_file():
            logger.debug("Path {} is not a file", configfile)
            continue
        try:
            config = json.load(configfile.open(encoding="utf8"))
            logger.debug("Using config file {}", configfile.as_posix())
            if "linter" not in config:
                config["linter"] = {}

            for key in DEFAULT_LINTER_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_LINTER_CONFIG[key]  # type: ignore
            return config# type: ignore
        except JSONDecodeError as json_error:
            logger.error("Failed to load {}: {}", configfile.as_posix(), json_error)

    logger.error("Failed to find config file")
    return {}


def generate_jinja2_template_file(
    module: str,
    filename: str,
    context: Optional[Dict[str, Any]],
    module_path: str = ".",
) -> Optional[str]:
    """ generates a file """

    if context is None:
        context = {}

    # start up jinja2
    jinja2_env = Environment(
        loader=PackageLoader(package_name="github_linter", package_path=module_path),
        autoescape=select_autoescape(),
    )
    try:
        template = jinja2_env.get_template(f"fixes/{module}/{filename}")
        rendered_template = template.render(**context)

    except jinja2.exceptions.TemplateNotFound as template_error:
        logger.error("Failed to load template: {}", template_error)
        return None
    return rendered_template

def setup_logging(debug: bool) -> None:
    """ sets up logging """

    if not debug:
        logger.remove()
        logger.add(level="INFO", sink=sys.stdout)
