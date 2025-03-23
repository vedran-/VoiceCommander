import torch
import numpy as np
import wave
import time
from datetime import datetime
from scripts.AudioService import AudioService

class SpeechRecorder:
    def __init__(self, speech_threshold=0.5, buffer_duration=0.5, silence_duration=1.0, energy_threshold=500):
        self.audio_service = AudioService()
        try:
            self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                           model='silero_vad',
                                           force_reload=True)
        except Exception as e:
            print(f"Error loading Silero VAD model: {e}")
            raise

        self.recording = False
        self.speech_threshold = speech_threshold
        self.buffer_duration = buffer_duration
        self.silence_duration = silence_duration
        self.energy_threshold = energy_threshold
        self.buffer = []
        self.current_speech = []
        self.last_speech_time = 0
        self.chunk_size = 512
        
        if self.audio_service.CHUNK % self.chunk_size != 0:
            raise ValueError(f"AudioService.CHUNK ({self.audio_service.CHUNK}) must be divisible by chunk_size ({self.chunk_size})")

    def start_recording(self):
        self.audio_service.StartRecording()
        self.recording = True
        no_speech_counter = 0
        while self.recording:
            try:
                audio_chunk = self.audio_service.ReadChunk()
                if self._process_audio(audio_chunk):
                    no_speech_counter = 0
                else:
                    no_speech_counter += 1
                
                # If no speech detected for a while, wait longer before processing the next chunk
                if no_speech_counter > 100:  # Adjust this value as needed
                    time.sleep(0.1)  # Adjust this value as needed
            except Exception as e:
                print(f"Error processing audio: {e}")
                self.stop_recording()

    def stop_recording(self):
        self.recording = False
        self.audio_service.StopRecording()
        self._save_current_speech()

    def _process_audio(self, audio_chunk):
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Energy-based pre-filter
        energy = np.sum(np.abs(audio_int16)) / len(audio_int16)
        if energy < self.energy_threshold:
            return False

        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        speech_detected = False
        processed_chunks = []

        for i in range(0, len(audio_float32), self.chunk_size):
            chunk = audio_float32[i:i+self.chunk_size]
            if len(chunk) < self.chunk_size:
                # Pad the last chunk if it's smaller than chunk_size samples
                chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)), 'constant')
            
            speech_prob = self.model(torch.from_numpy(chunk), 16000).item()
            processed_chunks.append(chunk)
            
            if speech_prob > self.speech_threshold:
                speech_detected = True
                self.last_speech_time = self.audio_service.accumulated_time
                if not self.current_speech:
                    self.current_speech.extend(self.buffer)
                self.current_speech.extend(processed_chunks)
                break  # Exit the loop if speech is detected
        
        if not speech_detected:
            self.buffer.extend(processed_chunks)
            buffer_duration = len(self.buffer) * self.chunk_size / self.audio_service.FRAME_RATE
            while buffer_duration > self.buffer_duration:
                self.buffer.pop(0)
                buffer_duration = len(self.buffer) * self.chunk_size / self.audio_service.FRAME_RATE

        current_time = self.audio_service.accumulated_time
        if self.current_speech and (current_time - self.last_speech_time) > self.silence_duration:
            self._save_current_speech()

        return speech_detected

    def _save_current_speech(self):
        if not self.current_speech:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"speech_{timestamp}.wav"
        
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.audio_service.CHANNELS)
                wf.setsampwidth(self.audio_service.BYTES_PER_SAMPLE)
                wf.setframerate(self.audio_service.FRAME_RATE)
                audio_int16 = (np.concatenate(self.current_speech) * 32768).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())

            print(f"Speech detected and saved to {filename}")
        except Exception as e:
            print(f"Error saving speech file: {e}")
        finally:
            self.current_speech = []

    def adjust_parameters(self, speech_threshold=None, buffer_duration=None, silence_duration=None, energy_threshold=None):
        if speech_threshold is not None:
            self.speech_threshold = speech_threshold
        if buffer_duration is not None:
            self.buffer_duration = buffer_duration
        if silence_duration is not None:
            self.silence_duration = silence_duration
        if energy_threshold is not None:
            self.energy_threshold = energy_threshold
        print(f"Parameters updated: speech_threshold={self.speech_threshold}, buffer_duration={self.buffer_duration}, "
              f"silence_duration={self.silence_duration}, energy_threshold={self.energy_threshold}")

# Usage example
if __name__ == "__main__":
    recorder = SpeechRecorder()
    
    print("Starting speech recording. Press Ctrl+C to stop.")
    try:
        recorder.start_recording()
    except KeyboardInterrupt:
        print("\nStopping speech recording.")
        recorder.stop_recording()
    
    print("Speech recording completed.")

    # Example of adjusting parameters
    recorder.adjust_parameters(speech_threshold=0.6, energy_threshold=600)