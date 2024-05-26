import streamlit as st
import random
import time
from openai import OpenAI
import json
import requests 
from typing import List, Dict
from dotenv import dotenv_values
from datetime import datetime

config = dotenv_values(".env")

# OpenAI API client setup
client = OpenAI(api_key = config.get('OPENAI_API_KEY'))

st.title("Chat with AmeriGPT")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
        "role": "system",
        "name": "WebBot",
        "content": f"""
                    You are AmeriGPT, a friendly and helpful chatbot that helps users navigate the 2024 Amerikick Internationls, an international
                    martial arts competition taking place in Atlantic City on August 15-17, 2024. Today's date is {datetime.now().strftime("%I:%M%p %A, %B %-d")}.
                    Your job is to help with questions relating to the tournament, local resturant or events, and provide users with relevant information when requested. 
                    DO NOT ANSWER ANY QUESTIONS THAT ARE INNAPROPRIATE OR UNRELATED TO THE TOURNAMENT, IF THEY ARE ASKED RESPOND WITH "I'm sorry, I can't help with that
                    I can only answer questions regarding the tournament."
                    """
        },
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Function to call restaurants API
def get_restaurants(
    keyword: str, 
) -> List[Dict[str, str]]:
    """
    Fetches a list of restaurants around a specified location using Google Places API.

    :param api_key: Google Places API key
    :param location: Latitude and longitude of the location (format: "lat,lng")
    :param radius: Radius in meters within which to search for restaurants
    :return: List of dictionaries containing restaurant details
    """
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": "39.363333, -74.439166",
        "radius": 3000,
        "type": "restaurant",
        "key": config.get('GOOGLE_PLACES_API_KEY'),
        "keyword": keyword
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    data = response.json()

    restaurants = []
    for place in data.get("results", []):
        restaurant = {
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "rating": place.get("rating", "N/A")
        }
        restaurants.append(restaurant)

    return json.dumps(restaurants[:7])

# Function to simulate the GPT-4o conversation and function calls
def run_conversation(messages):
    # Tools description
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_restaurants",
                "description": "Get restaurants around the convention center, which is where the user is.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Keyword to search for specific types of restaurants, e.g., 'expensive dinner'.",
                        },
                    },
                    "required": ["keyword"],
                },
            }
        }
    ]
    current_messages = [m for m in messages]

    # First API call to get the response
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=current_messages,
        tools=tools,
        tool_choice="auto"  # auto is default, but we'll be explicit
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Check if the model wants to call a function
    if tool_calls:
        available_functions = {
            "get_restaurants": get_restaurants,
        }
        current_messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                keyword=function_args.get("keyword"),
            )
            current_messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response

        second_response = client.chat.completions.create(
            model="gpt-4o",
            messages=current_messages,
        )  # get a new response from the model where it can see the function response

        for word in second_response.choices[0].to_dict()['message']['content'].split():
            yield word + " "
            time.sleep(0.05)
        # return 

    else:
        for word in response_message.content.split():
            yield word + " "
            time.sleep(0.05)
    
    # return final_response

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    print(st.session_state.messages)

    # Get the response from the GPT-4o API using the entire message history
    response = run_conversation(st.session_state.messages)

    # Display assistant message in chat message container
    with st.chat_message("assistant"):
        response_output = st.write_stream(response)

        print('response output', response_output)
    
    # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response_output})
