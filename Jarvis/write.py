import pyttsx3
import datetime
import webbrowser
import os
import wikipedia
import requests

engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if hour < 12:
        speak("Good Morning!")
    elif hour < 18:
        speak("Good Afternoon!")
    else:
        speak("Good Evening!")
    speak("I am Jarvis. Please tell me how may I help you.")

def get_weather(city):
    api_key = "17ef3e0f83e747a8e8e5343014c267f0"  # <-- Get from https://openweathermap.org
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    res = requests.get(url).json()
    if res["cod"] == 200:
        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        speak(f"The temperature in {city} is {temp}°C with {desc}.")
    else:
        speak("City not found in query or weather service unavailable.")

def open_app(path, name=""):
    try:
        os.system(path)
        speak(f"Opening {name in query or 'app'}...")
    except:
        speak("Sorry, couldn't open the application.")

if __name__ == "__main__":
    wishMe()
    while True:
        query = input("✏️ Enter Command: ").lower()

        if query == "exit":
            speak("Goodbye!")
            break

        elif "wikipedia" in query:
            speak("Searching Wikipedia...")
            query = query.replace("wikipedia", "")
            try:
                result = wikipedia.summary(query, sentences=2)
                print(result)
                speak("According to Wikipedia,")
                speak(result)
            except:
                speak("Sorry, I couldn't fetch the Wikipedia result.")

        elif "open youtube" in query:
            webbrowser.open("https://www.youtube.com")
            speak("Opening YouTube.")

        elif "open google" in query:
            webbrowser.open("https://www.google.com")
            speak("Opening Google.")

        elif "open vs code" in query:
            open_app("C:\\path\\to\\VSCode.exe", "Visual Studio Code")

        elif "play music" in query:
            music_dir = "C:\\Users\\YourUser\\Music"
            songs = os.listdir(music_dir)
            if songs:
                os.system(os.path.join(music_dir, songs[0]))
                speak("Playing music.")
            else:
                speak("No music files found.")

        elif "the time" in query:
            time = datetime.datetime.now().strftime("%H:%M:%S")
            print(time)
            speak(f"The time is {time}")

        elif "weather" in query:
            speak("Which city?")
            city = input("Enter City Name: ")
            get_weather(city)

        elif "shutdown" in query:
            speak("Shutting down the system.")
            os.system("shutdown /s /t 5")
            
        elif "open chatgpt" in query:
            webbrowser.open("https://chatgpt.com")
            speak("Opening ChatGPT")

        elif "restart" in query:
            speak("Restarting the system.")
            os.system("shutdown /r /t 5")

        elif "lock" in query:
            speak("Locking the system.")
            os.system("rundll32.exe user32.dll,LockWorkStation")

        elif "start flappy bird" in query or "launch flappy bird" in query:
            os.system("python Games/flappy_bird.py")
        
        elif "start letter guessing game" in query or "launch letter guessing game " in query:
            os.system("python Games/letter_guess.py")
            
        elif "start ludo" in query or "launch ludo" in query:
            os.system("python Games/Ludo.py")
            
        elif "start number guessing game" in query or "launch number guessing game" in query:
            os.system("python Games/number_guess.py")
            
        elif "start rock paper scissors" in query or "launch rock paper scissors" in query:
            os.system("python Games/rps.py")
            
        elif "start snake and ladders" in query or "launch snake and ladders" in query:
            os.system("python Games/snake_and_ladders.py")
            
        elif "start word guessing game" in query or "launch word guessing game" in query:
            os.system("python Games/word_guess.py")
        
        else:
            speak("Sorry, I didn't understand that query.")
