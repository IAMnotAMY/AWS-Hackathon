"""Setup script for nl-floorspace-agent package."""

from setuptools import setup, find_packages

setup(
    name="nl-floorspace-agent",
    version="0.1.0",
    description="Natural Language to Floorspace JSON Agent",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Developer",
    author_email="dev@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.34.0",
        "pydantic>=2.5.0",
        "hypothesis>=6.92.0",
        "pytest>=7.4.0",
        "spacy>=3.7.0",
        "tenacity>=8.2.0",
        "jsonschema>=4.20.0",
    ],
    extras_require={
        "dev": [
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.7.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)