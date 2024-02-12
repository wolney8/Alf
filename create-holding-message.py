import json
from gtts import gTTS
import os

# Check if the subdirectory exists, create it if not
if not os.path.exists('holding_messages'):
    os.makedirs('holding_messages')

# Load phrases from JSON
with open('holding_phrases.json', 'r') as json_file:
    phrases = json.load(json_file)["phrases"]

# Generate a holding message for each phrase using gTTS
for index, phrase in enumerate(phrases):
    tts = gTTS(text=phrase, lang='en')
    file_name = f"holding_messages/holding_{index}.mp3"
    tts.save(file_name)
    print(f"Generated {file_name}")
