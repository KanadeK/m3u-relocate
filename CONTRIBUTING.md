# Contributing

Please start with an issue describing a reproducible problem and a minimal synthetic fixture. Keep real data and credentials out of public reports. There is no contributor license agreement.

Use Python 3.10 or newer in a virtual environment:

```sh
python -m pip install -e .
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m coverage run -m unittest discover -s tests
python -m coverage report
python -m build
```

Tests should demonstrate behavior through realistic inputs, error cases and the installed CLI. CI does not write commits or update dependencies. External pull requests are not automatically merged. The maintainer reviews and implements accepted changes; any legitimately reused third-party material must retain its license and attribution.
