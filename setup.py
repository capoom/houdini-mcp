from setuptools import setup, find_packages

# This minimal setup.py delegates to pyproject.toml
# It's only needed for editable installs with older pip versions
setup(
    name="houdini-mcp",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
