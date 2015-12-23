#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name='cave filter',
    version='0.1',
    packages=find_packages(),

    data_files = [("/etc", ['cavefilter/cave_filter.cfg'])],

    # installing unzipped
    zip_safe = False,

    # predefined extension points, e.g. for plugins
    entry_points = """
    [console_scripts]
    cave_filter = cavefilter.cave_filter:main
    """,
    # pypi metadata
    author = "Stefan Kögl",

    # FIXME: add author email
    author_email = "stefan.koegl@rub.de",
    description = "a tool to easily update a gentoo system managed by the paludis package manager",

    # FIXME: add long_description
    long_description = """You get a list of packages to update. You can choose which packages to update. Only use this if the manual update would be too time consuming or you just want to pick some packages. When you know what you are doing"
    """,

    # FIXME: add license
    license = "GPL v3",

    # FIXME: add keywords
    keywords = "",

    # FIXME: add download url
    url = "",
)
