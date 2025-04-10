from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import datetime

from Functions import (
    open_application, 
    login,
    terminal_ready,
    run_commands_with_exception_handling,
    logout
)

#Setup 
chrome_options = Options()
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--disable-search-engine-choice-screen")
prefs = {
    "profile.default_content_setting_values.clipboard": 1,  # 1 = Allow, 2 = Block
    "profile.default_content_setting_values.clipboard-read": 1,
    "profile.default_content_setting_values.clipboard-write": 1
}
chrome_options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=chrome_options)
driver.set_window_size(300, 700)


# Clear any previous error log
open("pass_fail.txt", "w").close()

def test_results(message):
    clean_message = message.split("Stacktrace:")[0].strip()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {clean_message}"
    print(f"{formatted_message}")
    
    with open("pass_fail.txt", "a") as test_result_file:
        test_result_file.write(formatted_message + "\n")



    #########################
###### -BEGINNING OF TEST- ######
    #########################

#Verifies that the url is reachable. 
resposne = open_application(driver, "https://guac-demo.iik.ntnu.no", 20)
test_results(resposne)
if "FAILED" in resposne:
    exit()

#login
res_login = login(driver)
test_results(res_login)
if "FAILED" in res_login:
    exit()

#Terminal of container is ready
terminal, log_message = terminal_ready(driver)
test_results(log_message)
if "FAILED" in log_message:
    exit()


#Run commands 
results, clip_res = run_commands_with_exception_handling("commands.txt", terminal, driver, 30)
for result in results:
    test_results(result)
for clip in clip_res:
    test_results(clip)


#logout 
res_logout = logout(driver)
test_results(res_logout)
if "FAILED" in res_logout:
    exit()

#End of test execution
time.sleep(3)
driver.quit()
