# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
sys.path.insert(0, os.path.abspath('D:\dev\ms-reactor\scripts\pymsreact'))
#sys.path.insert(0, os.path.abspath('..\..'))

project = 'pymsreact'
copyright = '2022, Zoltan Udvardy'
author = 'Zoltan Udvardy'
release = 'v0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# The documentation in pymsreact is written using numpy style docstrings. 
# Autodoc is the extension parsing docstrings in the python module, napoleon and
# numpydoc extensions are responsible to recognise numpy style docstrings.
extensions = ['sphinx.ext.autodoc', 
              'sphinx.ext.napoleon', 
              'numpydoc']
#              'sphinx.ext.autosummary'] # TODO: I think numpydoc automatically using autosummary
napoleon_numpy_docstring = True
autosummary_generate = True  # Turn on sphinx.ext.autosummary
numpydoc_show_class_members = False # Enabling this config causing a lot of warnings
                                    # due to missing documentation. TODO: Reenable it later

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The documentation is created to be publicly available on the read the docs 
# platform, hence rtd theme is selected here.
html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

