# github_linter

This is mainly for me, but it's a way of going through the Github repositories that you have access to, to check all the things you'd usually expect.

Mainly because I've got like ~100 repos and keep changing how I do things.

## Current tests

- Dependabot
    - Has a (valid-ish) config
- Generic
    - Files you want gone
- Issues
    - Checks for open Issues
    - Checks for open Pull Requests
- `pyproject.toml`
    - Checks authors based on a list.
    - Check module name matches repo
    - TODO: Check for imports, maybe?
- pylintrc
    - Checks it exists
    - TODO: Checks for max line length
    - TODO: Checks for other things (typically I disable TODO's, IE W0501)

## Configuration

The config file is called `github_linter.json` - you can put it in the local dir or `~/.config/github_linter.json` - I've included my configuration in the repository.

## Adding new test modules

1. Add a module under `github_linter/tests/`
    - Set `str: CATEGORY` to a name which will go in the reports.
    - Set `List[str]: LANGUAGES` to a list of lower case languages, eg:
        - python
        - javascript
        - rust
        - shell
        - "all" is allowed if it's a generic thing
2. Call the tests `check_<something>`
3. Import the module in `__main__`
4. Add the module to `__main__.MODULES`
5. Eat cake.
