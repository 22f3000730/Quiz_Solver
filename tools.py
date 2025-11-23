import requests
import base64
import logging
from playwright.sync_api import sync_playwright
import threading
import speech_recognition as sr
from pydub import AudioSegment
import io
import tempfile
import os
from bs4 import BeautifulSoup

import sys
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def run_python_code(code: str) -> str:
    """
    Executes the given Python code and returns the standard output.
    Useful for data analysis, calculations, and processing CSV files.
    The code should print the final result to stdout.
    Pre-installed libraries: pandas, numpy, requests, etc.
    """
    try:
        logger.info("Executing Python code...")
        logger.info(f"Code:\n{code}")
        
        # Create a buffer to capture stdout
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        # Execution context
        local_scope = {
            "pd": pd,
            "np": np,
            "requests": requests,
            "io": io
        }
        
        try:
            exec(code, {}, local_scope)
        except Exception as exec_error:
            return f"Error executing code: {exec_error}"
        finally:
            sys.stdout = old_stdout
            
        output = redirected_output.getvalue()
        logger.info(f"Code Output:\n{output}")
        return output if output.strip() else "Code executed successfully but produced no output. Did you forget to print the result?"
        
    except Exception as e:
        logger.error(f"System error during code execution: {e}")
        return f"System error: {e}"


def download_file_as_base64(url: str) -> str:
    """
    Downloads a file from a URL and returns its content as a base64 encoded string.
    Useful when the answer requires a file attachment or CSV data.
    """
    try:
        logger.info(f"Downloading file from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Return the base64 encoded content
        b64_content = base64.b64encode(response.content).decode('utf-8')
        
        # Also log the actual content if it's text (CSV, etc.)
        try:
            text_content = response.content.decode('utf-8')
            logger.info(f"File content (first 200 chars): {text_content[:200]}")
        except:
            logger.info(f"Binary file downloaded, size: {len(response.content)} bytes")
            
        return b64_content
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return f"Error downloading file: {e}"

def fetch_page_text(url: str) -> str:
    """
    Fetches the text content of a URL using a headless browser to handle dynamic content.
    """
    try:
        logger.info(f"Fetching page text from: {url}")
        
        if not url.startswith("http"):
            return f"Error: URL must be absolute. Received: {url}"
            
        result = {}
        
        def run_playwright():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    html_content = page.content()
                    browser.close()
                    
                    # Parse with BS4
                    soup = BeautifulSoup(html_content, 'html.parser')
                    text_content = soup.get_text(separator='\n', strip=True)
                    
                    links = []
                    for a in soup.find_all('a', href=True):
                        links.append(f"Link: [{a.get_text(strip=True)}]({a['href']})")
                    
                    audio_sources = []
                    for audio in soup.find_all('audio'):
                        if audio.get('src'):
                            audio_sources.append(f"Audio: {audio['src']}")
                        for source in audio.find_all('source', src=True):
                            audio_sources.append(f"Audio: {source['src']}")
                            
                    result["content"] = text_content + "\n\n--- Extracted Links & Media ---\n" + "\n".join(links + audio_sources)
            except Exception as e:
                result["error"] = str(e)
        
        thread = threading.Thread(target=run_playwright)
        thread.start()
        thread.join()
        
        if "error" in result:
            logger.error(f"Error fetching page: {result['error']}")
            return f"Error fetching page: {result['error']}"
            
        content = result.get("content", "")
        logger.info(f"Fetched content (first 100 chars): {content[:100]}")
        return content
    except Exception as e:
        logger.error(f"Error fetching page: {e}")
        return f"Error fetching page: {e}"

def transcribe_audio(url: str) -> str:
    """
    Downloads an audio file from a URL and transcribes it using Google Speech Recognition.
    Supports MP3, WAV, etc.
    """
    try:
        logger.info(f"Transcribing audio from: {url}")
        
        if not url.startswith("http"):
             return f"Error: URL must be absolute. Received: {url}"

        response = requests.get(url)
        response.raise_for_status()
        
        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            
        # Convert to WAV if needed (using pydub)
        try:
            audio_content = io.BytesIO(response.content)
            audio = AudioSegment.from_file(audio_content)
            audio.export(temp_wav_path, format="wav")
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return f"Error converting audio: {e}"
            
        # Transcribe
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            
        logger.info(f"SPEECH RECOGNITION OUTPUT: {text}")
        
        # Clean up
        os.remove(temp_wav_path)
        
        return text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return f"Error transcribing audio: {e}"
