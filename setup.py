from setuptools import setup

setup(
    name="npm-tools",
    version="0.1.0",
    description="Update npm dependencies to their latest versions and install missing packages",
    author="Daniel Zhu",
    author_email="danielyumengzhu@gmail.com",
    py_modules=["npm_package_update", "npm_check_uninstalled_versions", "utils"],
    entry_points={
        "console_scripts": [
            "npm-updater=npm_package_update:main",
            "npm-installer=npm_check_uninstalled_versions:main",
        ],
    },
    python_requires=">=3.6",
)