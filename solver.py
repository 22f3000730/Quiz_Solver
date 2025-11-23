import asyncio
import json
import logging
import requests
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from agent import get_agent

logger = logging.getLogger(__name__)

async def solve_quiz(initial_url: str, email: str, secret: str):
    logger.info(f"Starting quiz solver workflow for {email}")
    
    current_url = initial_url
    
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            while current_url:
                # Generate a NEW session ID for each task/URL to keep memory clean
                import uuid
                session_id = str(uuid.uuid4())
                logger.info(f"Started new agent session for {current_url}: {session_id}")
                
                logger.info(f"Navigating to {current_url}")
                await page.goto(current_url)
                
                # Wait for content
                await page.wait_for_selector("body")
                
                # Extract content
                # Get full HTML to parse links and media
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract text
                text_content = soup.get_text(separator='\n', strip=True)
                
                # Extract links and media to append to context
                links = []
                for a in soup.find_all('a', href=True):
                    links.append(f"Link: [{a.get_text(strip=True)}]({a['href']})")
                
                audio_sources = []
                for audio in soup.find_all('audio'):
                    if audio.get('src'):
                        audio_sources.append(f"Audio: {audio['src']}")
                    for source in audio.find_all('source', src=True):
                        audio_sources.append(f"Audio: {source['src']}")
                
                # Combine into a rich context
                content = text_content + "\n\n--- Extracted Links & Media ---\n" + "\n".join(links + audio_sources)
                
                # If the content is empty or loading, wait a bit
                if not content.strip():
                    await asyncio.sleep(1)
                    content = await page.evaluate("document.body.innerText")
                
                logger.info(f"Extracted content (first 100 chars): {content[:100]}")
                
                # Use agent to solve (initialize here if needed, but we use get_agent() outside if we wanted persistent agent object, 
                # but we want fresh memory per task, so we rely on session_id)
                agent = get_agent()
                
                prompt = f"""
You are a quiz solver agent. 
Current Page URL: {current_url}

Page Content:
---
{content}
---

Your goal is to solve the task on this page.

GUIDELINES:
1. **Analyze**: Read the content to understand the problem.
2. **Tools**: You have tools for:
   - `fetch_page_text(url)`: Scraping web pages (REQUIRED for hidden answers).
   - `transcribe_audio(url)`: Transcribing audio files.
   - `download_file_as_base64(url)`: Downloading files.
   - `run_python_code(code)`: Executing Python code for data analysis/math.

3. **Strategy**:
   - If the task requires finding hidden info, scrape the linked page.
   - If the task requires math or data analysis (e.g. CSV), you CAN use `run_python_code` to write a script. If you are doing this return the python code in the JSON object titled "python_code", No extra explanations required. After which the results of the python code will be given to you and you shall format the json for submitting it.
   - If the task is simple, you can solve it directly.

4. **Output**:
   - Return ONLY a JSON object with the answer.

Required JSON format:
{{
    "answer_payload": {{"email": "...", "secret": "...", "url": "...", "answer": "..."}},
    "submit_url": "...",
    "reasoning": "..."
}}
"""
                
                # Run agent with session_id for memory
                response = agent.run(prompt, session_id=session_id)
                
                logger.info(f"LLM Response: {response.content}")
                
                # Parse response
                try:
                    response_text = response.content
                    logger.info(f"Raw LLM Response: {response_text}")
                    
                    # Robust JSON extraction using regex
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
                    else:
                        # Fallback to cleaning markdown
                        if "```json" in response_text:
                            response_text = response_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_text:
                            response_text = response_text.split("```")[1].split("```")[0].strip()
                        
                    result = json.loads(response_text)
                    
                    answer_payload = result.get("answer_payload")
                    submit_url = result.get("submit_url")
                    
                    if not answer_payload or not submit_url:
                        logger.error("Agent failed to provide answer_payload or submit_url")
                        break
                    
                    # Resolve relative URL
                    submit_url = urljoin(current_url, submit_url)
                        
                    logger.info(f"Solved. Submitting to {submit_url}")
                    
                    # Submit answer
                    submission_response = submit_answer(submit_url, answer_payload)
                    
                    logger.info(f"Submission Response: {json.dumps(submission_response, indent=2)}")
                    
                    if submission_response.get("correct"):
                        logger.info("Answer correct!")
                        next_url = submission_response.get("url")
                        if next_url:
                            current_url = next_url
                        else:
                            logger.info("Quiz completed!")
                            break
                    else:
                        logger.warning(f"Answer incorrect: {submission_response.get('reason')}")
                        # Retry logic could go here
                        break
                        
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse agent response: {response.content}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in solver loop: {e}")
        finally:
            await browser.close()

def submit_answer(submit_url, payload):
    try:
        logger.info(f"Submitting answer to {submit_url} with payload: {json.dumps(payload, indent=2)}")
        response = requests.post(submit_url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Submission failed: {e}")
        return {"correct": False, "reason": str(e)}
