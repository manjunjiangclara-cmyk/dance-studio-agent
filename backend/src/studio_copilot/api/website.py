"""Serve only the compiled website, never repository or database files."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def install_website(application: FastAPI) -> None:
    default = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    directory = Path(os.environ.get("WEBSITE_DIST", str(default))).resolve()
    if (directory / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=directory / "assets"), name="assets")

    def index():
        path = directory / "index.html"
        if not path.is_file():
            raise HTTPException(503, "Build the website with npm ci && npm run build in frontend/.")
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    application.add_api_route("/", index, include_in_schema=False)
    application.add_api_route("/demo", index, include_in_schema=False)
    application.add_api_route("/demo/{path:path}", index, include_in_schema=False)
    application.add_api_route("/workspace", index, include_in_schema=False)
    application.add_api_route("/workspace/{path:path}", index, include_in_schema=False)
