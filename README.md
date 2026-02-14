# github_linter

This is mainly for me, but it's a way of going through the Github repositories that you have access to, to check all the things you'd usually expect.

Because I've got like ~100 repos and keep changing how I do things, and it annoys me to work on an old one and hit all the weird edge cases I've fixed elsewhere.

## Current Modules

### Dependabot

* Checks for a (valid-ish) config

### Generic Things

* Files you want gone
* `CODEOWNERS` generation
* generation of `.github/FUNDING`.yml

### GitHub Actions

* Checks for github actions tests and stuff

### (GitHub) Issues
  
* Checks for open Issues
* Checks for open Pull Requests

### `pyproject.toml`

  Only runs if you've got Python.

* Checks authors based on a list.
* Check module name matches repo
* TODO: Check for imports, maybe?
* Checks it exists
* Checks for max line length configuration
* TODO: Checks for other things (typically I disable TODO's, IE W0501)

### Terraform

* TODO: flesh this out
* Checks for provider versions
* Checks you have provider config for all your required providers.

### Testing

* Doesn't check for much - have moved this to github_actions

### mkdocs

* checks if you've got mkdocs-looking things and then makes sure you've got a github actions thing to run them

## Configuration

The config file is called `github_linter.json` - you can put it in the local dir or `~/.config/github_linter.json` - I've included my configuration in the repository.

Each test module has its defaults, in the `DEFAULT_CONFIG` attribute.

For an example:

```python
>>> import github_linter.tests.pyproject
>>> print(github_linter.tests.pyproject.DEFAULT_CONFIG)
{'build-system': ['flit_core.buildapi', 'poetry.core.masonry.api'], 'readme': 'README.md'}
```

### Authentication

#### Using a Personal Access Token (Recommended)

```json
"github" : { 
    "token" : "<pat>"
}
```

#### Using username/password

```json
"github" : { 
    "username" : "<your_username>", 
    "password" : "<your_password>" 
}
```

#### Set the following in your config file to bypass auth and YOLO it

```json
"github" : { 
    "ignore_auth" : true 
}
```

## Adding new test modules

1. Add a module under `github_linter/tests/`
2. Set `CATEGORY: str = "nameofmodule"` to a name which will go in the reports.
3. Set `LANGUAGES: List[str] = []` to a list of lower case languages, eg: python / javascript / rust / shell / "all" which matches all. This is based on GitHub's auto-detection.
4. Call check functions `check_<something>`
5. Call fix functions `fix_<something>`
6. Import the module in `tests/__init__.py` as part of the big `from . import ()` block.
7. Eat cake.

## Docker container

The container runs an entrypoint of `/bin/bash` which puts you in an environment where the package and non-dev deps are installed.

The container name to pull is `ghcr.io/yaleman/github_linter:latest`.

### Building the docker container

This should auto-build with github actions (soon!) but here's a handy command:

```shell
docker build -t 'ghcr.io/yaleman/github_linter' .
```

### Running things in the docker container

Running the web server.

```shell
docker run --rm -it \
* e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
* v "$(pwd)/github_linter.json:/home/useruser/github_linter.json" \
* p '8000:8000' \
    ghcr.io/yaleman/github_linter:latest \
    python -m github_linter.web
```

## Thanks

* [Vue.js](http://vuejs.org) used in the UI
* [Pico](https://picocss.com) CSS framework.
  