from selenium.webdriver.common.by import By

# Login page locators
USERNAME_LOCATORS = [
    (By.NAME, "username", 1),
    (By.ID, "guac-field-cz1gpfe58l7ktoee-m87f4ei6", 2),
    (By.CSS_SELECTOR, "div.text-field input[type='text']", 3)
]

PASSWORD_LOCATORS = [
    (By.NAME, "password", 1),
    (By.CLASS_NAME, "password-field", 3),
    (By.CSS_SELECTOR, "div.password-field input[type='password']", 2)
]

LOGIN_BUTTON_LOCATORS = [
    (By.NAME, "login", 1),
    (By.CLASS_NAME, "login", 2),
]

# Dropdown and logout locators
DROPDOWN_LOCATORS = [
    (By.CLASS_NAME, "user-men43u", 1),
    (By.CSS_SELECTOR, "div.user-menu.ng-isolate-scope", 2),
    (By.XPATH, "//div[@ng-show='isAnonymous()']", 3),
]

LOGOUT_LOCATORS = [
    (By.CLASS_NAME, "ng-binding.logout", 1),
    (By.XPATH, "//a[text()='Logout']", 2),
    (By.CSS_SELECTOR, "a.ng-binding.logout", 3),
    (By.XPATH, "//li[contains(@ng-repeat, 'action in actions')]/a", 4),
]

RELOGIN_BUTTON_LOCATORS = [
    (By.XPATH, "//button[text()='Re-login']", 1),
    (By.XPATH, "//button[@ng-click='reAuthenticate()']", 2),
    (By.XPATH, "//button[@translate='APP.ACTION_LOGIN_AGAIN']", 3),
    (By.CSS_SELECTOR, "button.ng-scope", 4),
]
