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
- [ ] Run the **Upload Python Package** GitHub action on the tag
- [ ] Merge the `main` branch back into the `dev` branch
- [ ] On the `dev` branch, bump version in `averbis/__version__.py` to the next dev version, commit and wait until the build completed
- [ ] Once the release is available on PyPi, write the release notes
