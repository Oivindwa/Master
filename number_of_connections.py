import requests
import time

GUAC_URL = "https://guac-demo.iik.ntnu.no/guacamole"
USERNAME = "oivindwa"
PASSWORD = "Trumannrr1901N%"

def get_auth_token():
    """
    Logs into Guacamole with the given USERNAME/PASSWORD
    and returns the authToken string.
    """
    login_endpoint = f"{GUAC_URL}/api/tokens"
    payload = {"username": USERNAME, "password": PASSWORD}
    resp = requests.post(login_endpoint, data=payload)
    resp.raise_for_status()

    json_data = resp.json()
    return json_data["authToken"] 

def main():
    token = get_auth_token()
    print(f"Got token: {token[:12]}...")

    while True:
        try:
            conn_url = f"{GUAC_URL}/api/session/data/mysql/connections/3"
            resp = requests.get(conn_url, params={"token": token})
            resp.raise_for_status()

            data = resp.json()
            active_count = data.get("activeConnections", 0)

            if active_count == 0:
                print("-")
            else:
                print(f"Total number of active connections: {active_count}")

        except Exception as e:
            print(f"Error during retrieval: {e}")

        # Sleep 1 seconds before polling again
        time.sleep(1)

if __name__ == "__main__":
    main()
