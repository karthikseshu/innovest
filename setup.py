"""
Setup script for Email Transaction Parser.
"""
from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="email-transaction-parser",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A pluggable utility API for extracting transaction information from emails",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/email-transaction-parser",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/email-transaction-parser/issues",
        "Source": "https://github.com/yourusername/email-transaction-parser",
        "Documentation": "https://github.com/yourusername/email-transaction-parser#readme",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Email",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "email-parser=email_parser.api.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="email, transaction, parser, cashapp, paypal, financial, api",
)
