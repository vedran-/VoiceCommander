from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import numpy as np
from scipy.io import wavfile
import os
import torch

def extract_and_save_segment(wav, start, end, original_filename, index, output_dir, sample_rate):
    segment = wav[start:end]
    if isinstance(segment, torch.Tensor):
        segment = segment.cpu().numpy()
    
    # Normalize audio to 16-bit range
    segment = segment * 32767 / max(abs(segment.max()), abs(segment.min()))
    
    output_filename = f"{os.path.splitext(original_filename)[0]}_segment_{index+1}_{start}_{end}.wav"
    output_path = os.path.join(output_dir, output_filename)
    try:
        wavfile.write(output_path, sample_rate, segment.astype(np.int16))
        print(f"Saved segment {index+1} to {output_path}")
    except Exception as e:
        print(f"Error saving segment {index+1}: {str(e)}")

def process_audio_file(input_file, output_dir, sample_rate=16000):
    """
    Process an audio file to extract voice segments and save them as separate files.

    Args:
        input_file (str): Path to the input audio file.
        output_dir (str): Directory to save the extracted segments.
        sample_rate (int, optional): Sample rate for the output files. Defaults to 16000.
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    model = load_silero_vad()
    wav = read_audio(input_file)
    speech_timestamps = get_speech_timestamps(wav, model)

    for i, timestamp in enumerate(speech_timestamps):
        start, end = timestamp['start'], timestamp['end']
        extract_and_save_segment(wav, start, end, os.path.basename(input_file), i, output_dir, sample_rate)

    print(f"Extracted {len(speech_timestamps)} audio segments.")

# Usage
input_file = 'aa.wav'
output_dir = 'extracted_segments'
process_audio_file(input_file, output_dir)