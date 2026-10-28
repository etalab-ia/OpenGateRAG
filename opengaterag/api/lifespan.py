from contextlib import asynccontextmanager

from fastapi import FastAPI
import httpx

from opengaterag.api.infrastructure.configuration import get_configuration


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration = get_configuration()

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{configuration.dependencies.opengatellm.url}/health", timeout=60)
        if response.status_code != 200:
            raise RuntimeError("OpenGateLLM is not reachable.")

    yield
