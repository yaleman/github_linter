# github_linter

This is mainly for me, but it's a way of going through the Github repositories you've got access to, to check all the things you'd usually expect.

Mainly because I've got like ~100 repos and keep changing how I do things.


## Adding new test modules

1. Add a module under `github_linter/tests/`
2. Call the tests `check_<something>`
3. Import the module in `__main__`
4. Add the module to `__main__.MODULES`
5. Eat cake.
