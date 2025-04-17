up:
	@poetry update

deps:
	@poetry install --no-root --with=linting --all-extras

format: deps
	@poetry run tox run -e format

lint: deps
	@poetry run tox run -e lint

test:
	@poetry run tox

test-parallel: deps
	@poetry run tox run-parallel

build: clean deps
	@poetry build
	@poetry run tox run -e lint_distributions

clean:
	@rm -rf ./dist

publish:
	@poetry publish --build --repository formal

# aliases
check: lint
style: format
