import pyaudio

class AudioService:
    FRAME_RATE = 16000
    CHANNELS = 1
    CHUNK = 8192
    BYTES_PER_SAMPLE = 2
    BYTES_PER_SECOND = BYTES_PER_SAMPLE * FRAME_RATE * CHANNELS
    BYTE_ALIGN = BYTES_PER_SAMPLE * CHANNELS
    
    def __init__(self, device_index=None):
        self.pyaudio = None
        self.stream = None
        self.device_index = device_index
        self.is_paused = False  # Track if the stream is paused
        self.device_list = []  # List of available input devices (id, name)
        
        # Always get the device list first
        self.device_list = self.get_input_devices_list()
        
        # If no device specified, use default (usually device 0)
        if self.device_index is None:
            if len(self.device_list) > 0:
                self.device_index = self.device_list[0][0]  # Use first available device
            else:
                raise ValueError("No audio input devices found")
        else:
            # Check if device_index is a string (device name search)
            if isinstance(self.device_index, str):
                self.find_device_by_name(self.device_index)
            else:
                # Validate the provided numeric device index
                self.validate_device_index(self.device_index)

    def get_input_devices_list(self):
        """
        Get a list of available input devices
        
        Returns:
            List of tuples (device_id, device_name) for available input devices
        """
        devices = []
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                devices.append((i, device_info.get('name')))
        
        p.terminate()
        return devices

    def find_device_by_name(self, device_name):
        """
        Find a device by a substring in its name
        
        Args:
            device_name: A string to search for in device names
            
        Raises:
            ValueError: If no matching device is found
        """
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        found = False
        try:
            for i in range(0, num_devices):
                device_info = p.get_device_info_by_host_api_device_index(0, i)
                if (device_info.get('maxInputChannels') > 0 and 
                    device_name.lower() in device_info.get('name').lower()):
                    self.device_index = i
                    print(f"Found matching device: {i} - {device_info.get('name')}")
                    found = True
                    break
            
            if not found:
                raise ValueError(f"No input device found with name containing '{device_name}'")
        finally:
            p.terminate()

    def validate_device_index(self, device_index):
        """
        Validate that the specified device index is valid for an input device
        
        Args:
            device_index: The index to validate
            
        Raises:
            ValueError: If the device index is invalid
        """
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        try:
            if device_index < 0 or device_index >= num_devices:
                raise ValueError(f"Invalid device index {device_index}. Must be between 0 and {num_devices-1}")
            
            device_info = p.get_device_info_by_host_api_device_index(0, device_index)
            if device_info.get('maxInputChannels') <= 0:
                raise ValueError(f"Device {device_index} - {device_info.get('name')} is not an input device")
        finally:
            p.terminate()

    def list_input_devices(self):
        """
        Print available input devices to the console
        """
        print("\nAvailable input devices:")
        for device_id, device_name in self.device_list:
            print(f"Input Device id {device_id} - {device_name}")

    def switch_device(self, device_index):
        """
        Switch to a different input device
        
        Args:
            device_index: The index of the device to switch to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate the device index
            self.validate_device_index(device_index)
            
            # Skip if already using this device
            if self.device_index == device_index:
                return True
            
            # Completely stop and clean up the current recording session
            self.StopRecording()
            
            # Update the device index
            self.device_index = device_index
            
            # We need to initialize a clean state before starting
            self.accumulated_data = b''
            self.accumulated_time = 0
            self.dropped_bytes = 0
            self.dropped_time = 0
            self.is_paused = False
            
            # Create a fresh PyAudio instance
            self.pyaudio = pyaudio.PyAudio()
            
            # Don't automatically Start Transcription - let the caller do that
            # This allows proper sequencing with other components
            
            print(f"Successfully switched to audio device {device_index}")
            return True
        except Exception as e:
            print(f"Error switching device: {e}")
            return False

    def StartRecording(self):
        """Start the audio recording process"""
        self.pyaudio = pyaudio.PyAudio()
        self.accumulated_data = b''
        self.accumulated_time = 0
        self.dropped_bytes = 0
        self.dropped_time = 0
        self.is_paused = False

        if self.device_index is None:
            self.device_index = self.pyaudio.get_default_input_device_info()['index']

        self._create_stream()
        
        deviceInfo = self.pyaudio.get_device_info_by_index(self.device_index)
        print(f"Listening on device {deviceInfo.get('name')}... Press Ctrl+C to stop.\n")

    def _create_stream(self):
        """Create a new audio stream"""
        if self.pyaudio is None:
            self.pyaudio = pyaudio.PyAudio()
            
        if self.stream is not None:
            try:
                self.stream.close()
            except:
                # Ignore errors when closing an already closed stream
                pass
            
        self.stream = self.pyaudio.open(format=pyaudio.paInt16,
                        channels=self.CHANNELS,
                        rate=self.FRAME_RATE,
                        input=True,
                        input_device_index=self.device_index,
                        frames_per_buffer=self.CHUNK)

    def PauseRecording(self):
        """Pause the audio recording stream"""
        if self.stream and not self.is_paused:
            try:
                self.stream.stop_stream()
                self.is_paused = True
                return True
            except Exception as e:
                print(f"Warning: Error pausing audio stream: {e}")
                return False
        return False
    
    def ResumeRecording(self):
        """Resume the audio recording stream"""
        if self.is_paused:
            try:
                # Check if the stream is still valid
                if self.stream:
                    try:
                        # Try to start the stream if it exists and is stopped
                        self.stream.start_stream()
                        self.is_paused = False
                        return True
                    except Exception as e:
                        # If error occurs while starting, create a new stream
                        print(f"Warning: Error resuming existing stream, creating new stream: {e}")
                        self._create_stream()
                        self.is_paused = False
                        return True
                else:
                    # Create a new stream if the old one is gone
                    self._create_stream()
                    self.is_paused = False
                    return True
            except Exception as e:
                print(f"Warning: Error resuming audio stream: {e}")
                return False
        return True  # Already resumed

    def ReadChunk(self):
        """Read a chunk of audio data from the stream"""
        # Return silence if paused or no stream
        if self.is_paused or not self.stream:
            return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
            
        try:
            # Safely check if stream is active
            is_active = False
            try:
                is_active = self.stream.is_active()
            except OSError:
                # Handle "Stream not open" error gracefully
                self.log_warning("Stream not open, recreating stream...")
                self._create_stream()
                return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
                
            if not is_active:
                # Try to restart the stream
                try:
                    self.log_warning("Stream not active, attempting to restart...")
                    self.stream.start_stream()
                except:
                    # If we can't restart, recreate it
                    self._create_stream()
                return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
                
            # Read from the stream with error handling
            try:
                chunk_data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                
                # Validate the chunk data (must be the expected size)
                expected_size = self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE
                if len(chunk_data) != expected_size:
                    self.log_warning(f"Invalid chunk size: {len(chunk_data)} bytes, expected {expected_size}")
                    return b'\x00' * expected_size
                    
                self.accumulated_data += chunk_data
                chunk_duration = len(chunk_data) / self.BYTES_PER_SECOND
                self.accumulated_time += chunk_duration
                return chunk_data
            except Exception as e:
                self.log_warning(f"Error reading chunk: {e}")
                return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
                
        except IOError as e:
            # Handle potential errors when reading from a paused/stopped stream
            self.log_warning(f"IOError reading audio chunk: {e}")
            return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
            
    def log_warning(self, message):
        """Helper to log warnings consistently"""
        print(f"Warning: {message}")

    def DropAudioBuffer(self):
        self.dropped_bytes += len(self.accumulated_data)
        self.dropped_time += self.accumulated_time
        self.accumulated_data = b''
        self.accumulated_time = 0

    def ExtractAudioData(self, start, duration):
        # Enforce a minimum duration (0.1 seconds should be safe)
        MIN_DURATION_SECONDS = 0.1
        if duration < MIN_DURATION_SECONDS:
            duration = MIN_DURATION_SECONDS
        
        startOffset = int((start * self.BYTES_PER_SECOND) / self.BYTE_ALIGN) * self.BYTE_ALIGN
        bytes_count = int((duration * self.BYTES_PER_SECOND) / self.BYTE_ALIGN) * self.BYTE_ALIGN
        
        # Ensure we have at least 160 bytes (10ms of audio at 16kHz, 16-bit, mono)
        MIN_BYTES = 320  # 20ms minimum to be safe
        if bytes_count < MIN_BYTES:
            bytes_count = MIN_BYTES
        
        startOffset -= self.dropped_bytes
        if startOffset < 0:
            bytes_count += startOffset
            startOffset = 0

        if startOffset + bytes_count > len(self.accumulated_data):
            # If we don't have enough data yet, return None to signal caller 
            # to wait for more data rather than sending a too-short sample
            if len(self.accumulated_data) < MIN_BYTES:
                return None
                
            bytes_count = len(self.accumulated_data) - startOffset
            
        # Final check to ensure we're not returning too little data
        if bytes_count < MIN_BYTES:
            return None
            
        return self.accumulated_data[startOffset:startOffset+bytes_count]

    def StopRecording(self):
        """Stop recording and clean up resources"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Warning: Error stopping stream: {e}")
            self.stream = None
        
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except Exception as e:
                print(f"Warning: Error terminating PyAudio: {e}")
            self.pyaudio = None
