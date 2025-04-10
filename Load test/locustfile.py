from locust import HttpUser, between, task, User
import json
import random
import time
import logging
import ssl
import gevent
import websocket
import base64
from collections import deque

logging.basicConfig(level=logging.ERROR)

# Shared dictionary for storing authentication tokens
#shared_tokens = []
shared_tokens = deque()


def get_credentials_from_json(json_file):
    """ Load user credentials from a JSON file. """
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading credentials: {e}")
        return []

user_credentials = get_credentials_from_json("s.json")

def load_commands_from_file(file_path):
    commands = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                commands.append(line)
    return commands

all_commands = load_commands_from_file("commands.txt")


class GuacamoleHttpUser(HttpUser):
    """ Handles HTTP-based authentication and token retrieval. """
    host = "https://guac-demo.iik.ntnu.no"
    wait_time = between(5, 10)

    def on_start(self):
        self.front_page()
        self.login()
    

    def front_page(self):
        """ Visit the Guacamole front page. """
        
        with self.client.get("/guacamole/#/", catch_response=True) as res:
            if res.status_code > 299:
                error_message = f"Failed to access front page: {res.status_code}"
                logging.error("Can NOT Access Front Page", error_message) 
        

    def login(self):
        """ Authenticate and store auth token with improved error handling. """
        credentials = random.choice(user_credentials)
        username = credentials["username"]
        password = credentials["password"]
        
  
        with self.client.post("/guacamole/api/tokens", 
                                data={"username": username, "password": password},
                                catch_response=True, timeout=60) as response:
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    auth_token = json_response.get("authToken")
                    
                    if auth_token:
                        #shared_tokens.append(auth_token)
                        shared_tokens.appendleft(auth_token)  # Use appendleft() to maintain FIFO order

                    else:
                        raise ValueError("Auth token missing in response")
                except json.JSONDecodeError:
                    logging.error("Invalid JSON response", response.text)
            
            else:
                logging.error("Login failed with status %s, details: %s", response.status_code, response.text)
    

    @task
    def keep_alive(self):
        """ A dummy task to keep HTTP users alive. """
        pass


    #on stop - https://guac-demo.iik.ntnu.no/guacamole/api/session DELETE






class GuacamoleWebSocketUser(User):
    """Simulates WebSocket-based SSH interactions via Guacamole."""
    
    host = "wss://guac-demo.iik.ntnu.no"
    wait_time = between(1, 10)

    def on_start(self):
        """Wait for authentication to be ready, then connect WebSocket and start listening."""
        while not shared_tokens:
            gevent.sleep(1)

        self.auth_token = shared_tokens.popleft()  # Use popleft() for thread-safe removal
        self.sync_id = None
        #self.auth_token = shared_tokens.pop(0)

        self.websocket_connection()
        gevent.sleep(2)
        gevent.spawn(self.listen_for_messages)  
        gevent.spawn(self.start_keep_alive) 

    def websocket_connection(self):
        if not self.auth_token:
            logging.error("No auth token found. WebSocket connection aborted.")
            return

        ws_url = f"wss://guac-demo.iik.ntnu.no/guacamole/websocket-tunnel?token={self.auth_token}&GUAC_DATA_SOURCE=mysql&GUAC_ID=3&GUAC_TYPE=c"
        start_time = time.time()
        try:
            self.ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})
            gevent.sleep(2)
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WS", 
                name="Opened Connections",
                response_time=total_time, 
                response_length=0,  
                exception=None,
            )

      
        except Exception as e:
            logging.error(f"⛔ WebSocket connection error: {e}")
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WS",
                name="Failed Open Connection",
                response_time=total_time,
                response_length=0,
                exception=e,
            )
            self.ws = None


    def listen_for_messages(self):
        """Wait for incoming WS messages and detect 4.sync frames."""
        if not self.ws:
            return
        self.ws.settimeout(15)  # e.g. 15s to avoid blocking forever

        while self.ws.connected:
            try:
                msg = self.ws.recv()
                logging.debug(f"WS Received: {msg}")

                # If there's a 4.sync message, store the sync_id
                if "4.sync," in msg:
                    sync_fragment = msg.split("4.sync,")[1].split(";")[0]
                    self.sync_id = sync_fragment
                    logging.debug(f"[WebSocket] Received sync_id={self.sync_id}")
                elif "4.blob" in msg:
                    # something like "4.blob,1.86.iVBORw0KGgoAAAANSUhEU..."
                    # parse out the base64 text after the last comma
                    parts = msg.split(",")
                    base64_data = parts[-1].split(";")[0]  # remove trailing semicolon
                    try:
                        decoded_output = base64.b64decode(base64_data).decode("utf-8", errors="replace")
                        logging.debug(f"[SSH output] {decoded_output}")
                        # You can do any further checks to confirm command success
                    except Exception as e:
                        logging.debug(f"Error decoding blob: {e}")
            except websocket.WebSocketTimeoutException:
                # Timed out waiting for messages, no big deal—just loop again
                continue
            except Exception as e:
                logging.error(f"[WebSocket] Receive error: {e}")
                break


    def start_keep_alive(self):
        if not self.ws:
            return

        start_time = time.time()
        while True:
            if not self.ws.connected:
                self.environment.events.request.fire(
                    request_type="WS",
                    name="Keep-alive",
                    response_time=int((time.time() - start_time) * 1000),
                    response_length=0,
                    exception=RuntimeError("WebSocket no longer connected"),
                )
                logging.debug("[WebSocket] Not connected anymore, stop keep-alive loop.")
                break

            try:
                # Send Guacamole's "nop"
                self.ws.send("3.nop;")
                logging.debug("Sent 3.nop;")

                # If we have a sync_id from the server, use it
                if self.sync_id:
                    self.ws.send(f"4.sync,{self.sync_id};")
                    logging.debug(f"Sent 4.sync,{self.sync_id};")

                total_time = int((time.time() - start_time) * 1000)
                self.environment.events.request.fire(
                    request_type="WS",  # or "WS"
                    name="Keep-alive",
                    response_time=total_time,
                    response_length=0,
                    exception=None,
                )
                
                # Wait 5s before next keep-alive
                gevent.sleep(5)

            except Exception as e:
                # Mark as a failure in Locust
                total_time = int((time.time() - start_time) * 1000)
                self.environment.events.request.fire(
                    request_type="WS",
                    name="Failed keep-alive",
                    response_time=total_time,
                    response_length=0,
                    exception=e,
                )
                logging.error(f"[WebSocket] Keep-alive error: {e}")
                break  # Stop keep-alive loop



    def guac_instruction(self, opcode, *args):
        """
        Encode a Guacamole instruction in the form:
          N.opcode,<length-of-arg1>.<arg1>,...,<length-of-argN>.<argN>;
        where N is the total number of tokens (1 for opcode + one per argument).
        Example: self.guac_instruction("key", "108", "1") -> "3.key,3.108,1.1;"
        """
        tokens = [opcode] + list(args)
        if not tokens:
            return "0.;"  # Edge case: empty

        # First token is prefixed by the total token count.
        N = len(tokens)
        opcode_part = f"{N}.{tokens[0]}"  # e.g. "3.key"

        # Each subsequent argument is prefixed by its length.
        arg_parts = [f"{len(t)}.{t}" for t in tokens[1:]]
        all_parts = [opcode_part] + arg_parts
        return ",".join(all_parts) + ";"


    def send_command(self, command_string):
        start_time = time.time()
        try:
            for c in command_string:
                keysym = ord(c)

                # Key press
                press_msg = self.guac_instruction("key", str(keysym), "1")
                self.ws.send(press_msg)

                # Key release
                release_msg = self.guac_instruction("key", str(keysym), "0")
                self.ws.send(release_msg)

            # Finally press Enter
            press_enter = self.guac_instruction("key", "65293", "1")
            release_enter = self.guac_instruction("key", "65293", "0")
            self.ws.send(press_enter)
            self.ws.send(release_enter)

            # If no exception was raised, it's a success:
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WS",
                name="Commands Executed",
                response_time=total_time,
                response_length=0,
                exception=None,
            )

        except Exception as e:
            # If an error happens (EOF, etc.), mark it as a failure in Locust
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WS",
                name="failed sending command",
                response_time=total_time,
                response_length=0,
                exception=e,
            )
            # Re-raise if you want Locust to see the traceback or stop the user
            logging.debug("WebSocket send_command encountered an error")

            raise



    @task
    def run_commands_in_order(self):
        """ Execute each command in commands.txt sequentially. """
        for cmd in all_commands:
            self.send_command(cmd)
            # Add a small delay if you want to wait for output before sending next
            gevent.sleep(20)

        # Optionally, sleep to observe the last command's output
        gevent.sleep(100)

        self.stop()
        
        

    def on_stop(self):
        """Close the WebSocket on stop."""
        if hasattr(self, "ws") and self.ws:
            try:
                self.ws.close()
                logging.debug("⛔ WebSocket connection closed.")
            except:
                pass