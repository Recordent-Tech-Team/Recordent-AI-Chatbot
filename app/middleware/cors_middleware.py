from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=
        r"^https:\/\/([a-zA-Z0-9-]+\.)?recordent\.com$",
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST"
        ],
        allow_headers=["*"]
    )