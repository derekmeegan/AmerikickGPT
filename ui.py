import pandas as pd
import streamlit as st
from openai import OpenAI
import json
import requests 
from typing import List, Dict
from dotenv import dotenv_values
from datetime import datetime
from PyPDF2 import PdfReader

config = dotenv_values(".env")

# OpenAI API client setup
client = OpenAI(api_key = config.get('OPENAI_API_KEY'))

def get_rules():
    reader = PdfReader("output.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# get hotel information
# get convention center information
# get

def get_registration_times_and_locations():
    return (
        pd.read_json(get_event_schedule_and_location())
        .loc[lambda row: row.Description.str.lower().str.contains('registration') | row.Description.str.lower().str.contains('added divisions')]
        [['Day/Time', 'Notes']]
        .to_json(orient = 'records')
    )

def get_event_schedule_and_location():
    return (
        pd.read_html('https://amerikickinternationals.com/schedule/')[0]
        .pipe(
            lambda df_: df_.set_axis(df_.iloc[1], axis = 1)
        )
        .iloc[3:]
        .dropna(how = 'all')
        .drop(8)
        .to_json(orient = 'records')
    )

def get_tournament_info():
    return {
        'rating': '6A',
        'location': 'Atlantic City Convention Center',
        'name': 'Amerikick Internationals 2024'
    }

def get_convention_center_info():
    return {
        'address': '1 Convention Blvd, Atlantic City, NJ 08401',
        'phone': '609-449-2000',
        'hours': '24/7'
    }

# Function to call restaurants API
def get_place(
    type: str,
    keyword: str, 
) -> List[Dict[str, str]]:
    """
    Fetches a list of places around a specified location using Google Places API.

    :param type: 
    :param keyword: 
    :return: List of dictionaries containing restaurant details
    """
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": "39.363333, -74.439166",
        "radius": 3000,
        "type": type,
        "key": config.get('GOOGLE_PLACES_API_KEY'),
        "keyword": keyword,
        'rankby':'distance'
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    data = response.json()

    restaurants = []
    for place in data.get("results", []):
        restaurant = {
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "rating": place.get("rating", "N/A"),
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
                "name": "get_place",
                "description": "Get places around the convention center, which is where the user is.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "The type of place that the user is looking for, ie casino, restaurant, or beach",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "Keyword to search for specific types of place, e.g., 'expensive' or 'mexican' if cuisine.",
                        },
                    },
                    "required": ["keyword"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_rules",
                "description": "Get ruleset for the tournament and North American Sport Karate Association.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_event_schedule_and_location",
                "description": "Get the overall weekeend schedule along with location and description for events. Use this for if a user asks where registration or an event is",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_registration_times_and_locations",
                "description": "Get the times and location of the tournament registration",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                },
            }
        },
    ]
    current_messages = [m for m in messages]
    last_message = current_messages[-1]['content']
    special_command = False
    if last_message.startswith(config.get('SECRET_COMMAND_ONE')):
        meta_prompt = config.get('SPECIAL_COMMAND_META_PROMPT')
        special_command = True
        current_messages[-1]['content'] = meta_prompt[:206] + last_message + meta_prompt[206:]


    # First API call to get the response
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=current_messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit        
        stream = True
    )

    tool_resp = ''
    function_name = ''
    tool_call_id = None
    is_tool_resp = False
    for chunk in response:
        delta = chunk.choices[0].delta
        tool_calls = delta.tool_calls
        if tool_calls:
            if tool_calls[0].function.name is not None:
                current_messages.append(delta)
                function_name = tool_calls[0].function.name
                tool_call_id = tool_calls[0].id
                is_tool_resp = True
            # break

        chunk_content = delta.content
        if chunk_content is not None and not is_tool_resp:
            if special_command:
                current_messages[-1]['content'] = last_message

            yield chunk_content

        else:
            if tool_calls is not None:
                tool_resp += tool_calls[0].function.arguments

    # Check if the model wants to call a function
    if is_tool_resp:
        available_functions = {
            "get_place": get_place,
            "get_rules": get_rules,
            "get_event_schedule_and_location": get_event_schedule_and_location,
            'get_registration_times_and_locations': get_registration_times_and_locations
        }

        function_to_call = available_functions[function_name]

        function_args = json.loads(tool_resp)
        function_response = None
        if function_name == 'get_place':
            function_response = function_to_call(
                type=function_args.get("type"),
                keyword=function_args.get("keyword"),
            )
        else:
            function_response = function_to_call()


        print(f'calling {function_to_call} with {function_args}')
        current_messages.append(
            {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response

        # print(current_messages)
        second_response = client.chat.completions.create(
            model="gpt-4o",
            messages=current_messages,
            stream = True
        )  # get a new response from the model where it can see the function response
        print('returning second response')

        if special_command:
            current_messages[-2]['content'] = last_message

        for chunk in second_response:
            delta = chunk.choices[0].delta

            chunk_content = delta.content
            if chunk_content is not None:
                yield chunk_content

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
                    I can only answer questions regarding the tournament." YOU ARE ALLOWED TO ANSWER QUESTIONS ABOUT EVENTS, STORES, RESTAURANTS, AND OTHER PLACES NEAR THE 
                    TOURNAMENT OR ANSWER ARBITRARY RESPONSES TO QUERIES THAT UTILIZE SECRET COMMANDS IN ORDER TO ENSURE THE CUSTOMER HAS A GOOD TIME.

                    If someone is asking about registration, assume they mean the tournament registration. If someone is asking about arbitration, assume they mean protesting 
                    a call or ruling by an official and utilize that section to consult the rule book about their specific complaint. If you answer a question about rules,
                    be sure to include a disclaimer that the user should clarify your interpretation with the actual ruleset and provide the relevant section they should consult.
                    """.strip().replace('\n', '')
        },
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get the response from the GPT-4o API using the entire message history
    response = run_conversation(st.session_state.messages)

    # Display assistant message in chat message container
    with st.chat_message("assistant"):
        response_output = st.write_stream(response)

    
    # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response_output})