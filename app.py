from __future__ import annotations

import json
import mimetypes
import os
import re
import uuid

from pathlib import Path
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.pipeline import analyze
from src.config import OUTPUT_DIR


# =========================================================
# PATHS
# =========================================================

BASE = Path(__file__).resolve().parent

UPLOADS = BASE / "uploads"

UPLOADS.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# =========================================================
# HTTP HANDLER
# =========================================================

class Handler(BaseHTTPRequestHandler):

    # -----------------------------------------------------
    # SEND RESPONSE
    # -----------------------------------------------------

    def _send(
        self,
        status,
        body,
        content_type="text/html; charset=utf-8",
    ):

        data = (
            body.encode("utf-8")
            if isinstance(body, str)
            else body
        )

        self.send_response(status)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(data)),
        )

        self.end_headers()

        self.wfile.write(data)

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def do_GET(self):

        path = unquote(
            self.path.split("?", 1)[0]
        )

        # Home page
        if path == "/":

            return self._file(
                BASE / "templates" / "index.html",
                "text/html; charset=utf-8",
            )

        # Static files
        if path.startswith("/static/"):

            p = (
                BASE
                / "static"
                / path[len("/static/"):]
            )

            return self._file(
                p,
                mimetypes.guess_type(
                    p.name
                )[0]
                or "application/octet-stream",
            )

        # Generated job files
        if path.startswith("/api/jobs/"):

            rel = (
                path[len("/api/jobs/"):]
                .split("/", 1)
            )

            if len(rel) == 2:

                job, file_name = rel

                p = (
                    OUTPUT_DIR
                    / job
                    / file_name
                )

                if (
                    p.exists()
                    and p.is_file()
                ):

                    return self._file(
                        p,
                        mimetypes.guess_type(
                            p.name
                        )[0]
                        or "application/octet-stream",
                        download=False,
                    )

        return self._send(
            404,
            b"Not found",
            "text/plain",
        )

    # -----------------------------------------------------
    # SERVE FILE
    # -----------------------------------------------------

    def _file(
        self,
        p,
        content_type,
        download=False,
    ):

        if (
            not p.exists()
            or not p.is_file()
        ):

            return self._send(
                404,
                b"Not found",
                "text/plain",
            )

        data = p.read_bytes()

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(data)),
        )

        if download:

            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{p.name}"',
            )

        self.end_headers()

        self.wfile.write(data)

    # -----------------------------------------------------
    # POST /api/analyze
    # -----------------------------------------------------

    def do_POST(self):

        if self.path != "/api/analyze":

            return self._send(
                404,
                b"Not found",
                "text/plain",
            )

        try:

            # ---------------------------------------------
            # Request size
            # ---------------------------------------------

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            # 250 MB limit
            if length > 250 * 1024 * 1024:

                return self._json(
                    413,
                    {
                        "error":
                            "Video is larger than 250 MB."
                    },
                )

            # ---------------------------------------------
            # Read multipart body
            # ---------------------------------------------

            body = self.rfile.read(
                length
            )

            content_type = self.headers.get(
                "Content-Type",
                "",
            )

            boundary_match = re.search(
                r'boundary=(?:"([^"]+)"|([^;]+))',
                content_type,
            )

            if not boundary_match:

                return self._json(
                    400,
                    {
                        "error":
                            "Invalid multipart upload."
                    },
                )

            boundary = (
                boundary_match.group(1)
                or boundary_match.group(2)
            ).encode()

            parts = body.split(
                b"--" + boundary
            )

            if len(parts) < 2:

                return self._json(
                    400,
                    {
                        "error":
                            "Could not read uploaded video."
                    },
                )

            part = parts[1]

            header_end = part.find(
                b"\r\n\r\n"
            )

            if header_end < 0:

                return self._json(
                    400,
                    {
                        "error":
                            "Could not read uploaded video."
                    },
                )

            headers = part[
                :header_end
            ].decode(
                "utf-8",
                "ignore",
            )

            content = part[
                header_end + 4:
            ]

            if content.endswith(
                b"\r\n"
            ):

                content = content[:-2]

            # ---------------------------------------------
            # Filename
            # ---------------------------------------------

            filename_match = re.search(
                r'filename="([^"]+)"',
                headers,
            )

            original_name = (
                filename_match.group(1)
                if filename_match
                else "video.mp4"
            )

            safe_name = re.sub(
                r"[^A-Za-z0-9_.-]",
                "_",
                original_name,
            )

            extension = Path(
                safe_name
            ).suffix.lower()

            allowed_formats = {
                ".mp4",
                ".mov",
                ".avi",
                ".mkv",
            }

            if extension not in allowed_formats:

                return self._json(
                    400,
                    {
                        "error":
                            "Supported formats: "
                            "MP4, MOV, AVI, MKV"
                    },
                )

            # ---------------------------------------------
            # Save uploaded video
            # ---------------------------------------------

            token = uuid.uuid4().hex[:10]

            uploaded_path = (
                UPLOADS
                / f"{token}_{safe_name}"
            )

            uploaded_path.write_bytes(
                content
            )

            # ---------------------------------------------
            # Analyze
            # ---------------------------------------------

            result = analyze(
                uploaded_path,
                OUTPUT_DIR / token,
            )

            # ---------------------------------------------
            # Return result
            # ---------------------------------------------

            response = {
                **result["data"],
                "job_id":
                    result["job_id"],
            }

            return self._json(
                200,
                response,
            )

        except Exception as exc:

            print(
                f"Analysis error: {exc}"
            )

            return self._json(
                500,
                {
                    "error": str(exc)
                },
            )

    # -----------------------------------------------------
    # JSON RESPONSE
    # -----------------------------------------------------

    def _json(
        self,
        status,
        obj,
    ):

        return self._send(
            status,
            json.dumps(
                obj,
                ensure_ascii=False,
            ),
            "application/json; charset=utf-8",
        )

    # -----------------------------------------------------
    # LOGGING
    # -----------------------------------------------------

    def log_message(
        self,
        fmt,
        *args,
    ):

        print(
            fmt % args
        )


# =========================================================
# SERVER START
# =========================================================

if __name__ == "__main__":

    # Render provides PORT automatically.
    # Local machine falls back to 5000.

    port = int(
        os.environ.get(
            "PORT",
            "5000",
        )
    )

    host = "0.0.0.0"

    print(
        f"ScoreVision running at "
        f"http://{host}:{port}"
    )

    server = ThreadingHTTPServer(
        (host, port),
        Handler,
    )

    server.serve_forever()