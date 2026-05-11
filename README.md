# homeconnect

Simple Python client for the BSH Home Connect REST API implementing OAuth 2 authentication, REST calls, and SSE event stream parsing.

## Usage example

To use this library, you have to sign up to the [Home Connect Developer Portal](https://developer.home-connect.com/) and register a new application
to get a client ID, client secret, and redirect URI.

```python
from homeconnect import HomeConnect
hc = HomeConnect(my_clientid, my_clientsecret, my_redirecturi)
# open this URL in your web browser
print(hc.get_authurl())
# paste the resulting URL below as `auth_result` to get a token
hc.get_token(auth_result)
# list the existing appliances
hc.get_appliances()
```

## Simulator example

To test with the simulator, you can just use the sample file [examples/simulator_events.py](examples/simulator_events.py). First you need to prepare your Home Connect Developer Account as described [here](https://api-docs.home-connect.com/quickstart/?#authorization). Check out this repository and make sure you have the library installed in your python environment (`pip install -e .`). Afterwards you can run the `simulator_events.py` file. It will ask you for the Client ID, insert the one for `API Web Client` from the Applications page in your developer dashboard. A login page will be opened in your browser that requires you to login to your Home Connect account and grant access. After your approval, it will forward you to the quickstart guide. From this page you need to copy the full URL (it includes the authorization code) and paste it to the console that is running the `simulator_events.py`. That's already it. In the Home Connect Dashboard you can switch to the "Simulators" tab, play with the devices and see the events coming in your python console.

Note: In case the script fails with a message like "HomeAppliance is offline" make sure your devices in the simulator are marked as "Connected" and retry.

## Disclaimer

The package and its author are not affiliated with BSH or Home Connect. Use at your own risk.

## License

The package is released under the MIT license.
