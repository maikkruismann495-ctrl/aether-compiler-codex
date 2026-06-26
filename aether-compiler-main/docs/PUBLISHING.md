# Publishing Aether

This project is packaged with `pyproject.toml` and setuptools.

Release builds require Python 3.9+.

## Local Development Install

From the repo root:

```bash
python -m pip install -e .
aether --help
```

Install development tools:

```bash
python -m pip install -e ".[dev]"
```

## Verify Before Release

```bash
python -m unittest discover -s tests

for dir in examples/*; do
  aether "$dir" -o "example_datapacks/$(basename "$dir")"
done
```

On Windows PowerShell:

```powershell
python -m unittest discover -s tests

New-Item -ItemType Directory -Force example_datapacks | Out-Null
Get-ChildItem examples -Directory | ForEach-Object {
    aether $_.FullName -o "example_datapacks/$($_.Name)"
}
```

## Build Source and Wheel Distributions

```bash
python -m pip install -e ".[dev]"
python -m build
python -m twine check dist/*
```

This creates:

- `dist/aether_compiler-<version>.tar.gz`
- `dist/aether_compiler-<version>-py3-none-any.whl`

## Publish With GitHub Trusted Publishing

Recommended path:

1. Create a PyPI account.
2. On PyPI, create a Trusted Publisher for this repository.
3. Use these values:
   - Owner: your GitHub username or organization
   - Repository name: this repository name
   - Workflow filename: `publish.yml`
   - Environment name: `pypi`
4. Make sure `pyproject.toml` has the release version you want.
5. Commit and push the release changes.
6. Create a GitHub Release.
7. The `Publish to PyPI` workflow builds, checks, and publishes the package.

If the package name `aether-compiler` is already taken on PyPI, choose a new `project.name` in `pyproject.toml` before publishing.

## Manual Upload Fallback

Use this only if Trusted Publishing is not configured.

```bash
python -m pip install -e ".[dev]"
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

For a safer trial run, upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps aether-compiler
```

## Version Checklist

Before every release:

- Update `version` in `pyproject.toml`.
- Update `__version__` in `aether/__init__.py`.
- Update `CHANGELOG.md`.
- Run tests and compile examples.
- Build and run `twine check`.
