# Release Command

Create a new release for the trayscope project.

## Steps

1. **Check for uncommitted changes**
   - Run `git status --porcelain`
   - If there are uncommitted changes, stop and inform the user

2. **Get the latest tag and commits since then**
   - Run `git describe --tags --abbrev=0` to get the latest tag
   - Run `git log <latest-tag>..HEAD --pretty=format:"%h|%s"` to get commits since that tag
   - If no commits since the last tag, inform the user there's nothing to release

3. **Analyze commits to determine version bump**
   - **Minor bump** (increment middle number, reset patch to 0): commits containing keywords like `feat`, `feature`, `add`, `new`, `remove`, `breaking`, `refactor`, `change`
   - **Patch bump** (increment last number): commits containing keywords like `fix`, `bug`, `docs`, `typo`
   - Default to patch if unclear
   - Remember: this project is on v0.x.y so minor = breaking changes

4. **Calculate new version**
   - Parse current version from latest tag (e.g., v0.2.2 -> 0, 2, 2)
   - Apply the bump type
   - Format as new version string

5. **Show the user what will happen**
   - List the commits and their categories
   - Show current version -> new version
   - Ask for confirmation before proceeding

6. **Update CHANGELOG.md**
   - Read the current CHANGELOG.md
   - Generate a new entry with today's date in format `## [X.Y.Z] - YYYY-MM-DD`
   - Categorize commits into sections: Added, Changed, Fixed, Removed
   - Insert the new entry after the `# Changelog` header

7. **Update version in pyproject.toml**
   - Find the line `version = "X.Y.Z"` and update it

8. **Update version in trayscope/__init__.py**
   - Find the line `__version__ = "X.Y.Z"` and update it

9. **Commit and tag**
   - Stage the changed files: `git add CHANGELOG.md pyproject.toml trayscope/__init__.py`
   - Commit with message: `Release vX.Y.Z`
   - Create annotated tag: `git tag -a vX.Y.Z -m "Release X.Y.Z"`

10. **Push to remote**
    - Run `git push`
    - Run `git push --tags`
    - Inform the user that GitHub Actions will create the release and publish to PyPI
