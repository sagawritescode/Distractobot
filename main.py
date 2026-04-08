import rumps
import logging
import threading
import sys
from pynput import keyboard
from audio_manager import AudioManager
from transcriber import Transcriber
from llm_processor import LLMProcessor
from database import Database

# --- Monkey-patch for pynput macOS bug with media keys ---
# On macOS, pynput's darwin backend misses passing the 'injected' argument
# for media keys, which causes GlobalHotKeys to crash.
# We patch its methods to provide a default value.
# def _patched_on_press(self, key, injected=False):
#     if not injected:
#         for hotkey in self._hotkeys:
#             hotkey.press(self.canonical(key))

# def _patched_on_release(self, key, injected=False):
#     if not injected:
#         for hotkey in self._hotkeys:
#             hotkey.release(self.canonical(key))

# keyboard.GlobalHotKeys._on_press = _patched_on_press
# keyboard.GlobalHotKeys._on_release = _patched_on_release
# # ---------------------------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DistractoBotApp(rumps.App):
    def __init__(self):
        # Initialize the app with a microphone emoji and disable default quit button
        super(DistractoBotApp, self).__init__("🎙️", quit_button=None)
        self.audio_manager = AudioManager()
        self.transcriber = Transcriber()
        self.llm_processor = LLMProcessor()
        self.db = Database()
        
        # Basic UI menu with our own custom Quit button for clean exit
        self.record_button = rumps.MenuItem(title="Start Recording", callback=self.toggle_recording)
        self.cancel_button = rumps.MenuItem(title="Cancel Recording", callback=self.cancel_recording_action)
        self.quit_custom_button = rumps.MenuItem(title="Quit DistractoBot", callback=self.clean_quit)
        self.menu = [self.record_button, self.cancel_button, None, self.quit_custom_button] # None acts as a menu separator
        
        # Thread-safe flags for hotkey triggers
        self.hotkey_triggered = False
        self.cancel_hotkey_triggered = False
        
    @rumps.timer(0.1)
    def check_hotkey(self, sender):
        """Polls every 100ms to see if the global hotkey was pressed. 
        This ensures UI updates happen safely on the macOS main thread."""
        if self.hotkey_triggered:
            self.hotkey_triggered = False
            self.toggle_recording()
        if self.cancel_hotkey_triggered:
            self.cancel_hotkey_triggered = False
            self.cancel_recording_action()

    def toggle_recording(self, sender=None):
        if not self.audio_manager.is_recording:
            # Attempt to start recording FIRST
            self.audio_manager.start_recording()
            
            # Verify if it ACTUALLY started (e.g. microphone access wasn't blocked)
            if self.audio_manager.is_recording:
                self.title = "🔴"
                self.record_button.title = "Stop Recording"
            else:
                rumps.notification(title="Microphone Error", subtitle="", message="Could not access the microphone. Check Apple Security & Privacy Settings.")
        else:
            self.title = "🎙️"
            self.record_button.title = "Start Recording"
            output_file = self.audio_manager.stop_recording()
            
            if output_file:
                # Run transcription in a background thread to prevent UI freezing
                threading.Thread(target=self._process_audio, args=(output_file,)).start()

    def cancel_recording_action(self, sender=None):
        if self.audio_manager.is_recording:
            self.title = "🎙️"
            self.record_button.title = "Start Recording"
            self.audio_manager.cancel_recording()
            rumps.notification(title="DistractoBot", subtitle="Recording Cancelled", message="The recording was discarded.")
            
    def _process_audio(self, audio_file):
        # Phase 3: Speech to Text
        text = self.transcriber.transcribe(audio_file)
        if text:
            logging.info(f"\n{'='*40}\n✅ Transcribed Text: {text}\n{'='*40}")
            rumps.notification(title="DistractoBot \u2705", subtitle="Transcription Complete", message=text)
            
            # Phase 4: Intent Extraction via Ollama
            analysis = self.llm_processor.analyze_thought(text)
            if analysis:
                intent_msg = f"Intent: {analysis.get('intent')}\nSource: {analysis.get('source')}\nSummary: {analysis.get('summary')}"
                logging.info(f"\n{'='*40}\n🧠 LLM Analysis:\n{intent_msg}\n{'='*40}")
                
                # Pop-up notification for the intent
                title_text = f"Logged: {analysis.get('intent', 'Thought')}"
                rumps.notification(title=title_text, subtitle=analysis.get('source', ''), message=analysis.get('summary', ''))
                
                # Phase 5: Store to SQLite Database
                self.db.add_thought(
                    transcription=text,
                    intent=analysis.get('intent', ''),
                    source=analysis.get('source', ''),
                    summary=analysis.get('summary', '')
                )
            
    def on_hotkey(self):
        logging.info("Global hotkey pressed!")
        self.hotkey_triggered = True

    def on_cancel_hotkey(self):
        logging.info("Cancel hotkey pressed!")
        self.cancel_hotkey_triggered = True

    def clean_quit(self, sender):
        """Called when the user clicks 'Quit DistractoBot'. Ensures we don't leave zombie audio streams."""
        logging.info("Quitting DistractoBot cleanly...")
        if self.audio_manager.is_recording:
            self.audio_manager.stop_recording()
        rumps.quit_application()

def main():
    app = DistractoBotApp()
    
    # Define global hotkeys: Command+Option+R for record/stop, Command+Option+C for cancel
    hotkey = keyboard.GlobalHotKeys({
        '<cmd>+<alt>+r': app.on_hotkey,
        '<cmd>+<alt>+c': app.on_cancel_hotkey
    })
    # Start listening to hotkeys in a background thread
    hotkey.start()
    
    logging.info("Starting DistractoBot Menu Bar app...")
    logging.info("Press Cmd+Option+R or click the menu bar icon (🎙️) to toggle recording.")
    logging.info("Press Cmd+Option+C or click 'Cancel Recording' to discard.")
    
    # Needs to be called on the main thread and blocks indefinitely
    app.run()

if __name__ == "__main__":
    main()
