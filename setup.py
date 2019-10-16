import io
import re

import setuptools

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

with io.open("src/cacheorm/__init__.py", "rt", encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setuptools.setup(
    name="cacheorm",
    version=version,
    url="https://github.com/leosocy/cacheorm",
    project_urls={
        "Code": "https://github.com/leosocy/cacheorm",
        "Issue tracker": "https://github.com/leosocy/cacheorm/issues",
    },
    license="MIT",
    author="leosocy",
    author_email="leosocy@gmail.com",
    description="A cache-based python ORM.",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "mock",
            "coverage",
            "flake8",
            "mccabe",
            "flake8-bugbear",
            "pep8-naming",
            "flake8-comprehensions",
            "redis>=3.0",
            "libmc>=1.3.0",
            "msgpack<1.0",
            "protobuf>=3.9",
        ],
        "backends": ["redis>=3.0", "libmc>=1.3.0"],
        "serializers": ["msgpack>=0.6,<1.0", "protobuf>=3.9"],
    },
)
