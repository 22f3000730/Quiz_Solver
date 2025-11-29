import requests
import base64
import logging
from playwright.sync_api import sync_playwright
import threading
import speech_recognition as sr
from pydub import AudioSegment
import io
import tempfile
import sys
import os
import pandas as pd
import numpy as np
import speech_recognition as sr
from bs4 import BeautifulSoup
import pydub
from pydub import AudioSegment
import pypdf
import zipfile
import duckdb
from PIL import Image
import json

logger = logging.getLogger(__name__)

def run_python_code(code: str) -> str:
    """
    Executes Python code and returns the output.
    """
    try:
        logger.info("Executing Python code...")
        
        # Robustly extract code from markdown blocks if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
            
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
            "io": io,
            "sr": sr,
            "pydub": pydub,
            "sys": sys,
            "os": os,
            "BeautifulSoup": BeautifulSoup,
            "pypdf": pypdf,
            "zipfile": zipfile,
            "duckdb": duckdb,
            "Image": Image
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

def execute_python(code: str) -> str:
    """
    Executes Python code and returns the output.
    Use this for math, data analysis (pandas, numpy, duckdb), and file processing.
    """
    return run_python_code(code)



def read_pdf(url: str) -> str:
    """
    Downloads a PDF from a URL and extracts its text content.
    """
    try:
        logger.info(f"Reading PDF from: {url}")
        if not url.startswith("http"):
             return f"Error: URL must be absolute. Received: {url}"
             
        response = requests.get(url)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(response.content)
            temp_pdf_path = temp_pdf.name
            
        text = ""
        try:
            reader = pypdf.PdfReader(temp_pdf_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            return f"Error reading PDF: {e}"
        finally:
            os.remove(temp_pdf_path)
            
        return text[:5000] # Truncate if too long to avoid context overflow
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return f"Error downloading PDF: {e}"

def read_zip(url: str) -> str:
    """
    Downloads a ZIP file from a URL, lists its contents, and extracts text from small files.
    """
    try:
        logger.info(f"Reading ZIP from: {url}")
        if not url.startswith("http"):
             return f"Error: URL must be absolute. Received: {url}"
             
        response = requests.get(url)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            temp_zip.write(response.content)
            temp_zip_path = temp_zip.name
            
        result = "ZIP Contents:\n"
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    result += f"- {file_info.filename} ({file_info.file_size} bytes)\n"
                    # If it's a small text file, try to read it
                    if file_info.file_size < 10000 and not file_info.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        try:
                            with zip_ref.open(file_info) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                result += f"  Content: {content[:500]}\n"
                        except:
                            pass
        except Exception as e:
            return f"Error reading ZIP: {e}"
        finally:
            os.remove(temp_zip_path)
            
        return result
    except Exception as e:
        logger.error(f"Error downloading ZIP: {e}")
        return f"Error downloading ZIP: {e}"

def search_history(query: str) -> str:
    """
    Searches the history of solved quizzes for a given query (e.g., a previous URL).
    Returns the answer if found.
    """
    try:
        history_file = "history.jsonl"
        if not os.path.exists(history_file):
            return "No history found."
            
        results = []
        with open(history_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if query in str(entry):
                        results.append(str(entry))
                except:
                    pass
        
        if results:
            return "\n".join(results)
        return "No matching history found."
    except Exception as e:
        return f"Error searching history: {e}"




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
            
        # Transcribe using local Whisper (tiny model)
        # This runs entirely on-device (CPU/GPU) and does not make external API calls.
        import whisper
        
        # Load model (downloads once if not cached)
        model = whisper.load_model("tiny")
        result = model.transcribe(temp_wav_path)
        text = result["text"]
            
        logger.info(f"WHISPER OUTPUT: {text}")
        
        # Clean up
        os.remove(temp_wav_path)
        
        return text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return f"Error transcribing audio: {e}"

def understand_image(url: str, prompt: str = "Describe this image in detail") -> str:
    """
    Analyzes an image from a URL using the agent's vision capabilities (via API).
    Returns a description of the image.
    """
    try:
        logger.info(f"Analyzing image from: {url}")
        
        if os.path.exists(url):
            # It's a local file, convert to data URI
            try:
                with open(url, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    # Determine mime type based on extension, default to jpeg
                    mime_type = "image/jpeg"
                    if url.lower().endswith(".png"):
                        mime_type = "image/png"
                    elif url.lower().endswith(".gif"):
                        mime_type = "image/gif"
                    elif url.lower().endswith(".webp"):
                        mime_type = "image/webp"
                    
                    url = f"data:{mime_type};base64,{encoded_string}"
            except Exception as e:
                return f"Error reading local image file: {e}"

        if not url.startswith("http") and not url.startswith("data:"):
             return f"Error: URL must be absolute (http/https), a data URI, or a valid local file path. Received: {url[:50]}..."
             
        api_key = os.getenv("AI_TOKEN") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: AI_TOKEN not found."

        # Use OpenRouter API to analyze the image
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.0-flash-lite-001",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": url}}
                    ]
                }
            ]
        }
        
        response = requests.post("https://aipipe.org/openrouter/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        description = result['choices'][0]['message']['content']
        
        logger.info(f"IMAGE ANALYSIS OUTPUT: {description}")
        return description
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return f"Error analyzing image: {e}"

def call_api(url: str, method: str = "GET", headers: dict = None, json_data: dict = None) -> str:
    """
    Makes an HTTP request to an external API.
    Useful for sourcing data from APIs as required by the quiz.
    """
    try:
        logger.info(f"Calling API: {method} {url}")
        
        if not url.startswith("http"):
             return f"Error: URL must be absolute. Received: {url}"
             
        response = requests.request(method, url, headers=headers, json=json_data)
        
        try:
            return json.dumps(response.json(), indent=2)
        except:
            return response.text
            
    except Exception as e:
        logger.error(f"Error calling API: {e}")
        return f"Error calling API: {e}"




def fetch_page_text(url: str) -> dict:
    """
    Fetches the text content of a web page using Playwright.
    Also extracts links, audio sources, and takes a screenshot if visual elements are present.
    
    Args:
        url (str): The URL of the page to fetch.
    
    Returns:
        dict: A dictionary containing the 'content' (text + links/media) or 'error'.
    """
    result = {}
    
    try:
        logger.info(f"Fetching page text from: {url}")
        
        if not url.startswith("http"):
            result["error"] = f"Error: URL must be absolute. Received: {url}"
            return result
            
        def run_playwright():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    html_content = page.content()
                    
                    # Screenshot Logic
                    images = []
                    try:
                        has_visuals = page.evaluate("() => document.querySelectorAll('canvas, img').length > 0")
                        if has_visuals:
                            import uuid
                            unique_id = str(uuid.uuid4())[:8]
                            screenshot_path = f"/tmp/screenshot_{unique_id}.jpg"
                            page.screenshot(path=screenshot_path, full_page=True, type='jpeg', quality=50)
                            images.append(f"Image: [Page Screenshot]({screenshot_path})")
                            logger.info(f"Visual elements detected. Saved screenshot to {screenshot_path}")
                    except Exception as e:
                        logger.warning(f"Error handling screenshot in fetch_page_text: {e}")
                    
                    browser.close()
                    
                    # Parse with BS4
                    soup = BeautifulSoup(html_content, 'html.parser')
                    text_content = soup.get_text(separator='\n', strip=True)
                    
                    links = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        links.append(f"Link: [{a.get_text(strip=True)}]({href})")
                    
                    audio_sources = []
                    for audio in soup.find_all('audio'):
                        if audio.get('src'):
                            audio_sources.append(f"Audio: {audio['src']}")
                        for source in audio.find_all('source', src=True):
                            audio_sources.append(f"Audio: {source['src']}")

                    result["content"] = text_content + "\n\n--- Extracted Links & Media ---\n" + "\n".join(links + audio_sources + images)

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


def fetch_page_scripts(url: str) -> str:
    """
    Fetches only the scripts (inline and src) from a web page.
    Useful when the page mentions embedded logic or hidden code.
    """
    result = {}
    try:
        logger.info(f"Fetching page scripts from: {url}")
        
        if not url.startswith("http"):
            return f"Error: URL must be absolute. Received: {url}"

        def run_playwright():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    html_content = page.content()
                    browser.close()
                    
                    soup = BeautifulSoup(html_content, 'html.parser')
                    scripts = []
                    for script in soup.find_all('script'):
                        if script.get('src'):
                            scripts.append(f"Script Source: {script['src']}")
                        elif script.string and script.string.strip():
                            scripts.append(f"Inline Script: {script.string.strip()[:2000]}")
                    
                    result["content"] = "--- Extracted Scripts ---\n" + "\n".join(scripts)
            except Exception as e:
                result["error"] = str(e)
        
        thread = threading.Thread(target=run_playwright)
        thread.start()
        thread.join()
        
        if "error" in result:
            return f"Error fetching scripts: {result['error']}"
            
        return result.get("content", "No scripts found.")
    except Exception as e:
        return f"Error fetching scripts: {e}"

