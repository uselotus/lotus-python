test:
	pylint --rcfile=.pylintrc --reports=y --exit-zero analytics | tee pylint.out
	flake8 --max-complexity=10 --statistics analytics > flake8.out || true
	coverage run --branch --include=analytics/\* --omit=*/test* setup.py test

release:
	python setup.py sdist bdist_wheel
	twine upload dist/*