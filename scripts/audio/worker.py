import time
import logging
from PyQt6.QtCore import QThread

logger = logging.getLogger('VoiceCommander')

class AudioProcessingWorker(QThread):
    """
    Worker thread for processing audio
    """
    def __init__(self, transcription_service):
        super().__init__()
        self.transcription_service = transcription_service
        self.running = True
    
    def run(self):
        """Run the audio processing loop"""
        logger.info("Audio processing thread started")
        
        try:
            while self.running:
                # Process audio in small chunks to keep UI responsive
                if not self.transcription_service.process_audio():
                    # If processing failed, wait a moment before retrying
                    time.sleep(0.1)
                    
                # Small sleep to prevent CPU overuse
                time.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in audio processing thread: {e}", exc_info=True)
        finally:
            logger.info("Audio processing thread stopped")
    
    def stop(self):
        """Stop the audio processing thread"""
        self.running = False
        self.quit()
        self.wait() 