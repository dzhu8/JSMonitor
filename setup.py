from setuptools import find_packages, setup

setup(
    name="jsmonitor-tools",
    version="0.2.0",
    description="Tools to monitor and manage JavaScript and TypeScript files.",
    author="Daniel Zhu",
    author_email="danielyumengzhu@gmail.com",
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "jsmonitor-updater=python.npm_package_update:main",
            "jsmonitor-installer=python.npm_check_installs:main",
            "orange=python.orange:main",
            "format-imports=python.format_imports:main",
            "image-import-check=python.image_import_check:main",
        ],
    },
    python_requires=">=3.6",
)
