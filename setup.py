from pathlib import Path

from setuptools import setup, find_packages

from airway import __version__

root_path = Path(__file__).parent

print(find_packages())

setup(
    name="airway",
    version=__version__,
    description="Automatic classification of tertiary bronchi based on bronchus masks using a rule-based approach.",
    long_description=open(root_path / "README.md", "r").read(),
    long_description_content_type="text/markdown",
    license="GPL-3.0",
    author="Brutenis Gliwa",
    url="https://github.com/LiquidFun/Airway",
    python_requires=">=3.6",
    package_dir={"airway": "airway"},
    packages=find_packages(),
    package_data={
        "airway": [
            # These need to be put in the airway directory, so that these can be included in the pip package
            *[f"configs/{n}.yaml" for n in ("array_encoding", "classification", "example_defaults", "stage_configs")],
            "example_data/model.npz",
            "visualization/cytoscape/*.xml",
            "visualization/website",
        ]
    },
    entry_points={
        "console_scripts": [
            "airway=airway.cli.cli:main",
        ]
    },
    install_requires=[req.strip() for req in open("requirements.txt").readlines()],
    tests_require=["pytest"],
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
)
