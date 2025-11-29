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
                
                # Check for email input and fill it if present
                # Many quizzes require entering the email to see the question
                try:
                    email_input = await page.query_selector("input[type='email'], input[name='email'], input[placeholder*='email']")
                    if email_input:
                        logger.info(f"Found email input, filling with {email}")
                        await email_input.fill(email)
                        await email_input.press("Enter")
                        # Wait for potential update/navigation
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2) # Extra buffer for JS updates
                except Exception as e:
                    logger.warning(f"Error handling email input: {e}")
                
                # Extract content
                
                # Extract content
                # Get full HTML to parse links and media
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract text
                text_content = soup.get_text(separator='\n', strip=True)
                
                # Check for <base> tag
                base_url = current_url
                base_tag = soup.find('base', href=True)
                if base_tag:
                    base_url = urljoin(current_url, base_tag['href'])
                    logger.info(f"Found <base> tag, using base URL: {base_url}")
                
                # Extract links and media to append to context
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(base_url, href)
                    links.append(f"Link: [{a.get_text(strip=True)}]({full_url})")
                
                audio_sources = []
                for audio in soup.find_all('audio'):
                    if audio.get('src'):
                        src = audio['src']
                        full_src = urljoin(base_url, src)
                        audio_sources.append(f"Audio: {full_src}")
                    for source in audio.find_all('source', src=True):
                        src = source['src']
                        full_src = urljoin(base_url, src)
                        audio_sources.append(f"Audio: {full_src}")
                
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src:
                        full_src = urljoin(base_url, src)
                        alt = img.get('alt', 'No description')
                        images.append(f"Image: [{alt}]({full_src})")
                
                # Conditional Screenshot Logic
                # If there are visual elements (canvas or images), capture the page state to a file.
                # This allows the agent to "see" the page if needed, without cluttering context with base64.
                try:
                    has_visuals = await page.evaluate("() => document.querySelectorAll('canvas, img').length > 0")
                    if has_visuals:
                        screenshot_path = f"/tmp/screenshot_{session_id}.jpg"
                        await page.screenshot(path=screenshot_path, full_page=True, type='jpeg', quality=50)
                        images.append(f"Image: [Page Screenshot]({screenshot_path})")
                        logger.info(f"Visual elements detected. Saved screenshot to {screenshot_path}")
                    else:
                        logger.info("No significant visual elements detected. Skipping screenshot.")
                except Exception as e:
                    logger.warning(f"Error handling screenshot: {e}")
                
                # Combine into a rich context
                content = text_content + "\n\n--- Extracted Links & Media ---\n" + "\n".join(links + audio_sources + images)
                
                # If the content is empty or loading, wait a bit
                if not content.strip():
                    await asyncio.sleep(1)
                    content = await page.evaluate("document.body.innerText")
                
                logger.info(f"Extracted content (first 100 chars): {content[:100]}")
                
                # Use agent to solve (initialize here if needed, but we use get_agent() outside if we wanted persistent agent object, 
                # but we want fresh memory per task, so we rely on session_id)
                agent = get_agent()
                
                prompt = f"""
You are a highly capable Quiz Solver Agent.
Current Page URL: {current_url}

Page Content:
---
{content.replace("{", "{{").replace("}", "}}")}
---

**GOAL**
Solve the task on the current page.

**GUIDELINES**
- **Conciseness**: Plan and explain in **2-3 lines maximum**.
- **Action**: Respond **IMMEDIATELY** with a tool call or the final JSON. **DO NOT** output conversational text or plans like "I need to...". Just run the code.

**TOOL USAGE**
- **Secret Codes**: Return exactly as requested (no extra spaces).
- **Media**: (this is the order in which you should understand the contents of the page)
  - Audio: Use `transcribe_audio(url)`.
  - Images: Use `understand_image(url, prompt)`. (if /tmp is involved its stored locally and not in the url)
  - PDF/ZIP: Use `read_pdf(url)` or `read_zip(url)`.
  - History: Use `search_history(query)` with the previous quiz URL.
  - API: Use `call_api(url)` only if explicitly mentioned to call an api and not otherwise.
- **Files**:
  - **Local**: Paths starting with `/tmp/` are local. Pass them directly to tools.
  - **Relative URLs**: Resolve against the Current Page URL using `urllib.parse.urljoin`.
- **Scripts**: Use `fetch_page_scripts(url)` **ONLY** if the page explicitly asks to "run javascript" or "embedded javascript".
- **Stuck?**: If content is unchanged or ambiguous, **FIRST** **CRITICAL** verify visually with `understand_image`. Only then consider scripts.

**DATA ANALYSIS**
- **Process**:
  1. **Inspect**: Download/read the file and print `df.head()` and `df.columns`. **STOP**.
  2. **Analyze**: Read the inspection output, *then* write new code to solve.
- **Downloads**: Always check `status_code == 200`. Save to `/tmp`.
- **CSV**: Use `header=None` for number lists.
- **Output**: Calculate the final answer in Python. Print **ONLY** the result. Do not print large dataframes.

**DIRECT ANSWER**
If the answer is in the text, provide it directly. 
6. If sometimes the answer is wrong when previously you submitted it in some format (integer/string/float) try submitting it in another format.
7. If the task asks for email or uses an example email, then the email address is 22f3000730@ds.study.iitm.ac.in. You can use it if needed. But DO NOT confuse it for anything else based on your assumptions.
8. Email number for '22f3000730@ds.study.iitm.ac.in' is 45519 using sha1 hash. You can use it if needed. But DO NOT confuse it for anything else based on your assumptions. DO NOT assume that this is the answer unless the page explicitly states to submit it.
9. If the tasks ask for the secret, it is vjay@15
10. Screenshots are mentioned in the prompt like this: Image: [Page Screenshot](/tmp/screenshot_12345.jpg) use understand_image(/tmp/screenshot_12345.jpg, "") to understand the screenshot.
**OUTPUT**
When you have the final answer, return a JSON object with the following structure:
{{
    "answer_payload": {{"email": "...", "secret": "...", "url": "...", "answer": "..."}},
    "submit_url": "...",
    "reasoning": "..."
}}
If submission url is not available, use https://tds-llm-analysis.s-anand.net/submit to submit.
"""
                
                # Run agent with session_id for memory
                max_retries = 3
                for attempt in range(max_retries):
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
                        
                        result = json.loads(response_text)
                        
                        # Check if agent returned python_code instead of final answer
                        if "python_code" in result and "answer_payload" not in result:
                            python_code = result.get("python_code")
                            logger.info(f"Agent provided Python code to execute")
                            
                            # Execute the code
                            from tools import execute_python
                            code_output = execute_python(python_code)
                            logger.info(f"Python code executed, output: {code_output[:200]}...")
                            
                            # Ask agent to format final JSON with code output
                            followup_prompt = f"""
The Python code executed successfully. Output:

{code_output.replace("{", "{{").replace("}", "}}")}

Now return the final JSON for submission:

{{
    "answer_payload": {{"email": "{email}", "secret": "{secret}", "url": "{current_url}", "answer": <extract from output above>}},
    "submit_url": <submit URL from original page>,
    "reasoning": <brief explanation>
}}
"""
                            response = agent.run(followup_prompt, session_id=session_id)
                            logger.info(f"LLM Follow-up Response: {response.content}")
                            
                            # Parse follow-up response
                            response_text = response.content
                            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                            if json_match:
                                response_text = json_match.group(0)
                            result = json.loads(response_text)
                        
                        answer_payload = result.get("answer_payload")
                        submit_url = result.get("submit_url")
                        
                        if not answer_payload or not submit_url:
                            logger.error("Agent failed to provide answer_payload or submit_url")
                            if attempt < max_retries - 1:
                                prompt = "Error: You must return a JSON object with 'answer_payload' and 'submit_url'. Do not return conversational text."
                                continue
                            break
                        
                        if answer_payload:
                            # Trust the LLM's payload
                            pass
                        
                        # Resolve relative URL
                        submit_url = urljoin(current_url, submit_url)
                            
                        logger.info(f"Solved. Submitting to {submit_url}")
                        
                        # Submit answer
                        submission_response = submit_answer(submit_url, answer_payload)
                        
                        logger.info(f"Submission Response: {json.dumps(submission_response, indent=2)}")
                        
                        # Check for next URL first (priority over correctness for navigation)
                        next_url = submission_response.get("url")
                        is_correct = submission_response.get("correct")
                        
                        if next_url:
                            logger.info(f"Received next URL: {next_url}")
                            if not is_correct:
                                logger.warning(f"Answer was incorrect, but moving to next URL as instructed.")
                            else:
                                logger.info("Answer correct! Moving to next URL.")
                                
                            current_url = next_url
                            break # Break retry loop to process new URL
                        
                        # No new URL provided
                        if is_correct:
                            logger.info("Answer correct! No new URL provided. Quiz completed!")
                            current_url = None # Break outer loop
                            break # Break retry loop
                        else:
                            logger.warning(f"Answer incorrect: {submission_response.get('reason')}")
                            logger.info("No new URL provided. Retrying same URL in 2 seconds...")
                            await asyncio.sleep(2) 
                            # Break inner loop to refresh page and try again
                            break

                            
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse agent response: {response.content}")
                        if attempt < max_retries - 1:
                            prompt = "Error: Your response was not valid JSON. Please return ONLY a JSON object. Do not include any conversational text."
                            continue
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
