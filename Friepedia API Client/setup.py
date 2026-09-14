from setuptools import setup, find_packages
import os

setup(
    name="friepedia",
    version="1.0.0",
    author="Friepedia Team",
    description="The lightweight client for the Friepedia RAG Ecosystem.",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://friepedia.com", # Your future landing page
    packages=find_packages(),
    install_requires=[
        "pandas",
        "requests",
        "ipywidgets",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)