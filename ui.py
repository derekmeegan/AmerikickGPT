import streamlit as st
import random
import time
from openai import AsyncOpenAI, OpenAI
import json
import requests 
from typing import List, Dict
from dotenv import dotenv_values
from datetime import datetime
import asyncio

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
                    I can only answer questions regarding the tournament." YOU ARE ALLOWED TO ANSWER QUESTIONS ABOUT EVENTS, STORES, RESTAURANTS, AND OTHER PLACES NEAR THE 
                    TOURNAMENT OR ANSWER ARBITRARY RESPONSES TO QUERIES THAT UTILIZE SECRET COMMANDS IN ORDER TO ENSURE THE CUSTOMER HAS A GOOD TIME.
                    """
        },
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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
        }
    ]
    current_messages = [m for m in messages]
    last_message = current_messages[-1]['content']
    special_command = False
    if 'brain rot' in last_message:
        special_command = True
        current_messages[-1]['content'] = f'''
        brain rot is a special command, you must use the following words to construct a respponse to the message provided. the response should be funny and ligth hearted but not mean
        the message is {current_messages[-1]}

        'rizz': 'What is the ability to charm and woo a person called?',
        'rizz lord': 'someone who has rizz",
        'edging': 'A technique for delaying finishing by stopping/slowing just before finishing',
        'caseoh': 'What is the human equivalent (same size) to a black hole?',
        'mewing': 'A form of oral posture aimed to improve jaw and facial structure by pressing tongue to the roof of their mouth',
        'blud': 'A slang term used to address men - equivalent to "bro"',
        'don pollo': 'A Spanish-speaking influencer from Dominica who primarily creates food and supermarket videos. Also referred to as King of Ohio',
        'un video ma mi gente': "What is the above influencer's first line in most of his videos (hint: 5 words - Spanish)",
        'bill collector': 'Animals, primarily dogs, are depicted of paying money to what character?',
        'tiktok rizz party': "A party held recently that has landed all over everyone's fyp.",
        'blue tie': 'What item of clothing is used to refer to the group leader of a group of boys at the above party?',
        'duke dennis': "A twitch streamer often revered as the epitome of the appearance of man (6'4, plays basketball)",
        'kai cenat': 'Another twitch streamer, most recently famous for getting friendzoned by famousSouth African artist Tyla',
        'sigma': 'A term used to refer to a very successful and masculine, yet very independent man with little interest in others and their emotions.',
        'gyat': "A term used to refer to an attractive person's large posterior",
        'mewing streak': 'The term used to refer to maintaining the oral posture to restructure the jaw shape over prolonged periods of time',
        'sam sulek': 'A gym influencer recognizable by his incredible shape and more noticeably, his dialect',
        'gooning': 'When one brings themselves close to finishing repetitively, yet does not finish and continues to repeat this procedure over long periods of time',
        'skibidi toilet': 'The face of brainrot - a toilet with a head inside it',
        'skibidi': 'Someone or something that is weird, odd, or offputting',
        'beta': 'The term used to refer to a very basic and normal person, with no unique personality. Most of the population is this.',
        'yapping': 'Talking too much nonsense',
        'grimace shake': 'The name of the drink from the trend that depicts people supposedly falling down and fainting after drinking this drink.',
        'baby gronk': 'Who rizzed up Livvy Dunn?',
        'mog': 'The term used to refer to someone dominating in appearance because they are significantly more attractive than people around them',
        'fanum tax': 'A term for acquaintances taking food from each other',
        'quandale dingle': 'The name of a high school football player who has a weird shaped head. First roseto fame with his weird name on a PC login screen being made fun of.',
        'jelqing': "A massaging exercise done by stretching the one's wood so that it increases in length and girth",
        'looksmaxing': "The process of maximising one's physical attractiveness",
        'canthal tilt': "A term used to refer to the positioning of one's eyes"
        '''

    print(current_messages[-1])

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
        }

        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_resp)
        function_response = function_to_call(
            type=function_args.get("type"),
            keyword=function_args.get("keyword"),
        )
        print(f'calling {function_to_call} with {function_args}')
        current_messages.append(
            {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response

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