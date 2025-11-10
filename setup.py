"""Setup script for File Organizer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements = []
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]

# Read README
readme = Path(__file__).parent / "README.md"
long_description = ""
if readme.exists():
    with open(readme) as f:
        long_description = f.read()

setup(
    name="file-organizer",
    version="0.1.0-dev",
    author="John Tierney",
    author_email="jgtierney@gmail.com",
    description="Systematic file and folder organization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jgtierney/dl-organize",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Filesystems",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "file-organizer=file_organizer.cli:main",
        ],
    },
)

