# OpenGateRAG

[![Version](https://img.shields.io/github/v/release/etalab-ia/OpenGateRAG?color=blue&label=version)](https://github.com/etalab-ia/OpenGateRAG/releases)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/OpenGateRAG/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/OpenGateRAG)
[![License](https://img.shields.io/github/license/etalab-ia/OpenGateRAG?color=green&label=license)](https://github.com/etalab-ia/OpenGateRAG/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/etalab-ia/OpenGateRAG?color=yellow&label=stars)](https://github.com/etalab-ia/OpenGateRAG/stargazers)


## Developer mode (local API)

* Install dependencies

    ```bash
    pip install .
    ```

* Configure and export environment variables

    ```bash
    cp .env.example .env # update variables after copy
    export $(cat .env | grep -v ^# | xargs)
    ```

    > [!NOTE]
    > The database setup by `OPENGATELLM_DATABASE_URL` environment variable must be the same as the database used by the API specified in `OPENGATELLM_URL` environment variable.

* Run API locally

    ```bash
    uvicorn opengaterag.api.app:app --reload
    ```

## Run tests

* Install dependencies

    ```bas
    pip install ".[test]"
    ```

* Run tests

    ```
    pytest opengaterag/api/tests/unit/
    ```