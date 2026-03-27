from homeconnect import HomeConnect
import webbrowser


def print_status(app):
    print(app.name, app.status)

if __name__ == '__main__':
    client_id = input("Please enter the client ID: ")
    client_secret = input("Please enter the client secret: ")
    redirect_uri = input("Please enter your redirecturl (empty -> https://example.com): ")
    if redirect_uri == "":
        redirect_uri = 'https://example.com'

    hc = HomeConnect(client_id, client_secret, redirect_uri)

    webbrowser.open(hc.get_authurl())

    auth_result = input("Please enter the URL redirected to: ")

    hc.get_token(auth_result)

    appliances = hc.get_appliances()

    for app in appliances:
        app.get_status()
        print_status(app)
        app.listen_events(callback=print_status)
