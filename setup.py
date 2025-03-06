from setuptools import setup

setup(
    name="npm-updater",
    version="0.1.0",
    description="Update npm dependencies to their latest versions",
    author="Daniel Zhu",
    author_email="danielyumengzhu@gmail.com",
    py_modules=["npm_package_update"],
    entry_points={
        "console_scripts": [
            "npm-updater=npm_package_update:main",
        ],
    },
    python_requires=">=3.6",
)