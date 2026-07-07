# OpenGateRAG

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