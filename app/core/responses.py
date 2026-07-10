from typing import Any, Optional


def success(
    message: str = "Success",
    data: Optional[Any] = None,
    http_status: int = 200,
) -> dict:
    return {
        "status": True,
        "message": message,
        "data": data,
        "httpStatus": http_status,
    }


def error(
    err_code: str,
    err_message: str,
    http_status: int = 500,
) -> dict:
    return {
        "status": False,
        "errCode": err_code,
        "errMessage": err_message,
        "httpStatus": http_status,
    }
