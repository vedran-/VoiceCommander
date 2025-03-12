import importlib
import subprocess
import sys

def check_and_install_libraries():
    required_libraries = ['pyaudio', 'pyperclip', 'vosk', 'groq', 'googlesearch', 'selenium', 'keyboard', 'pynput', 'pygame']
    
    for library in required_libraries:
        try:
            importlib.import_module(library)
            #print(f"{library} is installed.")
        except ImportError as e:
            print(f"{library} is not installed. Installing... {e}\n")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", library])
                print(f"{library} has been successfully installed.")
            except subprocess.CalledProcessError:
                print(f"Failed to install {library}. Please install it manually.")
                sys.exit(1)