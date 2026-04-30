from setuptools import setup, find_packages

setup(
    name="odrl-infra-cli",
    version="0.1.0",
    description="ODRL Infrastructure CLI for AI Agents",
    author="CODATA",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "odrl-cli=bin.odrl_cli_wrapper:main",
        ],
    },
    scripts=['bin/odrl-cli'],
    python_requires=">=3.8",
)
