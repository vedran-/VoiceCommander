import json
import os
import string
import pyperclip
import pyautogui
import wave
from . import GroqWhisperService
from . import config
from vosk import KaldiRecognizer
from datetime import datetime
import time
from . import AudioService
from PyQt6.QtCore import QObject, pyqtSignal

class QtTranscriptionService(QObject):
    """Qt-compatible version of the TranscriptionService"""
    
    # Define Qt signals
    transcription_result = pyqtSignal(str)  # Emitted when new transcription is available
    llm_response = pyqtSignal(str)          # Emitted when LLM responds
    audio_state_changed = pyqtSignal(bool)  # Emitted when audio recording state changes (True=recording, False=paused)
    status_update = pyqtSignal(str)         # Emitted for status updates
    error = pyqtSignal(str)                 # Emitted on errors
    
    ALLOWED_CHARACTERS = set(' _-,.;()[]{}!@#$%^&') | set(string.ascii_letters + string.digits)
    INVALID_CHARACTERS = "<>:\"/\\|?*"
    INVALID_WORDS = {'', 'huh', 'uh', 'um', 'ah', 'oh', 'eh', 'do'}

    def __init__(self, vosk_service, audio_service):
        super().__init__()
        self.vosk_service = vosk_service
        self.audio_service = audio_service
        os.makedirs(config.AUDIO_FILES_SAVE_FOLDER, exist_ok=True)

        # Create GroqWhisperService and provide a reference to this service
        self.groq_whisper_service = GroqWhisperService.GroqWhisperService()
        
        # Transcription state control
        self.is_transcribing = True
        self.transcribing_active = False  # Flag to control the transcription loop
        
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
            if isinstance(result, str) and result:
                self.llm_response.emit(result)
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
                result = json.loads(self.recognizer.Result())
                if result.get('text'):
                    recognized_text = result['text']
                    if recognized_text in self.INVALID_WORDS:
                        return True

                    textData = result['result']

                    textStartTime = textData[0]['start']
                    if textData[0]['end'] - textStartTime > 0.5:    # Don't allow single words longer than 0.5s
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

            whisper_text = self.groq_whisper_service.TranscribeAudio(audio_data)
            if whisper_text is None:
                return

            # Handle special case for unmute command
            if whisper_text.lower().startswith("unmute"):
                self.groq_whisper_service.mute_llm = False

            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_text = f"{timestamp} > {whisper_text}"
            
            # Emit the transcription result signal
            self.transcription_result.emit(formatted_text)

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
                
        except Exception as e:
            error_msg = f"Error processing speech: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg)

    def save_wav(self, audio_data, text):
        """Save recorded audio to a WAV file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_text = ''.join(c for c in text if c not in self.INVALID_CHARACTERS)[:120]
            filename = os.path.join(config.AUDIO_FILES_SAVE_FOLDER, f"transcription_{timestamp} - {safe_text}.wav")
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.audio_service.CHANNELS)
                wf.setsampwidth(self.audio_service.BYTES_PER_SAMPLE)  # 2 bytes for 'int16' as used by PyAudio
                wf.setframerate(self.audio_service.FRAME_RATE)
                wf.writeframes(audio_data)
                
        except Exception as e:
            error_msg = f"Error saving WAV file: {e}"
            self.status_update.emit(error_msg)
            self.error.emit(error_msg) 