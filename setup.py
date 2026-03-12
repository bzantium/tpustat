from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).parent


setup(
    name="tpustat",
    version="0.1.0",
    description="A gpustat-style TPU status CLI built on top of google-smi.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Ryan",
    license="MIT",
    python_requires=">=3.10",
    packages=["tpustat"],
    include_package_data=True,
    install_requires=[
        "psutil>=5.9",
        "shtab>=1.7",
    ],
    extras_require={
        "dev": ["pytest>=8.0"],
    },
    entry_points={
        "console_scripts": [
            "tpustat=tpustat.cli:main",
        ],
    },
)
