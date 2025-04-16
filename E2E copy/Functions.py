import datetime
from time import sleep, time
import re
from operator import itemgetter
from PIL import Image
import pytesseract
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException,
    NoSuchElementException
)

from locators import (
    USERNAME_LOCATORS,
    PASSWORD_LOCATORS,
    LOGIN_BUTTON_LOCATORS,
    DROPDOWN_LOCATORS,
    LOGOUT_LOCATORS,
    RELOGIN_BUTTON_LOCATORS
)

open("error_log.txt", "w").close()

def log_error(error_message):
    clean_message = error_message.split("Stacktrace:")[0].strip()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {clean_message}"
    print(f"Error: {formatted_message}")
    
    with open("error_log.txt", "a") as log_file:
        log_file.write(formatted_message + "\n")


def wait_for_best_locator(driver, locators, timeout):
    locators = sorted(locators, key=itemgetter(2))  
    for by, value, weight in locators:
        try:
            print(f"Trying locator: {by}='{value}' (weight: {weight})")
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            print(f"Found element: {element.text} (weight: {weight})")
            return element  
        except Exception as e:
            log_error(f"Failed locator: {by}='{value}' (weight: {weight}) -- ERROR: {e}")

    raise Exception(f"No matching element found using any locators: {locators}")


def open_application(driver, url, app_timeout):
    driver.set_page_load_timeout(app_timeout)
    try:
        driver.get(url)
        return "PASSED - Open Application"
    except TimeoutException as e:
        log_error(f"Error: Application failed to load within {app_timeout} seconds -- ERROR MESSAGE: {e}")
        log = (f"FAILED - Open Application - Error: {e}")
        return log
    except WebDriverException as e:
        log_error(f"Web Driver Exception -- ERROR MESSAGE: {e}")
        log = (f"FAILED - Open Application - Error: {e}")
        return log
    except Exception as e:
        log_error(f"Failed to load application -- ERROR MESSAGE: {e}")
        log = (f"FAILED - Open Application - Error: {e}")
    driver.quit()
    return log

def read_cred():
    try:
        with open('credentials.json', 'r') as file:
            credentials = json.load(file)
            username = credentials.get('username')
            password = credentials.get('password')

            return username, password
            
    except FileNotFoundError:
        error_msg = f"FAILED - File credentials.json not found. Ensure the file is in the correct directory."
        print(error_msg)
        return "Error", "Error"


def login(driver):
    try:
        wait = WebDriverWait(driver, 100)
        terminal = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        test2 = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.password-field input[type='password']")))
        test3 = wait.until(EC.element_to_be_clickable((By.NAME, "username")))


        print(f"FOUND IT!!!  --- {test2} -- ")
    except Exception as e:
        print("DIDNT WORK ")
    cred_user, cred_pass = read_cred()
    try:
        username_field = wait_for_best_locator(driver, USERNAME_LOCATORS, 5)
        username_field.clear()
        username_field.send_keys(cred_user)

        password_field = wait_for_best_locator(driver, PASSWORD_LOCATORS, 5)
        password_field.clear()
        password_field.send_keys(cred_pass)

        login_button = wait_for_best_locator(driver, LOGIN_BUTTON_LOCATORS, 5)
        login_button.click()

        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".login-error"))
            )
            return "FAILED - Logged into Guacamole"
        except TimeoutException:
            return "PASSED - Logged into Guacamole"


    except NoSuchElementException as e:
        log_error(f"Login failed: {e}")
        return (f"FAILED - Logged in to Guacamole - Error: {e}")
    except Exception as e:
        log_error(f"ERROR: {e}")
        log = (f"FAILED - Logged in to Guacamole - Error: {e}")
    driver.quit()
    return log


def terminal_ready(driver):
    try:
        wait = WebDriverWait(driver, 20)
        terminal = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("Terminal loaded successfully.")
        log = "PASSED - Connection to Linux container established"
        return terminal, log
    except TimeoutException as e:
        log_error(f"Terminal did not load in time: {e}")
        driver.quit()
        log = "FAILED - Connection to Linux container established"
        return "NOTHING", log



def wait_for_prompt(driver, crop_box, timeout, stage, command):
    start_time = time()
    while True:
        elapsed_time = time() - start_time
        if elapsed_time > timeout:
            if stage == 'before':
                return (False, f"FAILED - Timeout waiting for prompt BEFORE executing command: {command}")
            else:
                return (False, f"FAILED - Timeout waiting for prompt AFTER executing command: {command}")
        
        sleep(0.5)
        driver.save_screenshot("test.png")
        screenshot = Image.open("test.png")
        cropped_screenshot = screenshot.crop(crop_box)
        resized_screenshot = cropped_screenshot.resize(
            (cropped_screenshot.width * 2, cropped_screenshot.height * 2),
            Image.LANCZOS
        )
        grayscale = resized_screenshot.convert("L")
        text = pytesseract.image_to_string(grayscale)
        
        if ":~$" in text:
            if stage == 'before':
                print("Prompt is ready before executing the command.")
            else:
                print("Prompt has reappeared after executing the command.")
            return (True, text.strip())
        else:
            if stage == 'before':
                print("Waiting for prompt before executing the command...")
            else:
                print("Still waiting for prompt after executing the command...")



def copy_text_to_clipboard(driver, text_to_copy):
    open_result = open_clipboard(driver)
    print(open_result)
    
    try:
        wait = WebDriverWait(driver, 10)
        clipboard_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea.clipboard"))
        )
        clipboard_element.clear()
        clipboard_element.send_keys(text_to_copy)
        sleep(1)
        return True

    except Exception as e:
        print(f"Failed to write text to clipboard: {e}")
        return False

    finally:
        close_result = close_clipboard(driver)
        print(close_result)


def open_clipboard(driver):
    try: 
        actions = ActionChains(driver)
        actions.key_down(Keys.SHIFT)
        actions.key_down(Keys.CONTROL)
        actions.key_down(Keys.COMMAND)
        sleep(0.2)
        actions.key_up(Keys.CONTROL)
        actions.key_up(Keys.COMMAND)
        actions.key_up(Keys.SHIFT)
        actions.perform()

        return "PASSED - Opening Clipboard"

    except Exception as e:
        log_error(f"Logout failure ERROR: {e}")
        return (f"FAILED - Opening Clipboard - Error: {e}")
    
def close_clipboard(driver):
    try: 
        actions = ActionChains(driver)
        actions.key_down(Keys.SHIFT)
        actions.key_down(Keys.CONTROL)
        actions.key_down(Keys.COMMAND)
        sleep(0.2)
        actions.key_up(Keys.CONTROL)
        actions.key_up(Keys.COMMAND)
        actions.key_up(Keys.SHIFT)
        actions.perform()

        return "PASSED - Closing Clipboard"

    except Exception as e:
        log_error(f"Logout failure ERROR: {e}")
        return (f"FAILED - Closing Clipboard - Error: {e}")




def run_commands_with_exception_handling(file, terminal, driver, timeout):
    results = []  
    clipboard = []
    
    try:
        with open(file, "r") as f:
            commands = f.readlines()
    except FileNotFoundError:
        error_msg = f"FAILED - File '{file}' not found. Ensure the file is in the correct directory."
        print(error_msg)
        results.append(error_msg)
        return results

    crop_box = (0, 0, 800, 600)
    
    for command in commands:
        command = command.strip()
        if not command:
            continue  

        success, msg = wait_for_prompt(driver, crop_box, timeout, stage='before', command=command)
        if not success:
            print(msg)
            results.append(msg)
            continue 

        terminal.send_keys(command + Keys.ENTER)
        print(f"Command '{command}' executed. Waiting for prompt to reappear...")

        success, msg = wait_for_prompt(driver, crop_box, timeout, stage='after', command=command)
        if not success:
            print(msg)
            results.append(msg)
        else:
            result = f"PASSED - Command '{command}' executed successfully."
            print(result)
            results.append(result)
            clipboard_success = copy_text_to_clipboard(driver, command)
            if clipboard_success: 
                clipboard.append(f"PASSED - Copy command: {command} to clipboard")
            else: 
                clipboard.append(f"FAILED - Copy command: {command} to clipboard")

    
    return results, clipboard

def logout(driver):
    sleep(10)
    try:
        clip_res = open_clipboard(driver)
        print(clip_res)

        sleep(1)
        dropdown_menu = wait_for_best_locator(driver, DROPDOWN_LOCATORS, timeout=4)
        dropdown_menu.click()
        sleep(1)
        logout_button = wait_for_best_locator(driver, LOGOUT_LOCATORS, timeout=4)
        logout_button.click()
        sleep(1)
        succ_logout = wait_for_best_locator(driver, RELOGIN_BUTTON_LOCATORS, timeout=4)
        succ_logout.click()

        return "PASSED - Logging out of Guacamole"
    
    except NoSuchElementException as e:
        log_error(f"Logout failed: {e}")
        return (f"FAILED - Logging out of Guacamole - Error: {e}")
    except Exception as e:
        log_error(f"Logout failure ERROR: {e}")
        log = (f"FAILED - Logging out of Guacamole - Error: {e}")
    driver.quit()
    return log
