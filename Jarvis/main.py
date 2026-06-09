import speech_recognition as sr
import webbrowser
import pyttsx3
import os
import time

engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def processCommand(command):
    command = command.lower()
    if "open google" in command:
        webbrowser.open("https://google.com")
        speak("Opening Google")
        
    elif "open facebook" in command:
        webbrowser.open("https://facebook.com")
        speak("Opening Facebook")
        
    elif "open youtube" in command:
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")
        
    elif "open linkedin" in command:
        webbrowser.open("https://linkedin.com")
        speak("Opening LinkedIn")
        
    elif "open gamer" in command:
        webbrowser.open("https://www.youtube.com/@AnshuBisht")
        speak("Opening Anshu Bisht's channel")
        
    elif "open mrbeast" in command:
        webbrowser.open("https://www.youtube.com/@MrBeast")
        speak("Opening MrBeast channel")
        
    elif "open bulky star" in command:
        webbrowser.open("https://www.youtube.com/@BulkyStar")
        speak("Opening Bulky Star channel")
        
    elif "open code with harry" in command:
        webbrowser.open("https://www.youtube.com/@CodeWithHarry")
        speak("Opening Code With Harry channel")
    
    elif command.startswith("play"):
        # You can replace this part with your actual musicLibrary logic or local mp3 player
        song = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else ""
        # example: open youtube search with song name
        webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
        speak(f"Playing {song} on YouTube")
    elif 'open file manager' in command:
        try:
            os.startfile("3D Objects")
            speak("Opening file manager")
        except Exception as e:
            speak("Sorry, could not open file manager")
            print(e)
    elif "start flappy bird" in command:
        os.system("python Games/flappy_bird.py")

    elif "start letter guessing game":
        os.system("python Games/letter_guess.py")

    elif "start ludo" in command:
        os.system("python Games/Ludo.py")

    elif "start number guessing game":
        os.system("python Games/number_guess.py")

    elif "start rock paper scissors":
        os.system("python Games/rps.py")
        
    elif "start snake and ladders":
        os.system("python Games/snake_and_ladders.py")

    elif "start word guessing game" :
        os.system("python Games/word_guess.py")
    else:
        speak("Sorry, I did not understand the command")

def listen_for_wake_word(recognizer, mic):
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening for wake word 'Jarvis'...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        word = recognizer.recognize_google(audio).lower()
        print(f"Heard: {word}")
        return word == "jarvis"
    except sr.WaitTimeoutError:
        print("Listening timed out waiting for phrase")
        return False
    except sr.UnknownValueError:
        print("Could not understand audio")
        return False
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return False

def listen_for_command(recognizer, mic):
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening for command...")
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=7)
        command = recognizer.recognize_google(audio)
        print(f"Command: {command}")
        return command
    except sr.WaitTimeoutError:
        speak("I didn't hear anything, please try again")
        return ""
    except sr.UnknownValueError:
        speak("Sorry, I could not understand what you said")
        return ""
    except sr.RequestError as e:
        speak("Sorry, my speech service is down")
        print(f"Request Error: {e}")
        return ""

if __name__ == "__main__":
    speak("Initializing Jarvis...") 
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    while True:
        if listen_for_wake_word(recognizer, mic):
            speak("Yes sir, how can I help?")
            command = listen_for_command(recognizer, mic)
            if command:
                processCommand(command)
            else:
                speak("Please say the command again.")
        else:
            time.sleep(1)  # small pause before next listen cycle to avoid CPU hogging
