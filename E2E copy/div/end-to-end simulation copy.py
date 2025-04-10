from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time

# Disable choice of browser
chrome_options = Options()
chrome_options.add_argument("--disable-search-engine-choice-screen")
driver = webdriver.Chrome(options=chrome_options)

# Fetch the correct domain
driver.get("https://guacamole.iik.ntnu.no")
driver.implicitly_wait(0.5)

# Find the login elements and enter credentials
driver.find_element(By.NAME, "username").clear()
driver.find_element(By.NAME, "password").clear()
driver.find_element(By.NAME, "username").send_keys("osGJ")
driver.find_element(By.NAME, "password").send_keys("flipper7500")

# Click on login button and wait to make sure the connection is up
driver.find_element(By.NAME, "login").click()
time.sleep(5)


terminal = driver.find_element(By.TAG_NAME, "body")

with open("commands.txt", "r") as file: 
    commands = file.readlines()

    for command in commands:
        command = command.strip()  # Remove leading/trailing spaces
        if not command:
            continue  # Skip empty lines

        print(f"Running command: {command}")
        terminal.send_keys(command + Keys.ENTER)
        time.sleep(2)  # Adjust this sleep based on command execution time

        # Capture output (depends on your terminal's behavior)
        output = driver.find_element(By.TAG_NAME, "body").text
        print(f"Output for command '{command}':\n{output}")

# Write a command in the terminal
terminal = driver.find_element(By.TAG_NAME, "body")
terminal.send_keys("ls" + Keys.ENTER)

time.sleep(3)

# Create an ActionChain
actions = ActionChains(driver)
actions.key_down(Keys.SHIFT)
actions.key_down(Keys.CONTROL)
actions.key_down(Keys.COMMAND)
time.sleep(0.2)
actions.key_up(Keys.CONTROL)
actions.key_up(Keys.COMMAND)
actions.key_up(Keys.SHIFT)
actions.perform()


# Wait to see the output before the window automatically closes
time.sleep(40)
print("Login successful and Command+Control+Shift pressed.")
