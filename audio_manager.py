import logging
import os
import queue
import tempfile
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

class AudioManager:
    """Manages audio recording directly to a secure temporary file."""

    def __init__(self, samplerate: int = 16000, channels: int = 1) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self.is_recording = False
        self.q: queue.Queue = queue.Queue()
        self.stream: Optional[sd.InputStream] = None
        self.output_filename: Optional[str] = None
        self.output_file: Optional[sf.SoundFile] = None
        self._writer_thread: Optional[threading.Thread] = None

    def __del__(self) -> None:
        """Ensure audio resources are cleaned up if the object is garbage collected."""
        if getattr(self, 'is_recording', False):
            self.stop_recording()

    def _callback(self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags) -> None:
        """This is called (from a separate thread) for each audio block."""
        if status:
            logging.warning(f"Audio status: {status}")
        if self.is_recording:
            # We copy the data because indata is volatile
            self.q.put(indata.copy())

    def _file_writer(self) -> None:
        """Runs in a separate thread to continuously write queued audio to disk.
        This prevents the audio callback from blocking on disk I/O and solves the RAM bloat."""
        if self.output_file is None:
            logging.error("File writer started but output_file is None.")
            return
            
        logging.debug("Background file writer thread started.")
        try:
            while self.is_recording or not self.q.empty():
                try:
                    # Block for a short time to avoid busy CPU loop when queue is empty,
                    # but allow the loop to check self.is_recording frequently.
                    data = self.q.get(timeout=0.1)
                    self.output_file.write(data)
                except queue.Empty:
                    continue
                except Exception as e:
                    logging.error(f"Error writing audio data to file: {e}")
                    break
        finally:
            logging.debug("Background file writer thread exiting.")

    def start_recording(self) -> None:
        """Starts audio recording and initializes the background disk writer."""
        if self.is_recording:
            return

        # Generate a unique temp file so we don't accidentally over-write or leak data
        temp_fw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.output_filename = temp_fw.name
        temp_fw.close() 

        self.is_recording = True
        self.q = queue.Queue() # Clear out any old data from extreme edge cases
        
        logging.info("Started recording...")

        # Initialize the output file in write mode
        self.output_file = sf.SoundFile(
            self.output_filename, 
            mode='w', 
            samplerate=self.samplerate, 
            channels=self.channels, 
            subtype='PCM_16'
        )

        try:
            self.stream = sd.InputStream(
                samplerate=self.samplerate, 
                channels=self.channels, 
                callback=self._callback
            )
            self.stream.start()
        except Exception as err:
            logging.error(f"Microphone access error! Please check Apple Security & Privacy permissions. Details: {err}")
            self.is_recording = False
            if self.output_file is not None:
                self.output_file.close()
            return

        # Start the background file writer thread
        self._writer_thread = threading.Thread(target=self._file_writer)
        self._writer_thread.start()

    def stop_recording(self) -> Optional[str]:
        """Stops the audio recording, closes files securely, and returns the path to the recorded .wav file."""
        if not self.is_recording:
            return None

        self.is_recording = False
        logging.info("Stopping recording...")

        if self.stream is not None:
            logging.debug("Stopping and closing audio stream...")
            try:
                self.stream.stop()
                self.stream.close()
                logging.debug("Audio stream stopped and closed.")
            except Exception as e:
                logging.error(f"Error closing audio stream: {e}")
            self.stream = None

        # Wait for the file writer to finish draining the queue
        if self._writer_thread is not None:
            logging.debug("Waiting for file writer thread to join...")
            self._writer_thread.join(timeout=2.0) # 2 second timeout to prevent permanent hang
            if self._writer_thread.is_alive():
                logging.warning("File writer thread did not finish in time. It might be stuck.")
            self._writer_thread = None

        if self.output_file is not None:
            logging.debug("Closing output file...")
            try:
                self.output_file.close()
                logging.debug("Output file closed.")
            except Exception as e:
                logging.error(f"Error closing output file: {e}")
            self.output_file = None

        logging.info(f"Saved audio to {self.output_filename}")
        return self.output_filename

    def cancel_recording(self) -> None:
        """Stops the audio recording, closes files securely, and discards the recorded .wav file."""
        if not self.is_recording:
            return

        self.is_recording = False
        logging.info("Canceling recording...")

        if self.stream is not None:
            logging.debug("Stopping and closing audio stream (cancel)...")
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logging.error(f"Error closing audio stream during cancel: {e}")
            self.stream = None

        # Wait for the file writer to finish draining the queue
        if self._writer_thread is not None:
            logging.debug("Waiting for file writer thread to join (cancel)...")
            self._writer_thread.join(timeout=2.0)
            self._writer_thread = None

        if self.output_file is not None:
            logging.debug("Closing output file (cancel)...")
            try:
                self.output_file.close()
            except Exception as e:
                logging.error(f"Error closing output file during cancel: {e}")
            self.output_file = None

        if self.output_filename and os.path.exists(self.output_filename):
            try:
                os.remove(self.output_filename)
                logging.info(f"Discarded audio file {self.output_filename}")
            except OSError as e:
                logging.error(f"Error discarding audio file: {e}")
            self.output_filename = None
