test:
	python -m pytest tests/

black:
	black -l 100 averbis/
	black -l 100 tests/

html:
	cd docs && make html

license:
	licenseheaders -t build/apache-2.tmpl -n "Averbis Python API" -y "2021" -o "Averbis GmbH" -u "https://www.averbis.com" -x ".*" "venv/*"
