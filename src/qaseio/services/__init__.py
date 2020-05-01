from typing import Callable, List, Type, TypeVar, Union

import attr
from apitist.constructor import converter
from apitist.requests import Session
from requests import Response


class TooManyRequestsException(Exception):
    pass


T = TypeVar("T")


@attr.s
class BaseService:
    s: Session = attr.ib()
    path: Callable[[str], str] = attr.ib()

    @staticmethod
    def validate_response(
        res: Response, to_type: Type[T], status: Union[int, List[int]] = 200
    ) -> T:
        if isinstance(status, int):
            status = [status]

        if res.status_code == 429:
            raise TooManyRequestsException("Too many requests")

        if res.status_code not in status:
            raise ValueError(
                "Got unexpected status code: {} {}".format(
                    res.status_code, res.content
                )
            )
        try:
            data = res.json()
            if data.get("status") is True and to_type:
                return converter.structure(data.get("result"), to_type)
            elif data.get("status") is True:
                return data.get("result")
        except Exception as e:
            raise ValueError("Unable to parse response {}".format(e))
        raise ValueError("Got error during response: {}".format(res.content))

    vr = validate_response
