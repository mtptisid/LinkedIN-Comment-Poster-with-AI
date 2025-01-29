import re 
import json
from groq import Groq  # Import the Groq SDK
from datetime import datetime, timedelta

# Initialize the Groq client
client = Groq(api_key="YOUR_API_KEY")  # Replace with your actual Groq API key

# Path to the JSON file containing LinkedIn activity data
JSON_FILE_PATH = "assets/linkedin_activity.json"

# Path to save the responses
RESPONSES_FILE_PATH = "assets/linkedin_responses.json"

# Post author name (to filter out comments from the author)
POST_AUTHOR = "Siddharamayya Mathapati"  #Change to your Linked in Name

# System prompt to guide the AI's behavior
system_prompt = """
You are a helpful assistant that generates professional and engaging responses to LinkedIn comments. 
The user will provide a LinkedIn post and a comment on that post. You will generate a thoughtful and relevant reply to the comment, considering the context of the post.

You are responding as Siddharamayya Mathapati, the author of the post. Ensure that all responses are written from Siddharamayya's perspective.

Guidelines:
1. Keep the response concise, professional, and relevant to the comment.
2. Use a friendly and appreciative tone.
3. If the comment is congratulatory, express gratitude and briefly mention the significance of the achievement.
4. Avoid overly verbose or generic responses.
5. Always end the response with: "+-------------------------------------+\n| This is an AI-generated response.   |\n+-------------------------------------+"

Examples:

Comment: Congrats Siddharamayya!
Response: Thank you so much for your kind words! I'm thrilled to share this achievement and excited to apply the new skills I've gained. Let's connect and explore opportunities to collaborate!
+-------------------------------------+
| This is an AI-generated response.   |
+-------------------------------------+

Comment: Great post!
Response: Thank you for your feedback! I'm glad you found the post insightful. Let me know if you'd like to discuss this further.
+-------------------------------------+
| This is an AI-generated response.  |
+-------------------------------------+

Comment: Interesting insights!
Response: I appreciate your comment! If you have any questions or would like to dive deeper into the topic, feel free to reach out.
+-------------------------------------+
| This is an AI-generated response.   |
+-------------------------------------+
"""

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

import os
import json

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
                pretty_display(f"File not found: {file_name} in either {file_path} or the current directory.", 'ERROR')
                return None

        # Load the JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            #data = json.load(file)
            return json.load(file)

    except json.JSONDecodeError as e:
        pretty_display(f"Invalid JSON format in file: {file_path}. Error: {e}", 'ERROR')
        return None
    except Exception as e:
        pretty_display(f"Error loading JSON file: {e}", 'ERROR')
        return None


def save_responses(responses, file_path):
    """Save the responses to a JSON file."""
    try:
        if not responses:  # Check if responses are empty
            # Overwrite the file with an empty JSON object
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump({}, file, indent=4)
            pretty_display(f"No responses. Cleared the file: {file_path}")
        else:
            # Save responses to the file
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(responses, file, indent=4)
            pretty_display(f"Responses saved to {file_path}")
    except Exception as e:
        pretty_display(f"Error saving responses: {e}", 'ERROR')


def is_recent(time_string):
    """Check if a comment was made within the last hour."""
    try:
        # Parse the time string (e.g., "20m", "4d", "1w")
        if "m" in time_string:
            minutes = int(time_string.replace("m", ""))
            return minutes <= 60  # Within the last hour
        elif "h" in time_string:
            hours = int(time_string.replace("h", ""))
            return hours == 0  # Less than an hour
        elif "d" in time_string:
            days = int(time_string.replace("d", ""))
            return False  # Older than a day
        elif "w" in time_string:
            weeks = int(time_string.replace("w", ""))
            return False  # Older than a week
        else:
            return False  # Unknown format
    except Exception as e:
        pretty_display(f"Error parsing time string '{time_string}': {e}", 'ERROR')
        return False

def filter_recent_comments(data):
    """Filter comments and replies that are recent and not from the post author."""
    recent_comments = []
    for post in data:
        # Clean the post content
        post_content = clean_text(post["Content"])

        for comment in post["Comments"]:
            # Clean the comment text
            comment_text = clean_text(comment["Comment Text"])

            # Check top-level comments
            if is_recent(comment["Time Commented"]) and comment["Commenter Name"] != POST_AUTHOR:
                recent_comments.append({
                    "Post URL": post["Post URL"],
                    "Post Content": post_content,  # Include cleaned post content
                    "Comment Text": comment_text,  # Include cleaned comment text
                    "Commenter Name": comment["Commenter Name"],
                    "Time Commented": comment["Time Commented"]
                })

            # Check replies to the comment
            for reply in comment.get("Replies", []):
                # Clean the reply text
                reply_text = clean_text(reply["Comment Text"])

                if is_recent(reply["Time Commented"]) and reply["Commenter Name"] != POST_AUTHOR:
                    recent_comments.append({
                        "Post URL": post["Post URL"],
                        "Post Content": post_content,  # Include cleaned post content
                        "Comment Text": reply_text,  # Include cleaned reply text
                        "Commenter Name": reply["Commenter Name"],
                        "Time Commented": reply["Time Commented"]
                    })
    return recent_comments

def generate_response(post_content, comment_text, commententor_name):
    """Generate a response using the Groq API."""
    try:
        # Define the user prompt (the LinkedIn post and comment)
        user_prompt = f"""
        LinkedIn Post:
        {post_content}

        Comment:
        {comment_text}

        Commentor:
        {commententor_name}

        You are responding as Siddharamayya Mathapati, the author of the post. Ensure that all responses are written from Siddharamayya's perspective and you are responding to Commentor,

        Guidelines:
        1. Keep the response concise, professional, and relevant to the comment.
        2. Use a friendly and appreciative tone.
        3. Avoid entioning commentor name in response.
        4. If the comment is congratulatory, express gratitude and briefly mention the significance of the achievement.
        5. Avoid overly verbose or generic responses.
        6. Always end the response with: "+-------------------------------------+\n| This is an AI-generated response.   |\n+-------------------------------------+"
        7. No PREAMBLE and NO PLACEHOLDER
        8. Acknowledges the commenter's input.
        """

        # Prepare the messages for the API request
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Send the request to the Groq API
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Replace with the correct Groq model name
            messages=messages,
            max_tokens=150,  # Increase token limit for more detailed responses
            temperature=0.7,  # Control randomness (0 = deterministic, 1 = random)
        )

        # Extract and return the generated response
        return response.choices[0].message.content

    except Exception as e:
        # Handle any errors that occur during the API request
        pretty_display(f"Error generating response: {e}", 'ERROR')
        return None

def process_comments(data):
    """Process comments, generate responses, and save them."""
    recent_comments = filter_recent_comments(data)
    if not recent_comments:
        pretty_display("No recent comments found.", 'SUCCESS')
        return

    responses = []
    for comment in recent_comments:
        pretty_display(f"New Comment from {comment['Commenter Name']} ({comment['Time Commented']}):" , 'WARNING')
        print(f"Comment: {comment['Comment Text']}")

        # Generate a response using Groq
        response = generate_response(comment["Post Content"], comment["Comment Text"], comment["Commenter Name"])
        if response:
            pretty_display("AI RESPONSE", 'SUCCESS')
            print(response)
              # Separator for readability

            # Save the response along with the post URL and comment details
            responses.append({
                "Post URL": comment["Post URL"],
                "Post Content": comment["Post Content"],  # Include cleaned post content
                "Comment Text": comment["Comment Text"],  # Include cleaned comment text
                "Commenter Name": comment["Commenter Name"],
                "Time Commented": comment["Time Commented"],
                "AI Response": response
            })

    # Save all responses to a JSON file
    save_responses(responses, RESPONSES_FILE_PATH)

def main():
    # Load the JSON data
    data = load_json_data(JSON_FILE_PATH)
    if not data:
        return

    # Process the comments and generate responses
    process_comments(data)

if __name__ == "__main__":
    main()