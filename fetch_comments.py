import re
import csv
import random
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

LOGIN_URL = "https://www.linkedin.com/login"
ALL_ACTIVITY_URL = "https://www.linkedin.com/in/siddharamayya-mathapati/recent-activity/all/"  ## replace with your account name/url

# List of common user-agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    # Add more user agents if needed
]

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



def get_random_user_agent():
    return random.choice(USER_AGENTS)

def clean_text(text):
    """
    Clean the text by removing unwanted characters (e.g., emojis, special symbols).
    """
    if not text:
        return text

    # Remove emojis and special symbols
    text = re.sub(r"[^\w\s.,!?]", "", text)  # Keep alphanumeric, spaces, and basic punctuation
    text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with a single space
    return text.strip()

def login_to_linkedin(username, password, headless=False):
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
            pretty_display("Remember me checkbox not found. Continuing...", 'WARNING')

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

def scroll_to_load_all_posts(driver, max_scrolls=20, scroll_delay=5, retries=3):
    """
    Scrolls to the bottom of the page to load all posts, with retries and random delays.
    """
    scroll_count = 0
    retry_count = 0

    # Get the initial number of posts
    initial_posts = driver.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
    #pretty_display(f"Initial number of posts: {len(initial_posts)}", 'INFO')

    while scroll_count < max_scrolls:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        #pretty_display(f"Scrolled to bottom. Scroll count: {scroll_count + 1}", 'INFO')

        # Add a random delay to mimic human behavior
        time.sleep(random.uniform(2, 4))  # Increased delay for better loading

        # Wait for new content to load
        try:
            # Wait for at least one new post to appear
            WebDriverWait(driver, scroll_delay).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "feed-shared-update-v2")) > len(initial_posts)
            )
            # Update the initial_posts count
            initial_posts = driver.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
            #pretty_display(f"New posts loaded. Total posts: {len(initial_posts)}", 'INFO')
            retry_count = 0  # Reset retry count if new posts are loaded
        except TimeoutException:
            retry_count += 1
            #pretty_display(f"No new posts loaded. Retry count: {retry_count}", 'INFO')
            if retry_count >= retries:
                # If no new posts are loaded after retries, stop scrolling
                #pretty_display("Max retries reached. Stopping scrolling.", 'INFO')
                break
            continue  # Retry scrolling

        # Increment the scroll count
        scroll_count += 1

    #pretty_display(f"Finished scrolling. Total scrolls: {scroll_count}")

    
def get_and_save_all_activity_data(driver, output_file="assets/activity_data.csv"):
    """
    Fetches LinkedIn activity data and saves the `data-urn` attributes to a CSV file.
    """
    try:
        # Navigate to the All Activity page
        driver.get(ALL_ACTIVITY_URL)

        # Wait for the main content to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "scaffold-finite-scroll__content"))
        )

        # Scroll to load all posts
        scroll_to_load_all_posts(driver, max_scrolls=20, scroll_delay=5)

        # Find all activity sections
        all_activity_data = []
        activity_page = driver.find_element(By.CLASS_NAME, "scaffold-finite-scroll__content")
        activity_sections = activity_page.find_elements(By.CLASS_NAME, "feed-shared-update-v2")

        # Extract `data-urn` from each activity section
        for section in activity_sections:
            data_urn = section.get_attribute("data-urn")
            if data_urn:
                all_activity_data.append(data_urn)

        # Save data to CSV
        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Data URN"])  # Write header
            for urn in all_activity_data:
                writer.writerow([urn])

        pretty_display(f"Activity data successfully saved to {output_file}.", 'SUCCESS')

    except Exception as e:
        pretty_display(f"An error occurred: {e}", 'ERROR')


def load_all_comments(driver):
    """Load all comments and replies by clicking 'Load more comments' and 'See previous replies' buttons."""
    try:
        # Load more comments
        while True:
            try:
                # Find the "Load more comments" button
                load_more_button = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Load more comments')]"))
                )
                # Scroll the button into view and click it
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", load_more_button)
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(random.uniform(2, 4))  # Wait for comments to load
            except TimeoutException:
                break  # No more "Load more comments" buttons

        # Load previous replies
        while True:
            try:
                # Find the "See previous replies" button
                see_previous_replies_button = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'See previous replies')]"))
                )
                # Scroll the button into view and click it
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", see_previous_replies_button)
                driver.execute_script("arguments[0].click();", see_previous_replies_button)
                time.sleep(random.uniform(2, 4))  # Wait for replies to load
            except TimeoutException:
                break  # No more "See previous replies" buttons

    except Exception as e:
        pretty_display(f"Error loading comments or replies: {e}", 'ERROR')


def parse_comments(comment_section):
    """Parse comments and replies recursively, ensuring no duplicates."""
    comments = []
    seen_ids = set()  # Track seen comment/reply IDs to avoid duplicates

    # Find all top-level comments
    top_level_comments = comment_section.find_elements(By.CLASS_NAME, "comments-comment-entity")

    for comment in top_level_comments:
        try:
            # Extract the unique data-id attribute
            data_id = comment.get_attribute("data-id")
            if data_id in seen_ids:
                continue  # Skip if this comment/reply has already been processed
            seen_ids.add(data_id)  # Mark this ID as seen

            # Extract comment text
            comment_text = comment.find_element(By.CLASS_NAME, "comments-comment-item__main-content").text.strip()
            comment_text = clean_text(comment_text)

            # Extract commenter's name
            commenter_name = comment.find_element(By.CLASS_NAME, "comments-comment-meta__description-title").text.strip()
            commenter_name = clean_text(commenter_name)

            # Extract time commented
            time_commented_info = comment.find_element(By.CLASS_NAME, "comments-comment-meta__info")
            time_commented = time_commented_info.find_element(By.CLASS_NAME, "comments-comment-meta__data").text.strip()
            time_commented = clean_text(time_commented)

            # Initialize the comment dictionary
            comment_data = {
                "Comment Text": comment_text,
                "Commenter Name": commenter_name,
                "Time Commented": time_commented,
                "Replies": []
            }

            # Check if this comment has replies
            try:
                # Find the replies section
                replies_section = comment.find_element(By.CLASS_NAME, "comments-replies-list")
                # Find all replies within the replies section
                replies = replies_section.find_elements(By.CLASS_NAME, "comments-comment-entity--reply")
                for reply in replies:
                    try:
                        # Extract the unique data-id attribute for the reply
                        reply_data_id = reply.get_attribute("data-id")
                        if reply_data_id in seen_ids:
                            continue  # Skip if this reply has already been processed
                        seen_ids.add(reply_data_id)  # Mark this reply ID as seen

                        # Extract reply text
                        reply_text = reply.find_element(By.CLASS_NAME, "comments-comment-item__main-content").text.strip()
                        reply_text = clean_text(reply_text)

                        # Extract replyer's name
                        replyer_name = reply.find_element(By.CLASS_NAME, "comments-comment-meta__description-title").text.strip()
                        replyer_name = clean_text(replyer_name)
                        # Extract time replied
                        time_reply_info = reply.find_element(By.CLASS_NAME, "comments-comment-meta__info")
                        time_replied = time_reply_info.find_element(By.CLASS_NAME, "comments-comment-meta__data").text.strip()
                        time_replied = clean_text(time_replied)

                        # Append the reply data
                        comment_data["Replies"].append({
                            "Comment Text": reply_text,
                            "Commenter Name": replyer_name,
                            "Time Commented": time_replied,
                            "Replies": []  # Replies to replies are not handled here
                        })
                    except Exception as e:
                        pretty_display(f"Error parsing reply: {e}", 'ERROR')
            except NoSuchElementException:
                pass  # No replies found

            # Append the comment data
            comments.append(comment_data)

        except Exception as e:
            pretty_display(f"Error parsing comment: {e}", 'ERROR')

    return comments

def fetch_post_details_from_file(driver, input_file="assets/activity_data.csv"):
    """Fetch post details including content, author, time, and comments."""
    try:
        # Read the `data-urn` values from the input CSV file
        with open(input_file, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row
            urns = [row[0] for row in reader]  # Extract the data-urn column

        all_activity_data = []

        for data_urn in urns:
            try:
                # Construct the post URL
                post_url = f"https://www.linkedin.com/feed/update/{data_urn}/"
                driver.get(post_url)
                time.sleep(random.uniform(3, 5))  # Wait for the page to load

                # Extract post content
                post_content = driver.find_element(By.CLASS_NAME, "feed-shared-update-v2__description").text.strip()
                post_content = clean_text(post_content)

                # Extract author
                author = driver.find_element(By.CLASS_NAME, "update-components-actor__title").text.strip()
                author = author.split('\n')[0]
                author = clean_text(author)
                

                # Extract time posted
                time_posted = driver.find_element(By.CLASS_NAME, "update-components-actor__sub-description").text.strip()
                time_posted = clean_text(time_posted)
                time_posted = time_posted.split(' ')[0]

                # Click "Comment" button to load comments
                comment_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Comment"]')
                driver.execute_script("arguments[0].click();", comment_button)
                time.sleep(random.uniform(2, 4))  # Wait for comments to load

                # Load all comments and replies
                load_all_comments(driver)

                # Extract comments
                comment_section = driver.find_element(By.CLASS_NAME, "comments-comments-list")
                comments = parse_comments(comment_section)

                # Append post data
                all_activity_data.append({
                    "Post URL": post_url,
                    "Author": author,
                    "Time Posted": time_posted,
                    "Content": post_content,
                    "Comments": comments
                })

            except Exception as e:
                pretty_display(f"Error processing post {data_urn}: {e}", 'ERROR')

        return json.dumps(all_activity_data, indent=4)

    except Exception as e:
        pretty_display(f"Error fetching post details: {e}", 'ERROR')
        return None


def save_json_to_file(json_data, file_path="assets/linkedin_activity.json"):
    try:
        with open(file_path, "w") as json_file:
            json_file.write(json_data)
        pretty_display(f"LinkedIn activity data saved successfully to {file_path}.", 'SUCCESS')
    except Exception as e:
        pretty_display(f"Error saving JSON data: {e}", 'ERROR')


if __name__ == "__main__":
    username = "your_username"  # Replace with your credentials
    password = "your_password"  # Replace with your credentials

    driver = login_to_linkedin(username, password, headless=True)

    if driver:
        get_and_save_all_activity_data(driver)
        json_data = fetch_post_details_from_file(driver)
        if json_data:
            save_json_to_file(json_data)

        # Close the browser
        driver.quit()
    else:
        pretty_display("Failed to log in, no further actions.", 'ERROR') 

