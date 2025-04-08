import io, sys, os
import wave
import webbrowser
import pyttsx3
from datetime import datetime
from groq import Groq
from googlesearch import search
from . import config
import threading

class GroqWhisperService:
    SYSTEM_PROMPT = (
        "### Instructions:\n"
        "You are checking a streamed user input, checking if we got the whole input, and judging if user "
        "wants us to run a command. You can also write Python scripts, and run them.\n"
        "The input will sometimes be incomplete, and you should respond with 'INCOMPLETE_COMMAND' - that means that continuation of that command will come in next message(s).\n"
        "Similarly, when you're not sure, check previous messages for context.\n\n"
        "Your output should be a single command or a comment.\n"
        "\n### Available commands:\n"
        " - INCOMPLETE_COMMAND: If we're not 100% sure that the user is finished with its input\n"
        " - DICTATE: Sometimes the user will start with the word 'dictate', and you should write down what it said in a nicer way\n"
        " - RESET: Resets the chat history\n"
        " - MUTE: Mutes AI chat\n"
        " - UNMUTE: Unmutes AI chat\n"
        " - STOP: Stops transcription and listening\n"
        " - RESUME: Resumes transcription and listening\n"
        " - PASTE <on | off>: enabled / disables automatic pasting of text copied to clipboard"
        " - SWITCH_LANGUAGE <en|sl|hr|...>\n"
        " - SEARCH '<query>': searches the web\n"
        " - CALENDAR_ADD '<timestamp>' ```<description>```\n"
        " - MEMO_ADD ```<description>```\n"
        " - WRITE_EMAIL [to: <person>] [subject: '<subject>'] [content: ```<content>```]\n"
        " - WRITE_FILE '<filename>' [```<content>```]: You always have to write whole content of the file, you can't update just a part of it.\n"
        " - RUN_SCRIPT '<filename>'\n"
        " - SHOOT <person>\n"
        " - RESPOND_TO_USER <some comment>: if you need to respond to the user, and no other command fits in the profile\n"
    )


    def __init__(self):
        self._api_key = config.GROQ_API_KEY
        self._model = config.LLM_MODEL
        self._transcription_model = config.TRANSCRIPTION_MODEL
        self._unfamiliar_words = config.UNFAMILIAR_WORDS
        self.initialize_client()
        self._language = "en"  # Private attribute
        self.mute_llm = True
        self.automatic_paste = True
        self.InitializeChat()        
        os.makedirs(config.CHAT_HISTORY_SAVE_FOLDER, exist_ok=True)
        os.makedirs(config.LLM_SANDBOX_WORKING_FOLDER, exist_ok=True)

        # Initialize TTS
        self._initialize_tts()
        
        # Signal callbacks for UI interaction
        self.on_command_stop = None
        self.on_command_resume = None
        self.on_command_reset = None

    def initialize_client(self):
        """Initialize the Groq client with the current API key"""
        try:
            self.client = Groq(api_key=self._api_key)
            return True
        except Exception as e:
            print(f"Error initializing Groq client: {e}")
            return False

    @property
    def api_key(self):
        """Get the current API key"""
        return self._api_key
        
    @api_key.setter
    def api_key(self, value):
        """Set the API key and reinitialize the client"""
        if value != self._api_key:
            self._api_key = value
            self.initialize_client()
            print(f"API key updated and client reinitialized")

    @property
    def model(self):
        """Get the current LLM model"""
        return self._model
        
    @model.setter
    def model(self, value):
        """Set the LLM model"""
        if value != self._model:
            self._model = value
            print(f"LLM model updated to: {value}")

    @property
    def transcription_model(self):
        """Get the current transcription model"""
        return self._transcription_model
        
    @transcription_model.setter
    def transcription_model(self, value):
        """Set the transcription model"""
        if value != self._transcription_model:
            self._transcription_model = value
            print(f"Transcription model updated to: {value}")
            
    @property
    def unfamiliar_words(self):
        """Get the current unfamiliar words"""
        return self._unfamiliar_words
        
    @unfamiliar_words.setter
    def unfamiliar_words(self, value):
        """Set the unfamiliar words"""
        if value != self._unfamiliar_words:
            self._unfamiliar_words = value
            print(f"Unfamiliar words updated")

    @property
    def language(self):
        """Get the current language code"""
        return self._language
        
    @language.setter
    def language(self, value):
        """Set the language code"""
        self._language = value

    def _initialize_tts(self):
        """Initialize the text-to-speech engine with error handling"""
        try:
            self.tts = pyttsx3.init()
            self.tts.setProperty('volume', 0.8)
            self.tts.setProperty('rate', 150)
            
            voices = self.tts.getProperty('voices')
            if len(voices) > 0:
                print(f"TTS initialized with {len(voices)} voices")
                for voice in voices:
                    print(f"Voice: {voice.name}")
                
                # Set voice to the second voice if available
                if len(voices) > 1:
                    self.tts.setProperty('voice', voices[1].id)
            else:
                print("No TTS voices found")
                
            # Add lock for TTS operations to prevent concurrent access
            self.tts_lock = threading.Lock()
            return True
        except Exception as e:
            print(f"Error initializing TTS: {e}")
            self.tts = None
            self.tts_lock = None
            return False

    def InitializeChat(self):
        print(f"Initializing chat... LLM: \033[33m{self._model}\033[0m, transcription by: \033[33m{self._transcription_model}\033[0m")
        self.messages = [
            {
                "role": "system",
                "content": self.get_system_prompt()
            }
        ]
        self.chat_timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    def TranscribeAudio(self, audio_data):
        if audio_data is None:
            print("No audio data to transcribe")
            return None
            
        # Verify minimum audio length (prevent "too short" API errors)
        if len(audio_data) < 320:  # Less than 20ms at 16kHz, 16-bit, mono
            print(f"Audio too short to transcribe: {len(audio_data)} bytes")
            return None
            
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(16000)  # Sample rate of 16kHz
            wav_file.writeframes(audio_data)
        wav_data = wav_buffer.getvalue()

        try:
            transcription = self.client.audio.transcriptions.create(
                file=("instructions.wav", wav_data),
                model=self._transcription_model,
                prompt=self._unfamiliar_words,  # Optional
                response_format="verbose_json",  # Optional
                language=self.language,  # Optional
                temperature=0.4  # Optional
            )
        except Exception as e:
            print(f"Transcription API error: {e}")
            return None

        # Extract text from segments with acceptable no_speech_prob
        text = ""
        for segment in transcription.segments:
            if segment['no_speech_prob'] <= config.MAX_TRANSCRIPTION_NO_SPEECH_PROBABILITY:
                text += segment['text']
        text = str(text).strip()

        # Check if text is empty
        if text == "":
            return None

        if text.startswith('Thank you') or text.startswith('Subtitles by'):
            return None

        return text

    def get_system_prompt(self):
        additional_info = (
                f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"System: {sys.platform}\n"
                f"System: {sys.getwindowsversion()}\n"
                f"Current user: {os.getlogin()}\n"
                f"Current directory: {os.getcwd()}\n"
                )
        
        #print(additional_info)
        return self.SYSTEM_PROMPT + additional_info

    def AddUserMessage(self, message):
        """
        Add a user message to the conversation
        
        Args:
            message: The message from the user
        """
        if not message:
            return
            
        # Skip if muted
        if self.mute_llm:
            return
            
        # Add user message
        self.messages.append({
            "role": "user",
            "content": message
        })
        
        # Get response from Groq API
        response = self._call_groq_api(message)
        
        # Add assistant response
        self.messages.append({
            "role": "assistant",
            "content": response
        })

        # Write whole messages to a file using UTF-8 encoding
        try:
            filename = os.path.join(config.CHAT_HISTORY_SAVE_FOLDER, f"chat_{self.chat_timestamp}.json")
            with open(filename, "w", encoding="utf-8") as file:
                file.write(str(self.messages))
        except Exception as e:
            print(f"Error writing chat history: {e}")

        try:
            self.ParseResponse(response)
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Response: {response}")

        #print(f'\n\n------------MESSAGES: {self.messages}')

    def WebSearch(self, query: str):
        print(f"Searching the web for: \033[92m{query}\033[0m")
        results = search(query, num_results=3)    
        for i, result in enumerate(results):
            print(f"{i+1}. {result}")
            if i == 0:
                self.ShowWebPage(result)

    def ShowWebPage(self, url: str):
        print(f"Opening web page: \033[92m{url}\033[0m")
        webbrowser.open(url)

    def run_script_independently(self, script_name):
        import subprocess
        try:
            if sys.platform == "win32":
                # On Windows, open a new console window and run the script
                # The 'start' command opens a new console window, /B runs without creating a new window
                # 'python' runs the script using the current Python interpreter
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Create the process but don't wait
                process = subprocess.Popen(
                    [sys.executable, script_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                # Return a message that the script was launched successfully
                return "Script launched in a new window.", ""
            else:
                # On Unix-like systems, run the script in the background
                process = subprocess.Popen(
                    [sys.executable, script_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Set up a thread to handle the output
                def handle_output():
                    stdout, stderr = process.communicate()
                    if stdout:
                        print(f"Script output:\n{stdout.decode()}")
                    if stderr:
                        print(f"Script errors:\n{stderr.decode()}")
                
                # Start the thread to handle the output asynchronously
                output_thread = threading.Thread(target=handle_output)
                output_thread.daemon = True  # Daemon thread will exit when the main program exits
                output_thread.start()
                
                # Return a message that the script was launched successfully
                return "Script launched in background.", ""

        except Exception as e:
            return None, f"Error running the script: {e}"

    def safe_tts_say(self, text):
        """
        Safely use TTS to speak text with error handling
        
        Args:
            text: Text to speak
        """
        # Skip TTS if not available or if AI is muted
        if self.mute_llm:
            return

        if not hasattr(self, 'tts') or not self.tts:
            # Try to reinitialize TTS
            try:
                self._initialize_tts()
            except Exception as e:
                print(f"Cannot initialize TTS: {e}")
                return
                
        if not hasattr(self, 'tts_lock'):
            self.tts_lock = threading.Lock()
            
        # Create and start a non-blocking TTS thread without holding the main lock
        # The thread will acquire and release the lock only when speaking
        try:
            tts_thread = threading.Thread(target=self._tts_speak, args=(text,), daemon=True)
            tts_thread.start()
        except Exception as e:
            print(f"Error starting TTS thread: {e}")
    
    def _tts_speak(self, text):
        """
        Internal method to actually speak text
        
        Args:
            text: Text to speak
        """
        # Only try to acquire the lock when actually speaking
        if not hasattr(self, 'tts_lock'):
            self.tts_lock = threading.Lock()
            
        # Short timeout to avoid blocking the application
        if not self.tts_lock.acquire(timeout=0.1):
            print("TTS lock acquisition timeout in thread")
            return
            
        try:
            # Start with a clean engine state
            try:
                self.tts.endLoop()
            except:
                # Ignore errors from endLoop - it might not be running
                pass
                
            # Actually speak the text
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                print(f"TTS error: {e}")
                
                # Try to reinitialize TTS if there's an error
                try:
                    print("Reinitializing TTS engine after error")
                    self._initialize_tts()
                except Exception as reinit_error:
                    print(f"Failed to reinitialize TTS: {reinit_error}")
        finally:
            # Always release the lock
            try:
                self.tts_lock.release()
            except:
                # Lock might already be released if there was an error
                pass

    def ParseResponse(self, response: str):
        """
        Parse the response from the LLM
        
        Args:
            response: The response to parse
            
        Returns:
            True if the response was handled, False otherwise
        """
        import re
        import subprocess
        
        # Skip empty responses
        if not response or len(response.strip()) == 0:
            return "No response."
            
        response = response.strip()
        
        # Handle incomplete commands
        if response.startswith("INCOMPLETE_COMMAND"):
            return ""
            
        # DICTATE command - just return the text
        if response.startswith("DICTATE "):
            # Remove the command and return the rest
            return response[8:].strip()
            
        # RESET command - reset the chat history
        if response.startswith("RESET"):
            self.InitializeChat()
            
            # Call reset callback if available
            if self.on_command_reset:
                self.on_command_reset()
            return "Chat history reset."
        
        # MUTE command - mute the LLM
        if response.startswith("MUTE"):
            self.mute_llm = True
            return "AI chat muted."
            
        # UNMUTE command - unmute the LLM
        if response.startswith("UNMUTE"):
            self.mute_llm = False
            return "AI chat unmuted."
            
        # STOP command - stop transcription
        if response.startswith("STOP"):
            if self.on_command_stop:
                self.on_command_stop()
                return "Transcription stopped."
            return "Stop command received, but no handler is available."
            
        # RESUME command - resume transcription
        if response.startswith("RESUME"):
            if self.on_command_resume:
                self.on_command_resume()
                return "Transcription resumed."
            return "Resume command received, but no handler is available."
            
        # PASTE command - toggle paste
        if response.startswith("PASTE"):
            parts = response.split()
            if len(parts) > 1:
                if parts[1].lower() == "on":
                    self.automatic_paste = True
                    return "Automatic paste enabled."
                elif parts[1].lower() == "off":
                    self.automatic_paste = False
                    return "Automatic paste disabled."
            
            # Toggle if no parameter provided
            self.automatic_paste = not self.automatic_paste
            status = "enabled" if self.automatic_paste else "disabled"
            return f"Automatic paste {status}."
            
        # SWITCH_LANGUAGE command - switch language
        if response.startswith("SWITCH_LANGUAGE"):
            parts = response.split()
            if len(parts) > 1:
                lang_code = parts[1].lower()
                self.language = lang_code
                
                # Map language codes to full names
                language_names = config.AVAILABLE_LANGUAGES
                lang_name = language_names.get(lang_code, lang_code)
                
                return f"Language switched to {lang_name}."
            return "No language specified."
            
        # SEARCH command - search the web
        if response.startswith("SEARCH "):
            # Extract query between single quotes
            match = re.search(r"SEARCH '(.*?)'", response)
            if match:
                query = match.group(1)
                results = self.WebSearch(query)
                return f"Search results for '{query}':\n{results}"
            return "Invalid search format. Use: SEARCH 'query'"
        
        # WRITE_FILE command - write content to a file
        if response.startswith("WRITE_FILE "):
            # Extract filename between single quotes
            filename_match = re.search(r"WRITE_FILE '(.*?)'", response)
            if not filename_match:
                return "Invalid file write format. Use: WRITE_FILE 'filename' ```content```"
                
            filename = filename_match.group(1)
            
            # Extract content between triple backticks
            content_match = re.search(r"```([\s\S]*?)```", response)
            content = content_match.group(1) if content_match else ""
            
            # Make the path safe by resolving it inside the sandbox directory
            safe_path = os.path.join(config.LLM_SANDBOX_WORKING_FOLDER, filename)
            
            try:
                # Create directory if doesn't exist
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                
                # Write the content to the file
                with open(safe_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                return f"File '{filename}' written successfully."
            except Exception as e:
                return f"Error writing file: {e}"
                
        # RUN_SCRIPT command - run a script file
        if response.startswith("RUN_SCRIPT "):
            # Extract filename between single quotes
            match = re.search(r"RUN_SCRIPT '(.*?)'", response)
            if not match:
                return "Invalid script format. Use: RUN_SCRIPT 'filename'"
                
            script_name = match.group(1)
            
            # Make the path safe by resolving it inside the sandbox directory
            script_path = os.path.join(config.LLM_SANDBOX_WORKING_FOLDER, script_name)
            
            if not os.path.exists(script_path):
                return f"Script '{script_name}' not found."
                
            try:
                stdout, stderr = self.run_script_independently(script_path)
                
                if stderr:
                    return f"Script ran with errors:\n{stderr}"
                    
                return f"Script '{script_name}' executed successfully.\nOutput: {stdout}"
            except Exception as e:
                return f"Error running script: {e}"
            
        # RESPOND_TO_USER command - general response
        if response.startswith("RESPOND_TO_USER "):
            # Remove the command and return the rest
            return response[16:].strip()
            
        # If we didn't handle the response, just return it as is
        return response

    def _call_groq_api(self, message):
        print(f"Calling Groq API with message: {message}")
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=self.messages,
                temperature=0.4,
                max_tokens=1024,
                top_p=1,
                stream=False
            )
            reply_text = response.choices[0].message.content
            return reply_text
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return f"Error: {str(e)}"

    def set_command_callbacks(self, stop_callback=None, resume_callback=None, reset_callback=None):
        """Set callbacks for handling commands"""
        self.on_command_stop = stop_callback
        self.on_command_resume = resume_callback
        self.on_command_reset = reset_callback
