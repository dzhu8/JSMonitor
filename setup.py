from setuptools import setup, find_packages

setup(
    name="jsmonitor-tools",
    version="0.2.0",
    description="Monitor and manage JavaScript and TypeScript dependencies",
    author="Daniel Zhu",
    author_email="danielyumengzhu@gmail.com",
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "jsmonitor-updater=python.npm_package_update:main",
            "jsmonitor-installer=python.npm_check_installs:main",
            "orange=python.orange:main",
        ],
    },
    python_requires=">=3.6",
)