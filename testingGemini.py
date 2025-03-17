import json
import os
from google import genai
from google.genai import types

# Configuration
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")  # Get API key from environment variable
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

client = genai.Client(api_key=GOOGLE_API_KEY)
MODEL_NAME = "gemini-2.0-flash"

#SEARCH_PROMPT = "I am building a platform that gives information on all available scholarships individually for a student in Karnataka. Find me scholarships in Karnataka with its application link and last date for applying. It should be currently available as of 16th March 2025. It should contain information such as last date, application process, and eligibility in separate categories organised in a JSON format. Thus give me an exhsostive list and not just general information. If one protal has multiple scholarships, I want each one in a different entry. This is to build a database and as such i want a very exhostive list of this."
SEARCH_PROMPT = "I am building a platform that gives information on all available scholarships individually and exhostively for a student in Karnataka. So you have to find me a list of links to these websites that offer scholarships. This is just a starting point as i will later ask some other agent to go through each link individually. This give me the links only. I want ONLY A LIST OF LINKS. NOTHING ELSE. I want a very exhostive list. All of these should be available as of 16th march 2025"
def google_search(query: str) -> dict:
    """Performs a Google search using Gemini API and returns structured results."""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval)]
            )
        )
        return response # Convert response to dictionary
    except Exception as e:
        print(f"Error during API call: {e}")
        return {"error": str(e)}

def save_to_json(data: dict, filename: str):
    """Saves data to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")

if __name__ == "__main__":
    results = google_search(SEARCH_PROMPT)
    if results and "error" not in results:
        print(results)
    else:
        print("Search failed or returned an error.")
