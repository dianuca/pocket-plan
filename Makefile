.PHONY: test run check migrate

test:
	python manage.py test

run:
	python manage.py runserver

check:
	python manage.py check

migrate:
	python manage.py migrate