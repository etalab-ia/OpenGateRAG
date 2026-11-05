# OpenGateRAG

[![Version](https://img.shields.io/github/v/release/etalab-ia/OpenGateRAG?color=blue&label=version)](https://github.com/etalab-ia/OpenGateRAG/releases)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/OpenGateRAG/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/OpenGateRAG)
[![License](https://img.shields.io/github/license/etalab-ia/OpenGateRAG?color=green&label=license)](https://github.com/etalab-ia/OpenGateRAG/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/etalab-ia/OpenGateRAG?color=yellow&label=stars)](https://github.com/etalab-ia/OpenGateRAG/stargazers)

## Supported document formats

OpenGateRAG ingests PDF, HTML, Markdown, TXT, DOCX, XLSX, PPTX, ODT, ODS, ODP, CSV and EPUB files. PDF and PPTX chunks retain 1-based source page or slide numbers in `metadata.page_number`; other formats leave it unset when no reliable physical pagination exists.

When available, chunks also expose a scalar `metadata.heading` for their nearest source heading and the producing `metadata.parser_name` / `metadata.parser_version`. These four provenance keys are reserved and bounded to the existing scalar metadata contract, so no nested parser document is written to Elasticsearch. Existing documents remain readable without reindexing.

DOCX, XLSX, PPTX, ODT, ODS, ODP, CSV and EPUB conversion runs locally through Docling without outbound resource fetching. ZIP-based documents are checked for malformed content, excessive member counts and decompressed-size limits before parsing. Existing LangChain chunking remains unchanged.

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
    > The database setup by `OPENGATELLM_DATABASE_URL` environment variable must be the same
    > as the database used by the API specified in `OPENGATELLM_URL` environment variable.


* Lauch database dependencies

    ```bash
    docker compose --file compose.example.yml up --wait --detach postgres elasticsearch
    ```

* Instantiate database

    ```bash
    alembic -c opengaterag/api/alembic.ini upgrade head
    ```

* Start the isolated parser worker

    ```bash
    uvicorn opengaterag.api.parser_worker:app --host 127.0.0.1 --port 8001
    ```

* Run API locally in another terminal

    ```bash
    uvicorn opengaterag.api.app:app --reload
    ```

The example Docker Compose deployment starts this worker automatically. The worker has no API or database credentials, uses an internal-only network, runs without root privileges, and enforces input, output, page, archive, CPU, memory and timeout limits. Its temporary files live on a bounded in-memory filesystem and are removed after each conversion.

### Run tests

* Install dependencies

    ```bash
    pip install ".[test]"
    ```

* Run tests

    ```bash
    pytest opengaterag/api/tests/unit/
    ```

### Alembic migrations

* Run migrations

    ```bash
     alembic -c opengaterag/api/alembic.ini upgrade head
    ```

* Create a new migration

    ```bash
    alembic -c opengaterag/api/alembic.ini revision --autogenerate -m "Add new column to users table"
    ```