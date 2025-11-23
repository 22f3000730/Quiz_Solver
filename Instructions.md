# API Endpoint Quiz Tasks


Your API endpoint will receive a POST request with a JSON payload containing your email, secret and a quiz URL, like this:

{
  "email": "your email", // Student email ID
  "secret": "your secret", // Student-provided secret
  "url": "https://example.com/quiz-834" // A unique task URL
  // ... other fields
}

Your endpoint must:

    Verify the secret matches what you provided in the Google Form.
    Respond with a HTTP 200 JSON response if the secret matches. Respond with HTTP 400 for invalid JSON and HTTP 403 for invalid secrets. (We’ll check this with incorrect payloads.)
    Visit the url and solve the quiz on that page.

The quiz page will be a human-readable JavaScript-rendered HTML page with a data-related task.

Here’s a sample quiz page (not the actual quiz you will receive). (This requires DOM execution, hence a headless browser.)

<div id="result"></div>

<script>
  document.querySelector("#result").innerHTML = atob(`
UTgzNC4gRG93bmxvYWQgPGEgaHJlZj0iaHR0cHM6Ly9leGFtcGxlLmNvbS9kYXRhLXE4MzQucGRmIj5
maWxlPC9hPi4KV2hhdCBpcyB0aGUgc3VtIG9mIHRoZSAidmFsdWUiIGNvbHVtbiBpbiB0aGUgdGFibG
Ugb24gcGFnZSAyPwoKUG9zdCB5b3VyIGFuc3dlciB0byBodHRwczovL2V4YW1wbGUuY29tL3N1Ym1pd
CB3aXRoIHRoaXMgSlNPTiBwYXlsb2FkOgoKPHByZT4KewogICJlbWFpbCI6ICJ5b3VyLWVtYWlsIiwK
ICAic2VjcmV0IjogInlvdXIgc2VjcmV0IiwKICAidXJsIjogImh0dHBzOi8vZXhhbXBsZS5jb20vcXV
pei04MzQiLAogICJhbnN3ZXIiOiAxMjM0NSAgLy8gdGhlIGNvcnJlY3QgYW5zd2VyCn0KPC9wcmU+`);
</script>

Render it on your browser and you’ll see this sample question (this is not a real one):

    Q834. Download file. What is the sum of the “value” column in the table on page 2?

    Post your answer to https://example.com/submit with this JSON payload:

    {
      "email": "your email",
      "secret": "your secret",
      "url": "https://example.com/quiz-834",
      "answer": 12345 // the correct answer
    }

Your script must follow the instructions and submit the correct answer to the specified endpoint within 3 minutes of the POST reaching our server. The quiz page always includes the submit URL to use. Do not hardcode any URLs.

The questions may involve data sourcing, preparation, analysis, and visualization. The "answer" may need to be a boolean, number, string, base64 URI of a file attachment, or a JSON object with a combination of these. Your JSON payload must be under 1MB.

The endpoint will respond with a HTTP 200 and a JSON payload indicating whether your answer is correct and may include another quiz URL to solve. For example:

{
  "correct": true,
  "url": "https://example.com/quiz-942",
  "reason": null
  // ... other fields
}

{
  "correct": false,
  "reason": "The sum you provided is incorrect."
  // maybe with no new url provided
}

If your answer is wrong:

    you are allowed to re-submit, as long as it is still within 3 minutes of the original POST reaching our server. Only the last submission within 3 minutes will be considered for evaluation.
    you may receive the next url to proceed to. If so, you can choose to skip to that URL instead of re-submitting to the current one.

If your answer is correct, you will receive a new url to solve unless the quiz is over.

When you receive a new url, your script must visit the url and solve the quiz on that page. Here’s a sample sequence:

    We send you to url: https://example.com/quiz-834
    You solve it wrongly. You get url: https://example.com/quiz-942 and solve it.
    You solve it wrongly. You re-submit. Now it’s correct and you get url: https://example.com/quiz-123 and solve it.
    You solve it correctly and get no new URL, ending the quiz.

Here are some types of questions you can expect:

    Scraping a website (which may require JavaScript) for information
    Sourcing from an API (with API-specific headers provided where required)
    Cleansing text / data / PDF / … you retrieved
    Processing the data (e.g. data transformation, transcription, vision)
    Analysing by filtering, sorting, aggregating, reshaping, or applying statistical / ML models. Includes geo-spatial / network analysis
    Visualizing by generating charts (as images or interactive), narratives, slides

The tech stack should be entirely made using python language. Please dont make it super complex, just make something that works.

Also all the AI calls are to be made via this documentaion:
OpenRouter API

GET /openrouter/*: Proxy requests to OpenRouter

Example: List Openrouter models

curl https://aipipe.org/openrouter/v1/models -H "Authorization: Bearer $AIPIPE_TOKEN"

Response:

{
  "data": [
    {
      "id": "google/gemini-2.5-pro-preview-03-25",
      "name": "Google: Gemini 2.5 Pro Preview"
      // ...
    }
  ]
}

Example: Make a chat completion request

curl https://aipipe.org/openrouter/v1/chat/completions \
  -H "Authorization: Bearer $AIPIPE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "google/gemini-2.0-flash-lite-001", "messages": [{ "role": "user", "content": "What is 2 + 2?" }] }'

Response contains:

{ "choices": [{ "message": { "role": "assistant", "content": "..." } }] }

The token is in the .env file as AI_TOKEN, make sure that you dont create garbage, everything should be working.