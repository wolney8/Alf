import openai  # Corrected import
import os
import pyaudio
import speech_recognition as sr
import time
from gtts import gTTS
from playsound import playsound
from dotenv import load_dotenv
from pathlib import Path
import config  # Import the config module
import random
import glob
from pydub import AudioSegment
from pydub.playback import play




# No need to load .env for API key since we're using config.py here
# load_dotenv()

# Set the OpenAI API key from config.py
openai.api_key = config.OPENAI_API_KEY


# Create an OpenAI API client
if openai.api_key is None:
    raise ValueError("OpenAI API key not found. Make sure your config.py file contains OPENAI_API_KEY.")
openai.api_key = openai.api_key  # Correct way to set the API key

# Settings and keys
model_engine = "gpt-4-0125-preview"  
language = 'en'

def recognize_speech():
    # obtain audio from the microphone
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Say something!")  # This can be removed if the audio cue is sufficient
        # Immediately start listening
        audio = r.listen(source)

    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        # convert the audio to text
        print("Google Speech Recognition thinks you said: " + r.recognize_google(audio))
        speech = r.recognize_google(audio)
        print("This is what we think was said: " + speech)
        # start_audio_response = AudioSegment.from_mp3("wake.mp3")
        # play(start_audio_response)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))

    # Play a randomly selected holding message
    play_holding_message()

    return speech

def play_holding_message():
    # Find all holding message files in the subdirectory
    holding_messages = glob.glob('holding_messages/holding_*.mp3')
    # Check if there are any messages found
    if not holding_messages:
        print("No holding message found. Consider generating holding messages first.")
        return  # Exit the function early if no messages are found
    silence = AudioSegment.silent(duration=500) 
    selected_message = random.choice(holding_messages)
    holding_audio_response = silence + AudioSegment.from_file(selected_message)
    play(holding_audio_response)


def chatgpt_response(prompt):
    # Define a standard context or instruction for the model
    standard_context = "You are a helpful smart speaker called Alf. Please keep your responses short and sweet."
    
    # send the converted audio text to chatgpt
    response = openai.ChatCompletion.create(
        model=model_engine,
        messages=[{"role": "system", "content": standard_context},
                  {"role": "user", "content": prompt}],
        max_tokens=150,  # You might also reduce max_tokens to encourage shorter responses
        n=1,
        temperature=0.5,  # Adjusting temperature can also affect the variability of responses
    )
    return response


def generate_audio_file(message):
    speech_file_path = Path(__file__).parent / "response.mp3"
    tts = gTTS(text=message, lang='en')
    tts.save(str(speech_file_path))

 
def play_audio_file():
    # play the audio file
    playsound("response.mp3")

def main():
    # run the program
    prompt = recognize_speech()
    print(f"Prompt:  {prompt}")
    responses = chatgpt_response(prompt)
    message = responses.choices[0].message.content
    print(message)
    generate_audio_file(message)
    play_audio_file()

if __name__ == "__main__":
    main()