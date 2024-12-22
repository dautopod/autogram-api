from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import openai
import json
import os
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "chrome-extension://oobgghfnikgdjofecgkadooeinfakdnk"}})  # Enable CORS for all routes

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

system_prompt = "You are an assistant expert at responding to group chat messages. The text is copied from WhatsApp's messages in a group chat. Analyze the text and understand all the messages in the chat and provide an appropriate response to those messages. For example if people in the group are wishing someone for their birthday or anniversary or any achievement, respond with a well formed short message for the same. Always return only one response message for the latest personal activity. Return this message as json where the key of the message is 'message'"

def extract_text_with_format(html_content):
    """
    Extracts text from HTML while retaining its display format.

    Args:
        html_content (str): HTML content as a string.

    Returns:
        str: Plain text extracted from HTML while preserving line breaks and spaces.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Replace <br> and <p> tags with newlines for formatting
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.insert_before("\n")
        p.append("\n")
    
    # Get text while retaining display format
    formatted_text = soup.get_text(separator=' ')
    return formatted_text.strip()

def call_openai_api(extracted_text):
    """
    Calls OpenAI's Chat Completions API with the extracted text and a prompt.

    Args:
        extracted_text (str): Text extracted from HTML.

    Returns:
        str: Response from OpenAI API.
    """
    try:
        # Combine the prompt and extracted text
        input_text = f"{extracted_text}"
        
        response = openai.chat.completions.create(
        model="gpt-4o",
        messages= [
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": system_prompt
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": input_text
                }
            ]
            }
        ])
        raw_response=response.choices[0].message.content.strip()

        # Parse the JSON-formatted string
        if raw_response.startswith("```json"):
            raw_response = raw_response.replace("```json", "").replace("```", "").strip()
        
        print(raw_response)
        # Load it as JSON
        parsed_response = json.loads(raw_response)
        return parsed_response.get("message", "Response key not found in the output.")
    except Exception as e:
        return f"Error communicating with OpenAI API: {str(e)}"

@app.route('/process-html', methods=['POST'])
def process_html():
    """
    API endpoint to extract text from HTML, send it to OpenAI, and return the response.

    Request Body:
        {
            "html": "<html_part>"
        }

    Returns:
        JSON: OpenAI response.
    """
    try:
        data = request.json
        html_content = data.get("html")
        if not html_content:
            return jsonify({"error": "HTML content is required"}), 400

        # Extract text from HTML
        extracted_text = extract_text_with_format(html_content)

        # Call OpenAI API with extracted text
        openai_response = call_openai_api(extracted_text)

        return jsonify({"response": openai_response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Use PORT from environment or default to 5000
    app.run(host='0.0.0.0', port=port)
