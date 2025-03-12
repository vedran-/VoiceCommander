import json
import os
import string
import pyperclip
import pyautogui
import pygame
import wave
from . import GroqWhisperService
from . import KeyboardService
from . import config
from vosk import KaldiRecognizer
from datetime import datetime
import time
from . import AudioService

class TranscriptionService:
    ALLOWED_CHARACTERS = set(' _-,.;()[]{}!@#$%^&') | set(string.ascii_letters + string.digits)
    INVALID_CHARACTERS = "<>:\"/\\|?*"
    INVALID_WORDS = {'', 'huh', 'uh', 'um', 'ah', 'oh', 'eh', 'do'}

    def __init__(self, vosk_service, audio_service):
        self.vosk_service = vosk_service
        self.audio_service = audio_service
        os.makedirs(config.AUDIO_FILES_SAVE_FOLDER, exist_ok=True)

        # Initialize PyGame early for both sound and keyboard handling
        if not pygame.get_init():
            pygame.init()
        pygame.mixer.init()
        self.ping_sound = pygame.mixer.Sound("c:/pj/projects/VoiceCommander/assets/snd_fragment_retrievewav-14728.mp3")
        self.ping_sound.set_volume(0.5)

        self.groq_whisper_service = GroqWhisperService.GroqWhisperService()
        
        # Transcription state control
        self.is_transcribing = True
        
        # Initialize the keyboard service with a reference to this service
        self.keyboard_service = KeyboardService.KeyboardService(
            self.groq_whisper_service, 
            self
        )
        
        # Give GroqWhisperService a reference to the keyboard service
        # This allows it to control transcription via voice commands
        self.groq_whisper_service.keyboard_service = self.keyboard_service

    def pause_transcription(self):
        """Pause the transcription process"""
        self.is_transcribing = False
        # Use the new dedicated method for pausing recording
        if hasattr(self, 'audio_service') and self.audio_service:
            self.audio_service.PauseRecording()
    
    def resume_transcription(self):
        """Resume the transcription process"""
        self.is_transcribing = True
        # Use the new dedicated method for resuming recording
        if hasattr(self, 'audio_service') and self.audio_service:
            if not self.audio_service.ResumeRecording():
                # If resume failed, try creating a new stream
                print("Warning: Failed to resume recording, attempting to restart...")
                try:
                    # Recreate the audio service as a last resort
                    device_index = self.audio_service.device_index
                    self.audio_service.StopRecording()
                    self.audio_service = AudioService.AudioService(device_index)
                    self.audio_service.StartRecording()
                    print("Successfully restarted recording")
                except Exception as e:
                    print(f"Error restarting recording: {e}")
                    self.is_transcribing = False

    def Transcribe(self):
        # Start the keyboard service before recording
        self.keyboard_service.start()
        
        self.audio_service.StartRecording()

        print("Transcription started. Listening for keyboard shortcuts and voice commands.")
        print("PyGame window must have focus for local keyboard shortcuts to work.")
        print("Click on the PyGame window to give it focus for local shortcuts.")

        rec = KaldiRecognizer(self.vosk_service.model, self.audio_service.FRAME_RATE)
        rec.SetWords(True)
        rec.SetPartialWords(True)
        # Disable Natural Language Semantic Markup Language (NLSML) output
        # This setting allows the recognizer to provide more structured and detailed output
        # including semantic interpretations of the recognized speech
        rec.SetNLSML(False)
        rec.Reset()

        # Make sure pygame processes its events 
        pygame.event.pump()

        try:
            while True:
                # Process any pending PyGame events
                pygame.event.pump()
                
                # Check for local keyboard input (non-blocking)
                self.keyboard_service.check_local_keys()
                
                # Skip processing if transcription is paused
                if not self.is_transcribing:
                    time.sleep(0.1)  # Sleep to avoid CPU spinning
                    continue
                    
                audio_chunk = self.audio_service.ReadChunk()

                if rec.AcceptWaveform(audio_chunk):
                    result = json.loads(rec.Result())
                    if result.get('text'):
                        recognized_text = result['text']
                        if recognized_text in self.INVALID_WORDS:
                            continue

                        textData = result['result']

                        textStartTime = textData[0]['start']
                        if textData[0]['end'] - textStartTime > 0.5:    # Don't allow single words longer than 0.5s
                            textStartTime = textData[0]['end'] - 1.5
                        textEndTime = textData[-1]['end']
                        textDuration = textEndTime - textStartTime

                        self.OnSpeechRecognized(textStartTime, textDuration)

                        # Reset the audio for the next recognition
                        rec.Reset()
                        self.audio_service.DropAudioBuffer()

        except KeyboardInterrupt:
            print("Stopped listening.")
        finally:
            # Stop the keyboard service before stopping recording
            self.keyboard_service.stop()
            self.audio_service.StopRecording()

    def OnSpeechRecognized(self, textStartTime, textDuration):
        audio_data = self.audio_service.ExtractAudioData(textStartTime-0.25, textDuration+0.25)

        whisper_text = self.groq_whisper_service.TranscribeAudio(audio_data)
        if whisper_text is None:
            return

        self.ping_sound.play()        
        
        if whisper_text.lower().startswith("unmute"):
            self.groq_whisper_service.mute_llm = False

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{timestamp}> \033[93m{whisper_text}\033[0m")

        # Copy the recognized text to the clipboard
        pyperclip.copy(whisper_text + ' ')

        if self.groq_whisper_service.automatic_paste:
            # Paste the recognized text from the clipboard
            pyautogui.hotkey('ctrl', 'v')
        
        # Send the text to LLM for further processing
        if self.groq_whisper_service.mute_llm == False:
            self.groq_whisper_service.AddUserMessage(whisper_text)

        # Save the accumulated audio as a .wav file
        if config.SAVE_AUDIO_FILES:
            self.save_wav(audio_data, whisper_text)

    def save_wav(self, audio_data, text):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_text = ''.join(c for c in text if c not in self.INVALID_CHARACTERS)[:120]
        filename = os.path.join(config.AUDIO_FILES_SAVE_FOLDER, f"transcription_{timestamp} - {safe_text}.wav")
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.audio_service.CHANNELS)
            wf.setsampwidth(self.audio_service.BYTES_PER_SAMPLE)  # 2 bytes for 'int16' as used by PyAudio
            wf.setframerate(self.audio_service.FRAME_RATE)
            wf.writeframes(audio_data)
        
        #print(f"Saved audio file: {filename}")
