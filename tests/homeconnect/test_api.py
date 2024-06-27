"""Tests for api classes."""

from requests.adapters import HTTPAdapter
import responses
from responses import registries

from homeconnect.api import ENDPOINT_APPLIANCES, TOTAL_RETRIES, URL_API, HomeConnectAPI

return_200_message = {
    "data": {
        "homeappliances": [
            {
                "name": "My Bosch Oven",
                "brand": "BOSCH",
                "vib": "HNG6764B6",
                "connected": True,
                "type": "Oven",
                "enumber": "HNG6764B6/09",
                "haId": "BOSCH-HNG6764B6-0000000011FF",
            }
        ]
    },
}


return_429_message = {
    "error": {
        "key": "429",
        "description": "The user has sent too many requests in a given amount of time.",
    }
}


def test_api() -> None:
    hc_api = HomeConnectAPI()
    assert hc_api.client_id is None


@responses.activate(registry=registries.OrderedRegistry)
def test_429_retry():
    """Test retries on 429 response status."""
    appliances_url = URL_API + ENDPOINT_APPLIANCES

    rsp_objs = [
        responses.get(
            appliances_url,
            json=return_429_message,
            status=429,
            headers={"Retry-After": "1"},
        )
        for _ in range(TOTAL_RETRIES)
    ]

    rsp_objs.append(responses.get(appliances_url, json=return_200_message, status=200))

    hc_api = HomeConnectAPI()

    adapter = HTTPAdapter(max_retries=hc_api.retry)

    hc_api._oauth.mount("https://", adapter)

    resp = hc_api.request("get", ENDPOINT_APPLIANCES)

    assert resp.status_code == 200
    for rsp in rsp_objs:
        assert rsp.call_count == 1


@responses.activate(registry=registries.OrderedRegistry)
def test_429_max_retry_exception():
    """Test max retries on 429 response status."""
    appliances_url = URL_API + ENDPOINT_APPLIANCES

    rsp_objs = [
        responses.get(
            appliances_url,
            json=return_429_message,
            status=429,
            headers={"Retry-After": "1"},
        )
        for _ in range(TOTAL_RETRIES)
    ]

    # Add one more than the number of retries.
    rsp_objs.append(
        responses.get(
            appliances_url,
            json=return_429_message,
            status=429,
            headers={"Retry-After": "1"},
        )
    )

    # Will not be called.
    rsp_objs.append(responses.get(appliances_url, json=return_200_message, status=200))

    hc_api = HomeConnectAPI()

    adapter = HTTPAdapter(max_retries=hc_api.retry)

    hc_api._oauth.mount("https://", adapter)

    resp = hc_api.request("get", ENDPOINT_APPLIANCES)

    assert rsp_objs[-1].call_count == 0
    assert resp is None
