# coding: utf-8
from setuptools import setup

setup(
  name="mpdispatcher",
  # version is handled dynamically by setuptools_scm
  use_scm_version = True,
  description="Signal dispatcher for multiprocessing, with asyncio support",
  keywords="",
  url="",
  author="Shahriar Heidrich",
  author_email="smheidrich@weltenfunktion.de",
  classifiers=[
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.6",
  ],
  modules=["mpdispatcher"],
  setup_requires=[
    "pytest-runner",
    "setuptools_scm",
  ],
  install_requires=[
  ],
  tests_require=[
    "pytest",
  ],
)
