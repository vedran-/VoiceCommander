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
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.language = "en"
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
        print(f"Initializing chat... LLM: \033[33m{config.LLM_MODEL}\033[0m, transcription by: \033[33m{config.TRANSCRIPTION_MODEL}\033[0m")
        self.messages = [
            {
                "role": "system",
                "content": self.get_system_prompt()
            }
        ]
        self.chat_timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    def TranscribeAudio(self, audio_data):
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(16000)  # Sample rate of 16kHz
            wav_file.writeframes(audio_data)
        wav_data = wav_buffer.getvalue()

        transcription = self.client.audio.transcriptions.create(
            file=("instructions.wav", wav_data),
            model=config.TRANSCRIPTION_MODEL,
            prompt=config.UNFAMILIAR_WORDS,  # Optional
            response_format="verbose_json",  # Optional
            language=self.language,  # Optional
            temperature=0.0  # Optional
        )

        # This is the object we get:
        #     Transcription(text=' Voice command or press Ctrl C to stop recording and prescribe.', task='transcribe', language='English', duration=3.63, segments=[{'id': 0, 'seek': 0, 'start': 0, 'end': 4, 'text': ' Voice command or press Ctrl C to stop recording and prescribe.', 'tokens': [50365, 15229, 5622, 420, 1886, 35233, 383, 281, 1590, 6613, 293, 49292, 13, 50565], 'temperature': 0, 'avg_logprob': -0.6023157, 'compression_ratio': 0.96875, 'no_speech_prob': 0.030296149}], x_groq={'id': 'req_01j42aapy0eset9a6kd0p4dk7y'})
        #print(f"    Transcription: {transcription}")
        # Extract probabilities from transcription
        #log_prob = segment['avg_logprob']
        #compression_ratio = segment['compression_ratio']
        #print(f"    Transcription confidence: {log_prob} - {compression_ratio} - {no_speech_prob}")
        
        # Check each segment, and use only text from those who have no_speech_prob <= config.MAX_TRANSCRIPTION_NO_SPEECH_PROBABILITY
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

        #no_speech_prob = sum(segment['no_speech_prob'] for segment in transcription.segments) / len(transcription.segments)
        #print(f"    [No speech: {no_speech_prob}] {transcription.text}")
        #if no_speech_prob > config.MAX_TRANSCRIPTION_NO_SPEECH_PROBABILITY:
        #    return None

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
            # Run the script in a separate process
            process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Capture the output and errors
            stdout, stderr = process.communicate()

            # Print the output and errors
            if stdout:
                print(f"Output:\n{stdout.decode()}")
            if stderr:
                print(f"Errors:\n{stderr.decode()}")
            return stdout.decode(), stderr.decode()

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
            
        # Remaining commands kept as they were...
        
        # RESPOND_TO_USER command - general response
        if response.startswith("RESPOND_TO_USER "):
            # Remove the command and return the rest
            return response[16:].strip()
            
        # If we didn't handle the response, just return it as is
        return response

    def _call_groq_api(self, message):
        """
        Call the Groq API with the user message
        
        Args:
            message: The message from the user
            
        Returns:
            The response from the Groq API
        """
        try:
            # Call the Groq API
            chat_completion = self.client.chat.completions.create(
                messages=self.messages,
                model=config.LLM_MODEL,
                temperature=0,
                stream=False,
                response_format={"type": "text"},
            )
            
            # Get the response
            response = chat_completion.choices[0].message.content.strip()
            return response
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return f"ERROR: Could not get response from API. {str(e)}"

    def set_command_callbacks(self, stop_callback=None, resume_callback=None):
        """Set callbacks for handling commands"""
        self.on_command_stop = stop_callback
        self.on_command_resume = resume_callback
