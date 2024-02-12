import os
import openai  # Corrected import
import pyaudio
import speech_recognition as sr
from gtts import gTTS
from dotenv import load_dotenv
# import apa102
import threading
from gpiozero import LED
try:
    import queue as Queue
except ImportError:
    import Queue as Queue
from alexa_led_pattern import AlexaLedPattern
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
import config  # Import the config module
import random
import glob


# Set the working directory for Pi if you want to run this code via rc.local script so that it is automatically running on Pi startup. Remove this line if you have installed this project in a different directory.
os.chdir('/home/pi/alf')
 
# No need to load .env for API key since we're using config.py here
# load_dotenv()

# Set the OpenAI API key from config.py
openai.api_key = config.OPENAI_API_KEY

# OpenAI API
if openai.api_key is None:
    raise ValueError("OpenAI API key not found. Make sure your config.py file contains OPENAI_API_KEY.")
openai.api_key = openai.api_key  # Correct way to set the API key

 
# load pixels Class
class Pixels:
    PIXELS_N = 12
 
    def __init__(self, pattern=AlexaLedPattern):
        self.pattern = pattern(show=self.show)
        self.dev = apa102.APA102(num_led=self.PIXELS_N)
        self.power = LED(5)
        self.power.on()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        self.last_direction = None
 
    def wakeup(self, direction=0):
        self.last_direction = direction
        def f():
            self.pattern.wakeup(direction)
 
        self.put(f)
 
    def listen(self):
        if self.last_direction:
            def f():
                self.pattern.wakeup(self.last_direction)
            self.put(f)
        else:
            self.put(self.pattern.listen)
 
    def think(self):
        self.put(self.pattern.think)
 
    def speak(self):
        self.put(self.pattern.speak)
 
    def off(self):
        self.put(self.pattern.off)
 
    def put(self, func):
        self.pattern.stop = True
        self.queue.put(func)
 
    def _run(self):
        while True:
            func = self.queue.get()
            self.pattern.stop = False
            func()
 
    def show(self, data):
        for i in range(self.PIXELS_N):
            self.dev.set_pixel(i, int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]))
 
        self.dev.show()
 
pixels = Pixels()
 
 
# Settings and keys
model_engine = "gpt-4-0125-preview"  
language = 'en'
 
def recognize_speech():
    # obtain audio from the microphone
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            pixels.off()
            print("Listening...")
            audio_stream = r.listen(source)
            print("Waiting for wake word...")
            # recognize speech using Google Speech Recognition
            try:
                # convert the audio to text
                print("gTTS thinks you said: " + r.recognize_google(audio_stream))
                speech = r.recognize_google(audio_stream)
                print("Recognized Speech:", speech)  # Print the recognized speech for debugging
                words = speech.lower().split()  # Split the speech into words
                if "alf" not in words:
                    print("Wake word not detected in the speech")
                    return False
                else:
                    # Wake up the display
                    pixels.wakeup()
                    print("Found wake word!")
                    # Add recognition of activation messsage to improve the user experience.
                    try:
                         # Add 1 second silence due to initial buffering how pydub handles audio in memory
                        silence = AudioSegment.silent(duration=1000) 
                        start_audio_response = silence + AudioSegment.from_mp3("wake.mp3")
                        play(start_audio_response)
                    except:
                        pass
                    return True
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))
        except KeyboardInterrupt:
            print("Interrupted by User Keyboard")
            pass

 
def speech():
    # obtain audio from the microphone
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Waiting for user to speak...")
        while True:
            try:
                r.adjust_for_ambient_noise(source)
                audio_stream = r.listen(source)
                # recognize speech using Google Speech Recognition
                try:
                    # convert the audio to text
                    print("gTTS thinks you said: " + r.recognize_google(audio_stream))
                    speech = r.recognize_google(audio_stream)
                    # wake up thinking LEDs
                    pixels.think()
                    return speech
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    pixels.off()
                    print("Waiting for user to speak...")
                    continue
                except sr.RequestError as e:
                    print("Could not request results from Google Speech Recognition service; {0}".format(e))
                    pixels.off()
                    print("Waiting for user to speak...")
                    continue
            except KeyboardInterrupt:
                print("Interrupted by User Keyboard")
                break

def play_holding_message():
    holding_messages = glob.glob('holding_messages/holding_*.mp3')
    if not holding_messages:
        print("No holding message found in 'holding_messages/'.")
        return  # Optionally, play a default message if no messages are found
    silence = AudioSegment.silent(duration=1000) 
    selected_message = random.choice(holding_messages)
    holding_audio_response = silence + AudioSegment.from_file(selected_message)
    play(holding_audio_response)
  
 
def chatgpt_response(prompt):
    # Define a standard context or instruction for the model
    standard_context = "You are a helpful smart speaker called Alf. Please keep your responses short and sweet."
    
    # Add a holding messsage like the one below to deal with current TTS delays until such time that TTS can be streamed.
    try:
        holding_audio_response = play_holding_message()
    except:
        pass
    # send the converted audio text to chatgpt
    response = response = openai.ChatCompletion.create(
        model=model_engine,
        messages=[{"role": "system", "content": standard_context},
                  {"role": "user", "content": prompt}],
        max_tokens=150,
        n=1,
        temperature=0.5,
    )
    return response
 
def generate_audio_file(message):
    speech_file_path = Path(__file__).parent / "response.mp3"
    tts = gTTS(text=message, lang='en')
    tts.save(str(speech_file_path))
 
def play_audio_file():
    # play the audio file and wake speaking LEDs
    pixels.speak()
    # Add 1 second silence due to initial buffering how pydub handles audio in memory
    silence = AudioSegment.silent(duration=1000) 
    audio_response = silence + AudioSegment.from_mp3("response.mp3")
    play(audio_response)

def main():
    # run the program
    # Indicate to the user that the device is ready
    # Add 1 second silence due to initial buffering how pydub handles audio in memory
    silence = AudioSegment.silent(duration=1000) 
    pixels.wakeup()
    device_on = silence + AudioSegment.from_mp3("on.mp3")
    play(device_on)
    while True:
        if recognize_speech():
            prompt = speech()
            print(f"This is the prompt being sent to OpenAI: {prompt}")
            responses = chatgpt_response(prompt)
            message = responses.choices[0].message.content
            print(message)
            generate_audio_file(message)
            play_audio_file()
            pixels.off()
        else:
            print("Speech was not recognised")
            pixels.off()
 
if __name__ == "__main__":
    main()
