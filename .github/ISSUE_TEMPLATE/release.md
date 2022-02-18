---
name: Release (for developers)
about: Release checklist

---

**GitHub issue tracker**
- [ ] Ensure all issues and PRs are resolved/merged
- [ ] Close the milestone
- [ ] Create milestone for the next release

**Code**
- [ ] Merge the `dev` branch into the `main` branch
- [ ] On the `main` branch, bump version in `averbis/__version__.py` to the release version, commit and wait until the build completed
- [ ] Create the release tag on the `main` branch
- [ ] Merge the `main` branch into the `dev` branch

**GitHub**
- [ ] Draft a [release](https://github.com/averbis/averbis-python-api/releases) from the tag you just made
- [ ] Publish the release (this also triggers the "publish" GitHub action)

**Code**
- [ ] On the `dev` branch, bump version in `averbis/__version__.py` to the next dev version, commit and wait until the build completed
