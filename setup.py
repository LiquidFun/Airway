from pathlib import Path

from setuptools import setup

setup(
    name="airway",
    version="0.1.1",
    description="Automatic classification of tertiary bronchi based on bronchus masks using a rule-based approach.",
    long_description=open(Path(__file__).parent / "README.md", "r").read(),
    long_description_content_type="text/markdown",
    license="GPL-3.0",
    author="Brutenis Gliwa",
    url="https://github.com/LiquidFun/Airway",
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "airway=airway_pipeline:run",
            "airway-vis=airway_vis:run",
        ]
    },
    install_requires=[
        "numpy",
        "pydicom",
        "networkx",
        "scikit-image",
        "pandas",
        "pyyaml",
        "matplotlib",
        "tqdm",
        "Markdown",
        "WeasyPrint",
        "python-igraph",
    ],
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
