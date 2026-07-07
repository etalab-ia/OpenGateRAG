# OpengateRAG

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

## Run e2e tests

* Install dependencies

    ```bas
    pip install ".[test]"
    ```

* Export environment variables

    Export a key of a user of your the setup OpenGateLLM API (`opengatellm.url` parameter in your configuration file) without `ADMIN` permission in `OPENGATELLM_USER_API_KEY` environment variable and a key of a user 
    with `ADMIN` permission in `OPENGATELLM_ADMIN_API_KEY` environment variable.

    Both users need to access to the setup embeddings model of the OpenGateLLM API (`opengatellm.model_name` parameter in your configuration file).

    ```bash
    export OPENGATELLM_USER_API_KEY=<your_user_api_key>
    export OPENGATELLM_ADMIN_API_KEY=<your_admin_api_key>
    ```
* Run tests

    ```
    pytest opengaterag/api/tests/e2e/
    ```