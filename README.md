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

## Disclaimer

The package and its author are not affiliated with BSH or Home Connect. Use at your own risk.

## License

The package is released under the MIT license.
