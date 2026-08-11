# github_linter

This is mainly for me, but it's a way of going through the Github repositories that you have access to, to check all the things you'd usually expect.

Because I've got like ~100 repos and keep changing how I do things, and it annoys me to work on an old one and hit all the weird edge cases I've fixed elsewhere.

## Getting Started

### Installation

Install using `uv` (recommended) or `pip`:

```shell
# Or install from source
git clone https://github.com/yaleman/github_linter.git
cd github_linter
uv sync
```

### Configuration

Create a configuration file at `~/.config/github_linter.json` or in your project directory:

```json
{
    "github": {
        "token": "ghp_your_personal_access_token_here"
    },
    "linter": {
        "owner_list": ["your_github_username"]
    }
}
```

**Generating a Personal Access Token (PAT):**

1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Click "Generate new token" > "Generate new token (classic)"
3. Select scopes: `repo` (for full repo access) and `read:user` (for user info)
4. Copy the token and save it in your config file

### Basic CLI Usage

List repositories you have access to:

```shell
uv run github-linter --list-repos
```

Run all checks on your repositories:

```shell
uv run github-linter
```

Run checks for a specific module:

```shell
uv run github-linter --module pyproject
uv run github-linter --module dependabot
```

Apply automated fixes (requires `--fix` flag):

```shell
uv run github-linter --fix
```

Filter by repository or owner:

```shell
uv run github-linter --repo my-project
uv run github-linter --owner my-org
```

### Troubleshooting

#### Authentication Errors

If you see authentication errors:

1.  Verify your PAT is correct and has the required scopes (`repo`, `read:user`)
2.  Ensure the token is saved in your config file without extra quotes or whitespace
3.  Test your token: `curl -H "Authorization: token ghp_your_token" https://api.github.com/user`

#### Permission Denied

-   The token must have appropriate permissions for the repositories you're checking
-   For organization repos, you need to be a member with at least read access

#### Module Not Found

-   Check the module name matches one of the available modules: `branch_protection`, `codeowners`, `dependabot`, `generic`, `github_actions`, `issues`, `mkdocs`, `pyproject`, `security_md`, `terraform`
-   Run `uv run github-linter --help` to see all available options

#### Rate Limiting

If you hit GitHub API rate limits:

-   Use a PAT instead of unauthenticated requests
-   Reduce the number of repositories checked at once using `--repo` or `--owner` filters

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
  