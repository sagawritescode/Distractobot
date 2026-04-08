import requests
import json
import logging
from typing import Dict, Optional

class LLMProcessor:
    def __init__(self, model_name="gemma4:e4b"):
        """
        Connects to a local Ollama instance. 
        Used 'gemma4:e4b' as it is the available model on this system.
        """
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        logging.info(f"Initialized LLM Processor with model: {self.model_name}")

    def analyze_thought(self, text: str) -> Optional[Dict[str, str]]:
        if not text or len(text) < 2:
            return None
            
        logging.info("Sending text to Ollama for intent analysis...")
        
        system_prompt = (
            "You are an assistant that categorizes a user's transcribed audio thoughts or distractions. "
            "Analyze the text and figure out the intent, the context/source of the thought, and a short summary. "
            "If the thought is just noise, categorize it as 'Noise'. "
            "Priority Intent Detection: If the user explicitly states an action (e.g., 'I want to log a todo task', 'save this idea', 'add a reminder', 'log a distraction', 'I wish I could'), "
            "extract that specific intent (e.g., 'Task' for todo, 'Idea' for idea, 'Reminder' for reminder, 'Random Thought' for distraction, 'Wishlist' for 'I wish I could'). "
            "Source Extraction (CRITICAL): Identify the specific person, app, channel, website, or activity that triggered this thought. "
            "- If a name is mentioned (e.g., 'Aman recommended', 'Met Sarah'), the source MUST be that person (e.g., 'Friend: Aman'). "
            "- If a platform is mentioned (e.g., 'WhatsApp Parallel Cinema Club', 'YouTube', 'Telegram'), use it. "
            "- Avoid 'Unknown' at all costs if any context exists. "
            "Respond ONLY with a valid JSON object matching this schema exactly:\n"
            "{\n"
            "  \"intent\": \"Short category (e.g., Task, Idea, Random Thought, Reminder, Note, Wishlist)\",\n"
            "  \"source\": \"Specific person, app, channel, or activity (e.g., 'Friend: Aman', 'WhatsApp: Parallel Cinema Club', 'Coding', 'Research')\",\n"
            "  \"summary\": \"A 1-sentence summary of the thought\"\n"
            "}"
        )

        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": text,
            "stream": False,
            "format": "json" # Ollama natively supports enforcing JSON format!
        }

        response_text = ""
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            response_text = data.get("response", "{}")
            
            # Parse the structured JSON returned by Ollama
            parsed = json.loads(response_text)
            return parsed
            
        except requests.exceptions.ConnectionError:
            logging.error("Failed to connect to Ollama. Make sure Ollama app is running locally!")
            return None
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON from Ollama response: {response_text}")
            return None
        except Exception as e:
            logging.error(f"LLM analysis failed: {e}")
            return None
