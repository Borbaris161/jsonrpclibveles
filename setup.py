#!/usr/bin/env/python

import setuptools

with open("README.md") as readme:
    long_description = readme.read()
    with open("README", "w") as pypi_readme:
        pypi_readme.write(long_description)

setuptools.setup(
    name="jsonrpclibveles",
    version="0.0.1",
    packages=setuptools.find_packages(),
    author="Krutsevich Artem",
    install_requires=["tornado", "websocket-client"],
    author_email="borbaris161@gmail.com",
    description="JSON-RPC VelesPy project library, implementing  custom jsonrpclib."
                "Uses tornadowebserver and websockets",
    long_description=long_description,
)

