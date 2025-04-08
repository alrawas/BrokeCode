from flask import Flask, request, jsonify
import tempfile
from flask_cors import CORS
import os
import scipy.io.wavfile
import scipy.signal
import numpy as np
# Uncomment these for AI transcription
# import torch
# from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC

"""
OVERVIEW OF CHANGES:

Original Implementation Issues:
- Used deprecated librosa functions causing warning messages
- Lacked robust handling for different audio formats from different browsers
- Had limited debugging information

New Implementation Improvements:
- Browser-agnostic backend that works with audio from any browser
- Replaced librosa with scipy for audio processing to avoid deprecation warnings
- Enhanced audio format detection and validation
- Added detailed logging to identify browser-specific format differences
- Structured for easy AI integration
"""

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins

# Uncomment these for AI transcription
# # Configure device (GPU if available, otherwise CPU)
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# 
# # Load processor and model
# processor = Wav2Vec2Processor.from_pretrained("/home/agrfhyl/processor")
# model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
# # Load your model state dictionary if you have a custom-trained model
# state_dict = torch.load("/home/agrfhyl/model_state_dict.pth", map_location=device)
# model.load_state_dict(state_dict)
# model.to(device)
# model.eval()  # set model to evaluation mode

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """
    Handle audio transcription requests
    
    CHANGE: Complete rewrite of audio processing pipeline
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    # CHANGE: Added file size logging for debugging
    print(f"Received audio file of size: {len(audio_bytes)} bytes")
    # CHANGE: Added header inspection to identify browser-specific format differences
    print(f"File header: {audio_bytes[:10]}")
    
    try:
        # Save the uploaded file temporarily
        # CHANGE: Added .wav suffix to help scipy identify the format
        # Note: With frontend WAV conversion, this should now be consistent across browsers
        temp_audio_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio_path.write(audio_bytes)
        temp_audio_path.close()
        
        try:
            # CHANGE: Using scipy for consistent processing
            # New: Works with standardized WAV format from any browser
            sr, audio_array = scipy.io.wavfile.read(temp_audio_path.name)
            print(f"Successfully read WAV file. Sample rate: {sr}Hz")
            
            # CHANGE: Added explicit data type conversion
            # This ensures consistent processing regardless of browser-specific encoding differences
            if audio_array.dtype != 'float32':
                if audio_array.dtype == 'int16':
                    audio_array = audio_array.astype('float32') / 32768.0
                elif audio_array.dtype == 'int32':
                    audio_array = audio_array.astype('float32') / 2147483648.0
                else:
                    audio_array = audio_array.astype('float32')
            
            # CHANGE: Added explicit stereo to mono conversion
            # Different browsers might produce different channel configurations
            if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
                audio_array = audio_array.mean(axis=1)
                print("Converted stereo to mono")
                
        except Exception as e:
            # CHANGE: Improved error reporting
            raise Exception(f"Could not read WAV file: {str(e)}")

        print("here4")        
        # CHANGE: Added validation check
        # Important to verify audio data validity regardless of source browser
        if audio_array is None or sr is None:
            raise Exception("Failed to extract valid audio data")
            
        # CHANGE: Using scipy for resampling instead of librosa
        # Original: Used librosa.resample which had deprecation warnings
        # New: Uses scipy.signal.resample without warnings
        # 
        # Note: Different browsers might record at different sample rates (commonly 48kHz),
        # but our frontend conversion to 16kHz should make this step unnecessary in most cases.
        # We keep it as a safeguard.
        if sr != 16000:
            print(f"Resampling from {sr}Hz to 16000Hz")
            number_of_samples = round(len(audio_array) * 16000 / sr)
            audio_array = scipy.signal.resample(audio_array, number_of_samples)
            sr = 16000
        
        # CHANGE: Enhanced audio diagnostics to debug browser-specific differences
        print(f"Audio array shape: {audio_array.shape}, dtype: {audio_array.dtype}")
        print(f"Audio min: {audio_array.min()}, max: {audio_array.max()}, mean: {audio_array.mean()}")
        
        # Clean up the temporary file
        os.remove(temp_audio_path.name)
        
        # CHANGE: Explicit dummy response for testing
        # Works consistently regardless of which browser generated the audio
        return jsonify({"transcription": "This is a test transcription. Your audio was processed successfully!"})
        
        # Uncomment this section for AI transcription
        # # Preprocess the audio for the model
        # inputs = processor(audio_array, sampling_rate=16000, return_tensors="pt")
        # input_values = inputs.input_values.to(device)
        # attention_mask = inputs.attention_mask.to(device) if "attention_mask" in inputs else None
        #
        # # Perform transcription using the model
        # with torch.no_grad():
        #     outputs = model(input_values, attention_mask=attention_mask)
        #     logits = outputs.logits
        #
        # # Decode the transcription
        # predicted_ids = torch.argmax(logits, dim=-1)
        # transcription = processor.decode(predicted_ids[0])
        #
        # return jsonify({"transcription": transcription})
        
    except Exception as e:
        # CHANGE: Improved exception handling and reporting
        # Helpful for diagnosing browser-specific issues
        print(f"Exception: {str(e)}")
        # Try to clean up temp file if it exists
        try:
            if os.path.exists(temp_audio_path.name):
                os.remove(temp_audio_path.name)
        except:
            pass
        return jsonify({"error": f"Could not process audio: {str(e)}"}), 500

if __name__ == '__main__':
    # CHANGE: Enabled debug mode for better development experience
    app.run(host='0.0.0.0', port=5001, debug=True)