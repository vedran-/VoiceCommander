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
        
        if self.device_index is None:
            self.initialize()
        else:
            # Check if device_index is a string (device name search)
            if isinstance(self.device_index, str):
                self.find_device_by_name(self.device_index)
            else:
                # Validate the provided numeric device index
                self.validate_device_index(self.device_index)

    def initialize(self):
        self.list_input_devices()
        self.device_index = int(input("\nEnter the device index you want to use: "))
        # Validate the selected device index
        self.validate_device_index(self.device_index)

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
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        print("\nAvailable input devices:")
        for i in range(0, num_devices):
            deviceInfo = p.get_device_info_by_host_api_device_index(0, i)
            if (deviceInfo.get('maxInputChannels')) > 0:
                print(f"Input Device id {i} - {deviceInfo.get('name')}")
        
        p.terminate()

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
                return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
                
            if not is_active:
                # Return silence if stream is not active
                return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
                
            # Read from the stream
            chunk_data = self.stream.read(self.CHUNK)
            self.accumulated_data += chunk_data
            chunk_duration = len(chunk_data) / self.BYTES_PER_SECOND
            self.accumulated_time += chunk_duration
            return chunk_data
        except IOError as e:
            # Handle potential errors when reading from a paused/stopped stream
            print(f"Warning: Error reading audio chunk: {e}")
            return b'\x00' * (self.CHUNK * self.CHANNELS * self.BYTES_PER_SAMPLE)
    
    def DropAudioBuffer(self):
        self.dropped_bytes += len(self.accumulated_data)
        self.dropped_time += self.accumulated_time
        self.accumulated_data = b''
        self.accumulated_time = 0

    def ExtractAudioData(self, start, duration):
        startOffset = int((start * self.BYTES_PER_SECOND) / self.BYTE_ALIGN) * self.BYTE_ALIGN
        bytes_count = int((duration * self.BYTES_PER_SECOND) / self.BYTE_ALIGN) * self.BYTE_ALIGN

        startOffset -= self.dropped_bytes
        if startOffset < 0:
            bytes_count += startOffset
            startOffset = 0

        if startOffset + bytes_count > len(self.accumulated_data):
            bytes_count = len(self.accumulated_data) - startOffset

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
