# matri/groq_utils.py

import json
import re
from groq import Groq, APIError
from django.conf import settings

def get_related_professions_groq(search_term: str, all_professions_list: list[str]) -> list[str] | None:
    """
    Uses Groq AI to find professions from all_professions_list that are related
    to the search_term.

    Args:
        search_term: The profession term entered by the user.
        all_professions_list: A list of unique professions existing in the database.

    Returns:
        A list of related professions found by Groq, or None if an API error occurs
        or the API key is missing (to signal a fallback).
        Returns an empty list if Groq runs successfully but finds no matches.
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        print("DEBUG: Groq API key not found in settings.")
        return None

    if not all_professions_list:
        print("DEBUG: No professions list provided to Groq function.")
        return []  # No professions to match against, so “successfully” return empty

    client = Groq(api_key=api_key)

    # Serialize the list of professions safely for the prompt
    professions_json_list = json.dumps(all_professions_list)

    prompt = f"""
    You are an expert in understanding job titles and professions.
    The user is searching for professions related to: "{search_term}".
    From the following list of professions: {professions_json_list}, identify ALL professions 
    in THIS EXACT LIST that are semantically similar, synonyms, are a subset/superset, or 
    are very closely related to "{search_term}".
    Return your answer ONLY as a JSON list of strings, where each string is one of the matching
    professions from the provided list. If no professions match, return an empty JSON list: [].
    Do not include any explanations; just output the JSON array.
    """

    try:
        print(f"DEBUG: Calling Groq API for search_term='{search_term}' with {len(all_professions_list)} candidate professions.")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",       # or “mixtral-8x7b-32768”
            temperature=0.2,               # more deterministic
            max_tokens=1024,
        )

        response_content = chat_completion.choices[0].message.content
        print(f"DEBUG: Groq raw response for '{search_term}': {response_content}")

        # Extract JSON array from the model’s response
        json_str = None
        if '```json' in response_content:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
            if match:
                json_str = match.group(1).strip()
        elif response_content.strip().startswith('[') and response_content.strip().endswith(']'):
            json_str = response_content.strip()
        else:
            match = re.search(r'(\[.*?\])', response_content, re.DOTALL)
            if match:
                json_str = match.group(1)

        if not json_str:
            print(f"DEBUG: Could not extract JSON from Groq response for '{search_term}'. Response = {response_content}")
            return None  # fall back

        try:
            parsed_response = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to decode JSON for '{search_term}'. Extracted string: '{json_str}'. Error: {e}")
            return None  # fall back

        if isinstance(parsed_response, list) and all(isinstance(item, str) for item in parsed_response):
            # Only keep those actually in our original list
            valid_professions = [p for p in parsed_response if p in all_professions_list]
            print(f"DEBUG: Groq identified valid professions for '{search_term}': {valid_professions}")
            return valid_professions
        else:
            print(f"DEBUG: Unexpected structure from Groq for '{search_term}': {parsed_response}")
            return None

    except APIError as e:
        print(f"ERROR: Groq APIError for '{search_term}': {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error in Groq call for '{search_term}': {e}")
        return None
