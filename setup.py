from setuptools import setup, find_packages

setup(
    name="example-reviewer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "openai>=1.0.0",
        "instructor>=1.5.0",
        "requests>=2.31.0",
        "markdown-it-py>=3.0.0",
        "python-frontmatter>=1.0.0",
        "regex>=2023.10.0",
        "python-json-logger>=2.0.0",
        "jinja2>=3.1.0",
        "gitpython>=3.1.40",
    ],
    extras_require={
        "vector": [
            "chromadb>=0.4.20",
            "sentence-transformers>=2.2.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "example-reviewer=src.cli.main:main",
        ],
    },
    python_requires=">=3.9",
    description="Automated code example validation and review pipeline",
    author="Aspose",
    license="MIT",
)
