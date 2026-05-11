from homeconnect import HomeConnect
import webbrowser
import time

SIMULATOR_API = 'https://simulator.home-connect.com'

def print_status(app):
    print(app.name, app.status)



if __name__ == '__main__':
    client_id = input("Please enter the client ID: ")
    client_secret = '' # not necessary for the simulator
    redirect_uri = 'https://api-docs.home-connect.com/quickstart/' # required by the api, all other values are blocked

    hc = HomeConnect(client_id, client_secret, redirect_uri, api_url=SIMULATOR_API)

    webbrowser.open(hc.get_authurl())

    auth_result = input("Please enter the URL redirected to: ")

    hc.get_token(auth_result)

    appliances = hc.get_appliances()

    for app in appliances:
        app.get_status()
        print_status(app)
        app.listen_events(callback=print_status)
