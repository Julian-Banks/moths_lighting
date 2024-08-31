from setuptools import setup, find_packages

def parse_requirements(filename):
	with open(filename) as f:
		return f.read().splitlines()


setup(
	name="moths_lighting",
	version = "0.1",
	packages =find_packages(),
	instal_requires = pares_requirements('requirements.txt'),
	author = "Julian Banks",
	author_email = "julianrowlandbanks@gmail.com",
	description = "A library built specifically for the moths event lighting setup!",
	long_description = open("README.md").read(),
	long_description_content_type = "text/markdown",
	url = "repo here",
	classifiers = [
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
	],
	python_requires='>=3.10'
)
