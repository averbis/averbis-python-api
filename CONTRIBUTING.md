# Contribution guidelines

This document describes briefly how to contribute code to the Averbis Python API.

* Review the LICENSE file and make yourself familiar with the project's license including the conditions for contributions
* Create an issue
* If you have no commit access to the repository, please fork the repository
* Create a branch based on the `dev` branch and give it a name including the issue number and title. Here are some examples
  * `feature/142-Ability-to-cook-hard-boiled-eggs` (use `feature` prefix for features and refactorings)
  * `bugfix/132-Unable-to-retrieve-salt-from-the-cupboard` (use `bugfix` for bugs)
* Submit your contribution as one or more commits on your branch
  * Before committing run `uv run task format` to auto-format the code.
  * Commit messages should include the issue number and full title in the first line, then a blank line and then 
    bulleted list explaining the details. Here is an example:
    ```
    Issue #142 - Ability to cook hard-boiled eggs
    
    - Added pot and stove
    - Added unit test for pot and stove
    - Added integration test ensuring pot works with stove
    - Updated documentation
    ```
* Open a pull request immediately after your first commit. If your pull request includes multiple commits, mark the pull
  request as *draft* while you are still working on it.
* Once the pull request is complete, mark it as *ready* and request a review.
