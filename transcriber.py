import mlx_whisper
import soundfile as sf
import logging

class Transcriber:
    def __init__(self, model_repo="mlx-community/whisper-small.en-mlx"):
        """
        Initializes the transcriber. 
        On its first run, mlx_whisper will automatically download the model from Hugging Face.
        'mlx-community/whisper-small.en-mlx' is a fast, highly accurate English model that takes ~500MB of RAM.
        """
        self.model_repo = model_repo
        logging.info(f"Initialized transcriber with model: {self.model_repo}")

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes the given audio file using Apple Silicon MLX optimizations.
        """
        logging.info(f"Starting transcription for {audio_file_path}...")
        
        try:
            # Bypassing the need for 'ffmpeg' system dependency by loading the audio natively
            # mlx_whisper expects a 16kHz float32 mono numpy array.
            audio_data, samplerate = sf.read(audio_file_path, dtype='float32')
            
            # Ensure it is a 1D array
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()

            # We enforce English here for speed and accuracy
            result = mlx_whisper.transcribe(
                audio_data,
                path_or_hf_repo=self.model_repo,
                language="en"
            )
            
            text = result.get("text", "").strip()
            return text
            
        except Exception as e:
            logging.error(f"Failed to transcribe audio: {e}")
            return ""
