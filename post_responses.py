import json
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException


# Path to the JSON file containing saved responses
RESPONSES_FILE_PATH = "assets/linkedin_responses.json"

# LinkedIn login URL
LOGIN_URL = "https://www.linkedin.com/login"

def pretty_display(message, message_type="INFO"):
    """
    Print a message with a colored border based on the message type.
    The border length is dynamically adjusted based on the longest line in the message.

    Parameters:
    - message (str): The message to display.
    - message_type (str): The type of message ('ERROR', 'WARNING', 'SUCCESS', 'INFO').
    """
    # Validate input types
    if not isinstance(message, str):
        raise ValueError("Message must be a string.")
    if message_type not in ['ERROR', 'WARNING', 'SUCCESS', 'INFO']:
        raise ValueError("Invalid message type. Choose from 'ERROR', 'WARNING', 'SUCCESS', 'INFO'.")

    # Split the message into lines
    lines = message.splitlines()

    # Find the length of the longest line
    max_length = max(len(line) for line in lines)

    # Define colors
    colors = {
        'ERROR': '\033[91m',  # Red
        'WARNING': '\033[93m',  # Yellow
        'SUCCESS': '\033[92m',  # Green
        'INFO': '\033[94m',  # Blue
        'RESET': '\033[0m'  # Reset to default
    }

    # Get the color for the message type
    color = colors[message_type]

    # Create the border
    border = '+' + '-' * (max_length + 2) + '+'

    # Print the formatted message
    print(color + border)
    for line in lines:
        print(color + '| ' + line.ljust(max_length) + ' |')
    print(color + border + colors['RESET'])
    

def load_json_data(file_path):
    """
    Load JSON data from the file. If the file is not found in the specified path,
    it checks the current working directory.

    Parameters:
    - file_path (str): The path to the JSON file.

    Returns:
    - dict or list: The loaded JSON data, or None if the file is not found or invalid.
    """
    try:
        # Check if the file exists in the specified path
        if not os.path.isfile(file_path):
            # If not, check the current working directory
            file_name = os.path.basename(file_path)
            current_dir_path = os.path.join(os.getcwd(), file_name)
            if os.path.isfile(current_dir_path):
                file_path = current_dir_path
            else:
                pretty_display(f"No New Comments to Reply so terminating this Process", 'WARNING')
                return None

        # Load the JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data

    except json.JSONDecodeError as e:
        pretty_display(f"Invalid JSON format in file: {file_path}. Error: {e}", 'SUCCESS')
        return None
    except Exception as e:
        pretty_display(f"Error loading JSON file: {e}", 'ERROR')
        return None

def login_to_linkedin(username, password, headless=False):
    """Log in to LinkedIn and return the WebDriver instance."""
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()

    # Optional headless mode
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service)#, options=chrome_options)
    driver.get(LOGIN_URL)

    try:
        # Input username and password
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )
        username_field.send_keys(username)

        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        password_field.send_keys(password)

        # Try to locate the "Remember me" checkbox
        try:
            remember_me_checkbox = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "rememberMeOptIn-checkbox"))
            )
            driver.execute_script("arguments[0].checked = false;", remember_me_checkbox)
        except TimeoutException:
            pretty_display("Remember me checkbox not found. Continuing...", 'INFO')

        # Click login
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "btn__primary--large"))
        )
        login_button.click()

        # Wait for CAPTCHA manual resolution
        pretty_display("If CAPTCHA is present, please solve it manually.", 'WARNING')
        input("Once logged in, press Enter to continue...")

        # Verify successful login
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "scaffold-layout"))
            )
            pretty_display("Login verified successfully!", 'SUCCESS')
        except TimeoutException:
            pretty_display("Login verification failed. Ensure you're on the homepage after CAPTCHA.", 'ERROR')
            driver.quit()
            return None

    except Exception as e:
        pretty_display(f"Login process encountered an error: {e}", 'ERROR')
        driver.quit()
        return None

    return driver

def reply_to_comment(driver, post_url, comment_text, commenter_name, ai_response):
#def reply_to_comment_with_xpath(driver, post_url, comment_text, commenter_name, ai_response):
    """Reply to a LinkedIn comment using XPath."""
    try:
        # Navigate to the post URL
        driver.get(post_url)
        time.sleep(5)  # Wait for the post to load

        # Scroll to load all comments
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new comments to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Find all comments
        comments = driver.find_elements(By.XPATH, "//article[contains(@class, 'comments-comment-entity')]")
        if not comments:
            pretty_display("No comments found on the post.", 'WARNING')
            return

        # Iterate through comments to find the matching one
        for comment in comments:
            try:
                # Get the commenter name
                commenter = WebDriverWait(comment, 10).until(
                    EC.presence_of_element_located((By.XPATH, ".//span[contains(@class, 'comments-comment-meta__description-title')]"))
                ).text.strip()  # Use strip() to remove extra whitespace

                # Get the comment text
                comment_content = comment.find_element(By.XPATH, ".//span[contains(@class, 'comments-comment-item__main-content')]").text

                # Check if the commenter name and comment text match
                if commenter_name in commenter and comment_text in comment_content:
                    print(f"Found matching comment from {commenter_name}: {comment_text}")

                    # Scroll the comment into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", comment)
                    time.sleep(2)

                    # Click the "Reply" button
                    try:
                        reply_button = WebDriverWait(comment, 10).until(
                            EC.element_to_be_clickable((By.XPATH, ".//button[contains(@aria-label, 'Reply')]"))
                        )
                        reply_button.click()
                        time.sleep(2)
                    except NoSuchElementException:
                        pretty_display("Reply button not found. Trying alternative method...", 'WARNING')
                        # Alternative method: Use JavaScript to click the Reply button
                        reply_button = comment.find_element(By.XPATH, ".//button[contains(@aria-label, 'Reply')]")
                        driver.execute_script("arguments[0].click();", reply_button)
                        time.sleep(2)

                    # Wait for the reply text box to be interactable
                    reply_box = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, ".//div[contains(@class, 'comments-comment-box--reply')]//div[@role='textbox']"))
                    )
                    reply_box.send_keys(ai_response)
                    time.sleep(2)

                    # Click the "Reply" button to post the response
                    post_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class, 'comments-comment-box__submit-button--cr')]"))
                    )
                    post_button.click()
                    time.sleep(3)

                    print(f"Replied to the comment with: {ai_response}")
                    break
            except NoSuchElementException as e:
                pretty_display(f"Error finding comment elements: {e}", 'ERROR')
                continue
            except Exception as e:
                pretty_display(f"Error processing comment: {e}", 'ERROR')
                continue
    except Exception as e:
        pretty_display(f"Error replying to comment: {e}", 'ERROR')


def main():
    # Load the saved responses
    responses = load_json_data(RESPONSES_FILE_PATH)
    if not responses:
        return

    username = "your_username"  # Replace with your credentials
    password = "your_password"  # Replace with your credentials

    driver = login_to_linkedin(username, password, headless=True)

    try:
        # Log in to LinkedIn
        if not driver:
            return

        # Process each response and reply to the comment
        for response in responses:
            post_url = response["Post URL"]
            commenter_name = response["Commenter Name"]
            comment_text = response["Comment Text"]
            ai_response = response["AI Response"]

            pretty_display(f"Processing comment on post: {post_url}", 'INFO')
            reply_to_comment(driver, post_url, comment_text, commenter_name, ai_response)
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()