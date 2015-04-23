# Summary

This python script watches a given directory for new pdf files and renames and moves files according to a set of rules.

# Dependencies

Python 3 with the following libraries from pypi:
- [watchdog]()
- [pyyaml]()

pdftotext (from poppler-utils)

# Installation

Just download, set up your configuration file, and run with python.

# Configuration

Coming soon...

# Todos
- default date format
- fix pylint errors
- change remaining print statements to logger
- document code
- create examples, documentation

# Future
- adjust mac colour labels
- could look at ocr from https://github.com/virantha/pypdfocr

# Acknowledgements

The idea came from online resources for going paperless, but I didn't feel like buying Hazel just for the file moving, and I couldn't find much else I liked.

I came across [Joe Workman's Paperless](https://github.com/joeworkman/paperless) ruby app, which was almost what I was looking for, but it overwrote files and was focused more on Evernote. I don't know Ruby at all and wasn't very comfortable making changes there, so I thought a more fun project would be to create it myself in Python. So this is very heavily inspired from that project.

For the implementation, I also found [this post](http://virantha.com/2013/04/20/python-auto-sort-of-ocred-pdfs/) helpful for some of the python code, although I ended up using a different pdf extractor. 
