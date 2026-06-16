from setuptools import setup, find_packages

setup(
    name="example-reviewer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.10,<3",
        "pydantic-settings>=2.14,<3",
        "anthropic>=0.40,<1",
        "openai>=1.58,<2",
        "instructor>=1.6,<2",
        "sqlalchemy>=2.0.36,<3",
        "requests>=2.32,<3",
        "markdown-it-py>=3.0,<4",
        "python-frontmatter>=1.1,<2",
        "regex>=2024.11,<2025",
        "python-json-logger>=2.0,<3",
        "jinja2>=3.1,<4",
        "gitpython>=3.1.43,<4",
        "python-dotenv>=1.0,<2",
        "pyminizip>=0.2.6,<1",
        "py7zr>=0.22,<1",
    ],
    extras_require={
        "vector": [
            "chromadb>=0.5,<1",
            "sentence-transformers>=3.3,<4",
        ],
        "dev": [
            "pytest>=8.3,<9",
            "pytest-asyncio>=0.24,<1",
            "pytest-mock>=3.14,<4",
            "pytest-cov>=6.0,<7",
            "pytest-timeout>=2.3,<3",
        ],
    },
    entry_points={
        "console_scripts": [
            "example-reviewer=src.cli.main:main",
        ],
    },
    python_requires=">=3.10",
    description="Automated code example validation and review pipeline",
    author="Aspose",
    license="MIT",
)
