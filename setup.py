from setuptools import setup

setup(
    name="jsmonitor-tools",
    version="0.1.0",
    description="Monitor and manage JavaScript and TypeScript dependencies",
    author="Daniel Zhu",
    author_email="danielyumengzhu@gmail.com",
    py_modules=["npm_package_update", "npm_check_installs", "utils"],
    entry_points={
        "console_scripts": [
            "jsmonitor-updater=npm_package_update:main",
            "jsmonitor-installer=npm_check_installs:main",
        ],
    },
    python_requires=">=3.6",
)