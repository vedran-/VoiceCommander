import json
import os
import string
import pyperclip
import pyautogui
import pygame
import wave
from . import GroqWhisperService
from . import config
from vosk import KaldiRecognizer
from datetime import datetime
import time
from . import AudioService
from PyQt6.QtCore import QObject, pyqtSignal

class TranscriptionService(QObject):
    """
    Transcription service for Voice Commander
    
    This service handles:
    - Audio processing and transcription
    - Integration with GroqWhisperService for LLM commands
    - Sound notifications
    - Signal emission for UI updates
    """
    
    # Define Qt signals
    transcription_result = pyqtSignal(dict)  # Emitted when new transcription is available (dict: {'timestamp': str, 'text': str, 'audio_path': str | None})
    llm_response = pyqtSignal(str)          # Emitted when LLM responds
    audio_state_changed = pyqtSignal(bool)  # Emitted when audio recording state changes (True=recording, False=paused)
    status_update = pyqtSignal(str)         # Emitted for status updates
    error = pyqtSignal(str)                 # Emitted on errors
    ui_state_changed = pyqtSignal()         # Emitted when UI state needs to be updated
    
    ALLOWED_CHARACTERS = set(' _-,.;()[]{}!@#$%^&') | set(string.ascii_letters + string.digits)
    INVALID_CHARACTERS = "<>:\"/\\|?*"
    INVALID_WORDS = {'', 'huh', 'uh', 'um', 'ah', 'oh', 'eh', 'do'} 

    def __init__(self, vosk_service, audio_service):
        super().__init__()
        self.vosk_service = vosk_service
        self.audio_service = audio_service
        os.makedirs(config.AUDIO_FILES_SAVE_FOLDER, exist_ok=True)

        # Initialize PyGame for sound playback
        if not pygame.get_init():
            pygame.init()
        pygame.mixer.init()
        self.ping_sound = pygame.mixer.Sound("c:/pj/projects/VoiceCommander/assets/snd_fragment_retrievewav-14728.mp3")
        self.ping_sound.set_volume(0.5)
        self.push_to_talk_sound = pygame.mixer.Sound("c:/pj/projects/VoiceCommander/assets/bubble-pop-4-323580.mp3")
        self.push_to_talk_sound.set_volume(0.5)

        # Create GroqWhisperService and provide a reference to this service
        self.groq_whisper_service = GroqWhisperService.GroqWhisperService()
        
        # Transcription state control
        self.is_transcribing = True
        self.transcribing_active = False  # Flag to control the transcription loop

        self.is_push_to_talk_mode = False
        self.pause_transcription_on_end_of_push_to_talk = False
        
        # Initialize the recognizer
        self.recognizer = KaldiRecognizer(self.vosk_service.model, self.audio_service.FRAME_RATE)
        self.recognizer.SetWords(True)
        self.recognizer.SetPartialWords(True)
        self.recognizer.SetNLSML(False)
        self.recognizer.Reset()
        
        # Override LLM response handler to emit signal
        self._override_groq_service()

    def _override_groq_service(self):
        """Override GroqWhisperService methods to emit signals instead of printing"""
        original_parse_response = self.groq_whisper_service.ParseResponse
        
        def new_parse_response(response):
            result = original_parse_response(response)
            
            # Emit the response as a message
            if isinstance(result, str) and result:
                self.llm_response.emit(result)
                
                # Emit status update for specific commands to make them visible in the status area
                if response.startswith("MUTE") or response.startswith("UNMUTE") or \
                   response.startswith("PASTE") or response.startswith("RESET") or \
                   response.startswith("SWITCH_LANGUAGE"):
                    self.status_update.emit(result)
                    
                    # Signal that UI needs to be updated
                    self.ui_state_changed.emit()
                
            return result
            
        self.groq_whisper_service.ParseResponse = new_parse_response
        
    def pause_transcription(self):
        """Pause the transcription process"""
        self.is_transcribing = False
        self.status_update.emit("Transcription paused")
        self.audio_state_changed.emit(False)
        
        # Use the dedicated method for pausing recording
        if hasattr(self, 'audio_service') and self.audio_service:
            self.audio_service.PauseRecording()
    
    def resume_transcription(self):
        """Resume the transcription process"""
        self.is_transcribing = True
        self.status_update.emit("Transcription resumed")
        self.audio_state_changed.emit(True)
        
        # Use the dedicated method for resuming recording
        if hasattr(self, 'audio_service') and self.audio_service:
            if not self.audio_service.ResumeRecording():
                # If resume failed, try creating a new stream
                self.status_update.emit("Warning: Failed to resume recording, attempting to restart...")
                try:
                    # Recreate the audio service as a last resort
                    device_index = self.audio_service.device_index
                    self.audio_service.StopRecording()
                    self.audio_service = AudioService.AudioService(device_index)
                    self.audio_service.StartRecording()
                    self.status_update.emit("Successfully restarted recording")
                except Exception as e:
                    error_msg = f"Error restarting recording: {e}"
                    self.status_update.emit(error_msg)
                    self.error.emit(error_msg)
                    self.is_transcribing = False
                    self.audio_state_changed.emit(False)

    def start_transcription(self):
        """Start the transcription loop in a non-blocking way"""
        self.audio_service.StartRecording()
        self.transcribing_active = True
        self.is_transcribing = True
        self.audio_state_changed.emit(True)
        self.status_update.emit("Transcription started")

    def stop_transcription(self):
        """Stop the transcription loop"""
        self.transcribing_active = False
        self.is_transcribing = False
        self.audio_state_changed.emit(False)
        self.audio_service.StopRecording()
        self.status_update.emit("Transcription stopped")

    def toggle_push_to_talk(self):
        """Toggle push-to-talk mode"""
        self.is_push_to_talk_mode = not self.is_push_to_talk_mode

        if self.is_push_to_talk_mode:
            # Play sound when push-to-talk is activated
            self.push_to_talk_sound.play()
            
            if not self.is_transcribing:
                self.resume_transcription()
                self.pause_transcription_on_end_of_push_to_talk = True
            else:
                self.pause_transcription_on_end_of_push_to_talk = False
        else:
            self.process_audio()
            if self.pause_transcription_on_end_of_push_to_talk:
                self.pause_transcription()
                self.pause_transcription_on_end_of_push_to_talk = False

        self.status_update.emit(f"Push-to-talk mode {'enabled' if self.is_push_to_talk_mode else 'disabled'}")

    def process_audio(self):
        """Process a single chunk of audio - call this regularly from a worker thread"""
        if not self.transcribing_active:
            return False
            
        if not self.is_transcribing:
            # Sleep handled by caller thread
            return True

        try:
            audio_chunk = self.audio_service.ReadChunk()

            if self.recognizer.AcceptWaveform(audio_chunk):

                if self.is_push_to_talk_mode:
                    return True

                result = json.loads(self.recognizer.Result())
                if result.get('text'):
                    recognized_text = result['text']
                    if recognized_text in self.INVALID_WORDS:
                        return True

                    textData = result['result']

                    textStartTime = textData[0]['start']
                    if textData[0]['end'] - textStartTime > 2.5:    # Don't allow single words longer than 0.5s
                        textStartTime = textData[0]['end'] - 1.5
                    textEndTime = textData[-1]['end']
                    textDuration = textEndTime - textStartTime

                    self.OnSpeechRecognized(textStartTime, textDuration)

                    # Reset the audio for the next recognition
                    self.recognizer.Reset()
                    self.audio_service.DropAudioBuffer()
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing audio: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg)
            return False

    def OnSpeechRecognized(self, textStartTime, textDuration):
        """Handle recognized speech"""
        try:
            audio_data = self.audio_service.ExtractAudioData(textStartTime-0.25, textDuration+0.25)
            
            # Skip if not enough audio data is available
            if audio_data is None or len(audio_data) < 320:  # Minimum 20ms of audio
                self.status_update.emit("Speech detected but audio sample too short, ignoring")
                return

            whisper_text = self.groq_whisper_service.TranscribeAudio(audio_data)
            if whisper_text is None:
                return

            # Play notification sound
            self.ping_sound.play()

            # Handle special case for unmute command
            if whisper_text.lower().startswith("unmute"):
                self.groq_whisper_service.mute_llm = False

            timestamp = datetime.now().strftime("%H:%M:%S")
            # formatted_text = f"{timestamp} > {whisper_text}" # Old format

            audio_path = None
            # Save the accumulated audio as a .wav file if enabled
            if config.SAVE_AUDIO_FILES:
                audio_path = self.save_wav(audio_data, whisper_text)
            
            # Emit the structured transcription result signal
            result_data = {
                'timestamp': timestamp,
                'text': whisper_text,
                'audio_path': audio_path
            }
            self.transcription_result.emit(result_data)

            pyperclip.copy(whisper_text + ' ')

            if self.groq_whisper_service.automatic_paste:
                # Paste the recognized text from the clipboard
                pyautogui.hotkey('ctrl', 'v')
            
            # Send the text to LLM for further processing
            if self.groq_whisper_service.mute_llm == False:
                self.groq_whisper_service.AddUserMessage(whisper_text)

            # Removed saving here, it's now part of the conditional block above
                
        except Exception as e:
            error_msg = f"Error handling speech recognition: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg)

    def save_wav(self, audio_data, text):
        """Save recorded audio to a WAV file and return the filename."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_text = ''.join(c for c in text if c not in self.INVALID_CHARACTERS)[:120]
            filename = os.path.join(config.AUDIO_FILES_SAVE_FOLDER, f"transcription_{timestamp} - {safe_text}.wav")
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.audio_service.CHANNELS)
                wf.setsampwidth(self.audio_service.BYTES_PER_SAMPLE)  # 2 bytes for 'int16' as used by PyAudio
                wf.setframerate(self.audio_service.FRAME_RATE)
                wf.writeframes(audio_data)
            
            return filename # Return the filename
                
        except Exception as e:
            error_msg = f"Error saving WAV file: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg)
            return None # Return None on error

    def reset_recognizer(self):
        """Reset and recreate the recognizer - call this when changing microphones"""
        try:
            # First make sure any active recognition is stopped
            if hasattr(self, 'recognizer'):
                self.recognizer.Reset()
            
            # Create a brand new recognizer instance
            self.recognizer = KaldiRecognizer(self.vosk_service.model, self.audio_service.FRAME_RATE)
            self.recognizer.SetWords(True)
            self.recognizer.SetPartialWords(True)
            self.recognizer.SetNLSML(False)
            self.recognizer.Reset()
            
            # Reset the audio buffer to prevent using old data with the new recognizer
            if hasattr(self, 'audio_service') and self.audio_service:
                self.audio_service.DropAudioBuffer()
            
            self.status_update.emit("Speech recognizer has been reset for new microphone")
            return True
        except Exception as e:
            error_msg = f"Error resetting recognizer: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg)
            return False 