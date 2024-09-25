import os
from datetime import datetime
import random
import string

def save_audio_file(text, user_id):
    """
    Simulates saving an audio file generated from text.
    In a real application, this would use a text-to-speech service.
    
    Args:
    text (str): The text to be converted to audio
    user_id (int): The ID of the user generating the audio
    
    Returns:
    str: The filename of the saved audio file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audio_{user_id}_{timestamp}.mp3"
    file_path = os.path.join('static', 'audios', filename)
    
    # For now, we'll just create a text file with the content
    with open(file_path, 'w') as f:
        f.write(f"This is a placeholder for audio generated from: {text}")
    
    return filename

def generate_unique_filename(extension):
    """
    Generates a unique filename with the given extension.
    
    Args:
    extension (str): The file extension (e.g., '.mp3', '.wav')
    
    Returns:
    str: A unique filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"file_{timestamp}_{random_string}{extension}"

def get_file_extension(filename):
    """
    Extracts the file extension from a filename.
    
    Args:
    filename (str): The name of the file
    
    Returns:
    str: The file extension (including the dot)
    """
    return os.path.splitext(filename)[1]

def is_allowed_file(filename, allowed_extensions):
    """
    Checks if a file has an allowed extension.
    
    Args:
    filename (str): The name of the file to check
    allowed_extensions (set): A set of allowed file extensions
    
    Returns:
    bool: True if the file has an allowed extension, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def create_directory_if_not_exists(directory):
    """
    Creates a directory if it doesn't already exist.
    
    Args:
    directory (str): The path of the directory to create
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

# You can add more utility functions here as needed for your application
