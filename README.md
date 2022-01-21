# github_linter

This is mainly for me, but it's a way of going through the Github repositories that you have access to, to check all the things you'd usually expect.

Because I've got like ~100 repos and keep changing how I do things, and it annoys me to work on an old one and hit all the weird edge cases I've fixed elsewhere.

![build](https://github.com/yaleman/github_linter/actions/workflows/testing.yml/badge.svg)

## Current tests

- Dependabot
    - Has a (valid-ish) config
- Generic
    - Files you want gone
    - `CODEOWNERS` generation
    - generation of `.github/FUNDING`.yml
- GitHub Actions
    - Checks... something? TODO, fix this :P
- (GitHub) Issues
    - Checks for open Issues
    - Checks for open Pull Requests
- `pyproject.toml`

Only runs if you've got Python.

    - Checks authors based on a list.
    - Check module name matches repo
    - TODO: Check for imports, maybe?
- `pylintrc`

Only runs if you've got python.

    - Checks it exists
    - Checks for max line length configuration
    - TODO: Checks for other things (typically I disable TODO's, IE W0501)
- Terraform
    - TODO: flesh this out
    - Checks for provider versions
    - Checks you have provider config for all your required providers.
- Testing
    - Checks that `.github/workflows/testing.yml exists`


## Configuration

The config file is called `github_linter.json` - you can put it in the local dir or `~/.config/github_linter.json` - I've included my configuration in the repository.

Each test module has its defaults, in the `DEFAULT_CONFIG` attribute.

For an example:

``` python
>>> import github_linter.tests.pyproject
>>> print(github_linter.tests.pyproject.DEFAULT_CONFIG)
{'build-system': ['flit_core.buildapi', 'poetry.core.masonry.api'], 'readme': 'README.md'}
```

### Authentication

1. Use the "GITHUB_TOKEN" auth method.
2. Set the following in your config file:
    
    ```json
    "github" : { 
        "username" : "<your_username>", 
        "password" : "<your_password>" 
    }
    ```

3. Set the following in your config file to bypass auth and YOLO it.
    
    ```json
    "github" : { 
        "ignore_auth" : true 
    }
    ```

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
