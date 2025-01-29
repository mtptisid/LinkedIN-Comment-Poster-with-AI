import time
import schedule
import subprocess

def pretty_display(message, message_type):
    """
    Print a message with a colored border based on the message type.

    Parameters:
    - message (str): The message to display.
    - message_type (str): The type of message ('ERROR', 'WARNING', 'SUCCESS', 'INFO').
    """
    # Validate input types
    if not isinstance(message, str):
        raise ValueError("Message must be a string.")
    if message_type not in ['ERROR', 'WARNING', 'SUCCESS', 'INFO']:
        raise ValueError("Invalid message type. Choose from 'ERROR', 'WARNING', 'SUCCESS', 'INFO'.")

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
    border_length = len(message) + 4  # 2 spaces for padding and 2 for the border
    border = '+' + '-' * (border_length - 2) + '+'

    # Print the formatted message
    print(color + border)
    print(color + '| ' + message + ' |')
    print(color + border + colors['RESET'])

def run_script(script_name):
    """Run a Python script using subprocess."""
    try:
        pretty_display(f"Running {script_name}...", 'INFO')
        subprocess.run(["python", script_name], check=True)
        pretty_display(f"{script_name} completed successfully!", 'WARNING')
    except subprocess.CalledProcessError as e:
        pretty_display(f"Error running {script_name}: {e}" , 'ERROR')

def main():
    """Main function to run all scripts in sequence."""
    try:
        pretty_display("Starting the LinkedIn comment automation workflow...", 'INFO')

        # Step 1: Fetch comments and save data
        run_script("fetch_comments.py")

        # Step 2: Generate AI responses and save them
        run_script("generate_responses.py")

        # Step 3: Post the AI responses to LinkedIn
        run_script("post_responses.py")

        pretty_display("Workflow completed successfully!", 'SUCCESS')
    except Exception as e:
        pretty_display(f"Error in main workflow: {e}", 'ERROR')

# Schedule the main function to run every 1 hour
schedule.every(2).minutes.do(main)

# Keep the script running
if __name__ == "__main__":
    pretty_display("Scheduler started. Waiting for the next run...", 'INFO')
    while True:
        schedule.run_pending()
        time.sleep(1)  # Sleep for 1 second to avoid high CPU usage