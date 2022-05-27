import json
import logging
import os
import time
from threading import Thread
from typing import Callable, Dict, Optional, Union

from oauthlib.oauth2 import TokenExpiredError
from requests import Response
from requests_oauthlib import OAuth2Session

from .sseclient import SSEClient

URL_API = "https://api.home-connect.com"
ENDPOINT_AUTHORIZE = "/security/oauth/authorize"
ENDPOINT_TOKEN = "/security/oauth/token"
ENDPOINT_APPLIANCES = "/api/homeappliances"
TIMEOUT_S = 120

LOGGER = logging.getLogger("homeconnect")


class HomeConnectError(Exception):
    pass


class HomeConnectAPI:
    def __init__(
        self,
        token: Optional[Dict[str, str]] = None,
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: str = None,
        api_url: Optional[str] = None,
        token_updater: Optional[Callable[[str], None]] = None,
    ):
        self.host = api_url or URL_API
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_updater = token_updater

        self._appliances = {}
        self.listening_events = False

        extra = {"client_id": self.client_id, "client_secret": self.client_secret}

        self._oauth = OAuth2Session(
            client_id=client_id,
            redirect_uri=redirect_uri,
            auto_refresh_kwargs=extra,
            token=token,
            token_updater=token_updater,
        )

    def refresh_tokens(self) -> Dict[str, Union[str, int]]:
        """Refresh and return new tokens."""
        LOGGER.info("Refreshing tokens ...")
        token = self._oauth.refresh_token(f"{self.host}{ENDPOINT_TOKEN}")

        if self.token_updater is not None:
            self.token_updater(token)

        return token

    def request(self, method: str, path: str, **kwargs) -> Response:
        """Make a request.

        We don't use the built-in token refresh mechanism of OAuth2 session because
        we want to allow overriding the token refresh logic.
        """
        url = f"{self.host}/{path.lstrip('/')}"
        try:
            return getattr(self._oauth, method)(url, **kwargs)
        except TokenExpiredError:
            LOGGER.warning("Token expired.")
            self._oauth.token = self.refresh_tokens()

            return getattr(self._oauth, method)(url, **kwargs)

    def get(self, endpoint):
        """Get data as dictionary from an endpoint."""
        res = self.request("get", endpoint)
        if not res.content:
            return {}
        try:
            res = res.json()
        except:
            raise ValueError("Cannot parse {} as JSON".format(res))
        if "error" in res:
            raise HomeConnectError(res["error"])
        elif "data" not in res:
            raise HomeConnectError("Unexpected error")
        return res["data"]

    def put(self, endpoint, data):
        """Send (PUT) data to an endpoint."""
        res = self.request(
            "put",
            endpoint,
            data=json.dumps(data),
            headers={
                "Content-Type": "application/vnd.bsh.sdk.v1+json",
                "accept": "application/vnd.bsh.sdk.v1+json",
            },
        )
        if not res.content:
            return {}
        try:
            res = res.json()
        except:
            raise ValueError("Cannot parse {} as JSON".format(res))
        if "error" in res:
            raise HomeConnectError(res["error"])
        return res

    def delete(self, endpoint):
        """Delete an endpoint."""
        res = self.request("delete", endpoint)
        if not res.content:
            return {}
        try:
            res = res.json()
        except:
            raise ValueError("Cannot parse {} as JSON".format(res))
        if "error" in res:
            raise HomeConnectError(res["error"])
        return res

    def get_appliances(self):
        """Return a list of `HomeConnectAppliance` instances for all
        appliances."""

        appliances = {}

        data = self.get(ENDPOINT_APPLIANCES)
        for home_appliance in data["homeappliances"]:
            haId = home_appliance["haId"]

            if haId in self._appliances:
                appliances[haId] = self._appliances[haId]
                appliances[haId].connected = home_appliance["connected"]
                continue

            appliances[haId] = HomeConnectAppliance(self, **home_appliance)

        self._appliances = appliances
        return list(self._appliances.values())

    def get_authurl(self):
        """Get the URL needed for the authorization code grant flow."""
        authorization_url, _ = self._oauth.authorization_url(
            f"{self.host}/{ENDPOINT_AUTHORIZE}"
        )
        return authorization_url

    def listen_events(self):
        """Spawn a thread with an event listener that updates the status."""
        self.listening_events = True
        uri = f"{self.host}/api/homeappliances/events"
        sse = SSEClient(uri, session=self._oauth, retry=1000, timeout=TIMEOUT_S)
        Thread(target=self._listen, args=[sse]).start()

    def _listen(self, sse):
        """Worker function for listener."""
        LOGGER.info("Listening to event stream for all devices")
        try:
            for event in sse:
                try:
                    for appliance in self._appliances.values():
                        if appliance.haId == event.id:
                            self.handle_event(event, appliance)
                            break
                except ValueError:
                    pass
        except TokenExpiredError:
            LOGGER.info("Token expired in event stream.")
            self._oauth.token = self.refresh_tokens()
            uri = f"{self.host}/api/homeappliances/events"
            sse = SSEClient(uri, session=self._oauth, retry=1000, timeout=TIMEOUT_S)
            self._listen(sse)

    def handle_event(self, event, appliance):
        """Handle a new event.

        Updates the status with the event data and executes any callback
        function."""
        event_data = json.loads(event.data)
        items = event_data.get("items")
        if items is not None:
            d = self.json2dict(items)
            appliance.status.update(d)
            if appliance.event_callback is not None:
                appliance.event_callback(appliance)
        else:
            LOGGER.warning("No items in event data: %s", event_data)

    @staticmethod
    def json2dict(lst):
        """Turn a list of dictionaries where one key is called 'key'
        into a dictionary with the value of 'key' as key."""
        return {d.pop("key"): d for d in lst}


class HomeConnect(HomeConnectAPI):
    """Connection to the HomeConnect OAuth API."""

    def __init__(
        self,
        client_id,
        client_secret="",
        redirect_uri="",
        api_url: Optional[str] = None,
        token_cache=None,
    ):
        """Initialize the connection."""
        self.token_cache = token_cache or "homeconnect_oauth_token.json"
        super().__init__(
            None, client_id, client_secret, redirect_uri, api_url, self.token_dump
        )

    def token_dump(self, token):
        """Dump the token to a JSON file."""
        with open(self.token_cache, "w") as f:
            json.dump(token, f)

    def token_load(self):
        """Load the token from the cache if exists it and is not expired,
        otherwise return None."""
        if not os.path.exists(self.token_cache):
            return None
        with open(self.token_cache, "r") as f:
            token = json.load(f)
        now = int(time.time())
        token["expires_in"] = token.get("expires_at", now - 1) - now
        return token

    def token_expired(self, token):
        """Check if the token is expired."""
        now = int(time.time())
        return token["expires_at"] - now < 60

    def get_token(self, authorization_response):
        """Get the token given the redirect URL obtained from the
        authorization."""
        LOGGER.info("Fetching token ...")
        token = self._oauth.fetch_token(
            f"{self.host}/{ENDPOINT_TOKEN}",
            authorization_response=authorization_response,
            client_secret=self.client_secret,
        )
        self.token_dump(token)


class HomeConnectAppliance:
    """Class representing a single appliance."""

    def __init__(
        self,
        hc,
        haId,
        vib=None,
        brand=None,
        type=None,
        name=None,
        enumber=None,
        connected=False,
    ):
        self.hc = hc
        self.haId = haId
        self.vib = vib or ""
        self.brand = brand or ""
        self.type = type or ""
        self.name = name or ""
        self.enumber = enumber or ""
        self.connected = connected
        self.status = {}

        self.event_callback = None

    def __repr__(self):
        return "HomeConnectAppliance(hc, haId='{}', vib='{}', brand='{}', type='{}', name='{}', enumber='{}', connected={})".format(
            self.haId,
            self.vib,
            self.brand,
            self.type,
            self.name,
            self.enumber,
            self.connected,
        )

    def listen_events(self, callback=None):
        """Register event callback method"""
        self.event_callback = callback

        if not self.hc.listening_events:
            self.hc.listen_events()

    @staticmethod
    def json2dict(lst):
        """Turn a list of dictionaries where one key is called 'key'
        into a dictionary with the value of 'key' as key."""
        return {d.pop("key"): d for d in lst}

    def get(self, endpoint):
        """Get data (as dictionary) from an endpoint."""
        return self.hc.get("{}/{}{}".format(ENDPOINT_APPLIANCES, self.haId, endpoint))

    def delete(self, endpoint):
        """Delete endpoint."""
        return self.hc.delete(
            "{}/{}{}".format(ENDPOINT_APPLIANCES, self.haId, endpoint)
        )

    def put(self, endpoint, data):
        """Send (PUT) data to an endpoint."""
        return self.hc.put(
            "{}/{}{}".format(ENDPOINT_APPLIANCES, self.haId, endpoint), data
        )

    def get_programs_active(self):
        """Get active programs."""
        return self.get("/programs/active")

    def get_programs_selected(self):
        """Get selected programs."""
        return self.get("/programs/selected")

    def get_programs_available(self):
        """Get available programs."""
        programs = self.get("/programs/available")
        if not programs or "programs" not in programs:
            return []
        return [p["key"] for p in programs["programs"]]

    def get_program_options(self, program_key):
        """Get program options."""
        options = self.get(f"/programs/available/{program_key}")
        if not options or "options" not in options:
            return []
        return [{p["key"]: p} for p in options["options"]]

    def start_program(self, program_key, options=None):
        """Start a program."""
        if options is not None:
            return self.put(
                "/programs/active", {"data": {"key": program_key, "options": options}}
            )
        return self.put("/programs/active", {"data": {"key": program_key}})

    def stop_program(self):
        """Stop a program."""
        return self.delete("/programs/active")

    def select_program(self, program, options=None):
        """Select a program."""
        if options is None:
            _options = {}
        else:
            _options = {"options": options}
        return self.put("/programs/selected", {"data": {"key": program, **_options}})

    def get_status(self):
        """Get the status (as dictionary) and update `self.status`."""
        status = self.get("/status")
        if not status or "status" not in status:
            return {}
        self.status = self.json2dict(status["status"])
        return self.status

    def get_settings(self):
        """Get the current settings."""
        settings = self.get("/settings")
        if not settings or "settings" not in settings:
            return {}
        self.status.update(self.json2dict(settings["settings"]))
        return self.status

    def set_setting(self, settingkey, value):
        """Change the current setting of `settingkey`."""
        return self.put(
            "/settings/{}".format(settingkey),
            {"data": {"key": settingkey, "value": value}},
        )

    def set_options_active_program(self, option_key, value, unit=None):
        """Change the option `option_key` of the currently active program."""
        if unit is None:
            _unit = {}
        else:
            _unit = {"unit": unit}
        return self.put(
            f"/programs/active/options/{option_key}",
            {"data": {"key": option_key, "value": value, **_unit}},
        )

    def set_options_selected_program(self, option_key, value, unit=None):
        """Change the option `option_key` of the currently selected program."""
        if unit is None:
            _unit = {}
        else:
            _unit = {"unit": unit}
        return self.put(
            f"/programs/selected/options/{option_key}",
            {"data": {"key": option_key, "value": value, **_unit}},
        )

    def execute_command(self, command):
        """Execute a command."""
        return self.put(
            f"/commands/{command}",
            {"data": {"key": command, "value": True}},
        )
