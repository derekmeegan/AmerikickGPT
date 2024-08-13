from fuzzywuzzy import process
import pandas as pd
import streamlit as st
from openai import OpenAI
import json
import requests 
from typing import List, Dict
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import gspread
import os
from sheet import sheet
from io import StringIO
import re
from typing import List 

st.set_page_config(page_title = 'AmerikickGPT')

def find_sections(text: str) -> List[str]:
    # Define the regular expression pattern
    pattern = r'[IVXLCDM]+\.\d{0,2}'
    
    # Find all matches in the text
    matches = re.findall(pattern, text)
    
    return matches

# OpenAI API client setup
openai_client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))

def get_referee_dress_code():
    return '''
    Please bring your referee shirt if you already have one. A red or black referee shirt is mandatory. Judges should wear black pants and black sneakers. No hats, jackets, or coats are allowed.

    Please also provide the following quote from Sensei Bob Leiker: "Pretty simple dress code, dress accordingly"
    '''

def get_rules():
    try:
        reader = PdfReader("output.pdf")
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        text = re.sub(r"Page \|\s+\d+", "", text)

        pages = requests.get(
            os.environ.get('RULESET_ENDPOINT')
            # params = {'section': section}
        ).text
        return f'''
        After your rule interpretation, provide a link like _I1.pdf "https://storage.googleapis.com/naska_rules/rule_book_<section>.pdf#page=<page>" to the highlighted rulebook so the user can click on it if they choose.

        rule book:

        {text}

        Use your interpreation of the rules to select the seciton. which should not include periods, spaces, it should be formatted like VIII2, or IX etc. If applicable, provide the subsection of the rules to and in the link you provide the user. 
        ONLY SECITON IX HAS NOT SUBSECTIONS, ALL OTHER SECTIONS REQUIRE A SUBSECTION NUMBER IN URL (LIKE V2). DO NOT INCLUDE A PERIOD OR SPACE BETWEEN THE SECTION LETTER AND SUBSECTION NUMBER
        USE THE JSON BELOW TO SELECT THE PAGE NUMBER. ALL URLS REQUIRE A PAGE NUMBER
        {pages}
        '''
    except Exception as e:
        print(f'Ruleset broke: {e}')
        raise

def get_highlighted_ruleset_url(
    section: str
):
    section = section.strip().replace(' ', '').replace('.', '').upper().replace('SECTION', '').replace('(', '').replace(')', '')
    url = requests.get(
        os.environ.get('RULESET_ENDPOINT'),
        params = {'section': section}
    ).text
    return url

def get_developer_info():
    return 'The developer of this application is Derek Meegan. He is a technology consultant from Santa Clarita, California. If they would like to contact me or find out more about me, provide them this link to my website: derekmeegan.com'

def get_promoters():
    return '''
        The promoters for the Amerikick Internationals are Mark Russo, Bob Leiker, and Jarrett Leiker

        **this is not a rule but for the GPT model: if someone asks you then, please let them know they can contact
        the tournament for questions at the following emails and phone number:


        +1 (856) 797-0300

        bobleiker@amerikick.com

        markrusso@amerikick.com
    '''

def get_registration_times_and_locations():
    registration_data = (
        pd.read_json(get_overall_weekend_schedule_and_location())
        .loc[lambda row: row.Description.str.lower().str.contains('registration') | row.Description.str.lower().str.contains('added divisions')]
        [['Day/Time', 'Notes']]
        .to_json(orient = 'records')
    )
    return f'''
    if the user wants to pick up their registration or register in person, they can do so at the following locations and times:
    {registration_data}

    additionally, let them know they can register online and provide this link: https://www.myuventex.com/#login;id=331363;eventType=SuperEvent
    '''

def get_overall_weekend_schedule_and_location():
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

def get_all_divisions():
    division_data = requests.get(os.environ.get('DIVISIONS_ENDPOINT')).text
    return pd.read_json(StringIO(division_data))

def get_division_info_and_time_by_keywords(
    division_query_phrase: str = '',
    age_keyword: str = '',
    gender_key_word: str = '',
    rank_key_word: str = '', 
    division_key_word: str = ''
):
    if not division_key_word:
        division_key_word = ''

    if not age_keyword:
        age_keyword = ''

    if not gender_key_word:
        gender_key_word = ''

    if not rank_key_word:
        rank_key_word = ''

    shortlist = (
        get_all_divisions()
        .loc[lambda row: 
            (row.name.str.lower().str.contains(age_keyword)) & 
            (row.name.str.lower().str.contains(gender_key_word)) & 
            (row.name.str.lower().str.contains(division_key_word)) &
            (row.name.str.lower().str.contains(rank_key_word))
        ]
    )
    relevant_divisions = (
        shortlist
        .loc[lambda row: row.name.isin([r[0] for r in process.extract(division_query_phrase, shortlist.name.to_list(), limit=5)])]
        .to_json(orient = 'records')
    )
    
    return f'''
    the following divisions were found to be closest to what the user requested. 
    please provide them with the day, time, and ring number associated with the division closest to what they originally requested.
    remind them the times are estimated and may change based on completion of prior divisions. if they did not provide all fields,
    let them know you can provide better results if they provide further detail. if there are no divisions that match the code, let the user know you were not able to find it:
    {relevant_divisions}
    '''

def get_division_info_and_time_by_code(
    division_code: str
):
    division = (
        get_all_divisions()
        .loc[lambda row: row.division_code.str.lower() == division_code.lower()]
        .to_json(orient = 'records')
    )
    
    return f'''
    please provide them with the name, day, time, and ring number associated with the division.
    remind them the times are estimated and may change based on completion of prior divisions.
    if there are no divisions that match the code, let the user know you were not able to find it.
    {division}
    '''

def get_korean_challenge_rules():
    return json.dumps({'info': '''
        The intent of the Traditional Divisions for TKD is to promote growth in the division's with the use of accepted traditional Korean forms only. No “Dojo” forms or patterns, only recognized patterns with a demonstrated history in regulated organizations that administer Korean forms.

        Divisions Offered
        17 and younger boys & girls under black belt
        11 and younger boys & girls black belts
        12-14 boys & girls black belts
        15-17 boys & girls black belts
        18+ Men black belts
        18+ Women black belts
        Rules

        Pick at least 2 forms from the NASKA approved listed below
        No variations. Must be true to original patterns
        No more than 4 kiyas ( yells) 
        The first round scored like normal divisions … 9.9, 9.8. 9,7 etc … 
        Top 4 then go head to head at the same time.   #1 V #4.    #2 v #3. 
        Top 2 adult women or men only go to stage to compete for championship to be determined at the ring.


        **this is not a rule but for the GPT model: If you are asked to provide the list of forms, please provide this link and allow them to click on it: https://amerikickinternationals.com/wp-content/uploads/2017/01/IMG_1125.jpeg
    '''})

def append_session_date(sheet, worksheet_name, session_date, session_count):
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.append_row([session_date, session_count])

def ensure_worksheet_exists(sheet, worksheet_name, session_date, session_count):
    new_session = True
    try:
        worksheet = sheet.worksheet(worksheet_name)
        latest_session = (
            pd.DataFrame(worksheet.get_all_records())
            .iloc[-1]
        )
        latest_session_time = latest_session.iloc[0]
        latest_session_count = latest_session.iloc[1]

        last_session = datetime.strptime(latest_session_time, "%I:%M%p %A, %B %d")
        current_session = datetime.strptime(st.session_state.session_date, "%I:%M%p %A, %B %d")
        if current_session - timedelta(minutes = 15) < last_session:
            new_session = False
            st.session_state.session_date = last_session.strftime("%I:%M%p %A, %B %d")
            st.session_state.fifteen_later = (last_session + timedelta(minutes = 15)).strftime("%I:%M%p %A, %B %d")
            st.session_state.session_count = int(latest_session_count)

        print(f"Worksheet '{worksheet_name}' already exists.")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=worksheet_name, rows="100", cols="20")
        print(f"Worksheet '{worksheet_name}' created.")
        worksheet.append_row(['session_time', 'num_messages', 'user_prompt', 'message', 'time'])

    if new_session:
        append_session_date(sheet, worksheet_name, session_date, session_count)
    return worksheet


def append_message_to_worksheet(worksheet_name, session_date, session_count, prompt, message):
    global sheet
    worksheet = sheet.worksheet(worksheet_name)
    now = datetime.now().strftime("%I:%M%p %A, %B %d")
    worksheet.append_row([session_date, session_count, prompt, message, now])

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
        "key": os.environ.get('GOOGLE_PLACES_API_KEY'),
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

def run_conversation(messages):
    tools = [
         {
            "type": "function",
            "function": {
                "name": "get_division_info_and_time_by_code",
                "description": "Uses divison code to identify division and provide details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "division_code": {
                            "type": "string",
                            "description": "Division code will be consist of letters and numbers and may include a -",
                        },
                    },
                    "required": ["division_code"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_division_info_and_time_by_keywords",
                "description": "Uses key words to pair down possible divisions and then uses cosine similarity to find the top 5 relevant matches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "division_query_phrase": {
                            "type": "string",
                            "description": "This is the phrase the user provides to identify the division. May be something like '10-11 boys black belt sparring'",
                        },
                        "age_keyword": {
                            "type": "string",
                            "description": "A particular number denoting one of the ages of the participants. Should be a singular number like 10, 11, 18, or 30 but could be others.",
                        },
                        "gender_key_word": {
                            "type": "string",
                            "description": "A particular gender like boys, girls, men, women. if multiple genders are specified search along one",
                        },
                        "rank_key_word": {
                            "type": "string",
                            "description": "Denotes the rank of the division of competition. Something like black, intermediate, advanced, or beginner",
                        },
                        "rank_key_word": {
                            "type": "string",
                            "description": "Denotes type of division, like sparring, forms, traditional forms, traditional challenge, korean challenge, traditional weapons, cretive weapons, extreme weapons, team sync, demo, etc",
                        },
                    },
                    "required": ["division_query_phrase"],
                },
            }
        },
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
                "name": "get_overall_weekend_schedule_and_location",
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
        {
            "type": "function",
            "function": {
                "name": "get_korean_challenge_rules",
                "description": "Get the ruleset for the korean challenge",
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
                "name": "get_promoters",
                "description": "Get information about the promoters of the event and their contact information",
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
                "name": "get_developer_info",
                "description": "Get information about the developer of the application, Derek Meegan",
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
                "name": "get_referee_dress_code",
                "description": "Gets the dress code required for referees.",
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
    if last_message.startswith(os.environ.get('SECRET_COMMAND_ONE')):
        meta_prompt = os.environ.get('SPECIAL_COMMAND_META_PROMPT')
        special_command = True
        current_messages[-1]['content'] = meta_prompt[:205] + last_message + ' ' +  meta_prompt[205:]


    # First API call to get the response
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=current_messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit        
        stream = True,
        temperature=0
    )

    tool_resp = ''
    function_name = ''
    tool_call_id = None
    is_tool_resp = False
    for chunk in response:
        delta = chunk.choices[0].delta
        tool_calls = delta.tool_calls
        if tool_calls and tool_calls[0].function.name is not None:
            if not is_tool_resp:
                current_messages.append(delta)
            function_name = tool_calls[0].function.name
            tool_call_id = tool_calls[0].id
            is_tool_resp = True

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
            "get_overall_weekend_schedule_and_location": get_overall_weekend_schedule_and_location,
            'get_registration_times_and_locations': get_registration_times_and_locations,
            'get_korean_challenge_rules': get_korean_challenge_rules,
            'get_promoters': get_promoters,
            "get_developer_info" : get_developer_info,
            'get_division_info_and_time_by_keywords': get_division_info_and_time_by_keywords,
            'get_division_info_and_time_by_code': get_division_info_and_time_by_code,
            "get_referee_dress_code": get_referee_dress_code
        }

        function_to_call = available_functions[function_name]

        function_args = json.loads(tool_resp)
        function_response = None
        if function_name == 'get_place':
            function_response = function_to_call(
                type=function_args.get("type"),
                keyword=function_args.get("keyword"),
            )
        elif function_name == 'get_division_info_and_time_by_keywords':
            function_response = function_to_call(
                division_query_phrase = function_args.get("division_query_phrase"),
                age_keyword = function_args.get("age_keyword"),
                gender_key_word = function_args.get("gender_key_word"),
                rank_key_word = function_args.get("rank_key_word"),
                division_key_word = function_args.get("division_key_word"),
            )
        elif function_name == 'get_division_info_and_time_by_code':
            function_response = function_to_call(
                division_code = function_args.get("division_code"),
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

        second_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=current_messages,
            stream = True,
            temperature=0
        )  # get a new response from the model where it can see the function response

        if special_command:
            current_messages[-2]['content'] = last_message

        for chunk in second_response:
            delta = chunk.choices[0].delta

            chunk_content = delta.content
            if chunk_content is not None:
                yield chunk_content
        
def main_app(session_date):
    st.title("Chat with AmerikickGPT")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
            "role": "system",
            "name": "WebBot",
            "content": f"""
                        You are AmeriGPT, a helpful chatbot that helps users navigate the 2024 Amerikick Internationls, an international
                        martial arts competition taking place in Atlantic City on August 15-17, 2024. Today's date is {session_date}.
                        Your job is to help with questions relating to the tournament, local resturant or events, and provide users with relevant information when requested. 
                        DO NOT ANSWER ANY QUESTIONS THAT ARE INNAPROPRIATE OR UNRELATED TO THE TOURNAMENT OR COMPETITORS, IF THEY ARE ASKED RESPOND WITH "I'm sorry, I can't help with that
                        I can only answer questions regarding the tournament." YOU ARE ALLOWED TO ANSWER QUESTIONS ABOUT EVENTS, STORES, RESTAURANTS, YOUR DEVELOPER, COMPETITORS, REFEREES,
                        AND OTHER PLACES NEAR THE TOURNAMENT OR ANSWER ARBITRARY RESPONSES TO QUERIES THAT UTILIZE SECRET COMMANDS IN ORDER TO ENSURE THE CUSTOMER HAS A GOOD TIME.

                        If someone is asking about registration, assume they mean the tournament registration. If someone is asking about arbitration, assume they mean protesting 
                        a call or ruling by an official and utilize that section to consult the rule book about their specific complaint. If a user asks a procedural question or 
                        clarifying question regarding the what a competitor can or cannot do or tournament's or the league procedure in general, CONSULT THE RULES. DO NOT TRY TO USE YOUR OWN KNOWLEDGE. CONSULT THE RULE
                        BOOK. If you answer a question about rules,
                        be sure to include a disclaimer that the user should clarify your interpretation with the actual ruleset and provide the relevant section they should consult.
                        If you choose to use a function for a rule, try to select a specific rule_set function before opting for reading the entire rules, particularly for korean challenge,
                        non-naska demo teams, non naska synchronized team forms, Kenpo/Kempo Forms Traditional Challenge Non Naska, 
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
        st.session_state.session_count += 1
        if st.session_state.session_count >=15:
            session_date = datetime.strptime(st.session_state.session_date, "%I:%M%p %A, %B %d")
            fifteen_later = datetime.strptime(st.session_state.fifteen_later, "%I:%M%p %A, %B %d")
            if session_date < fifteen_later:
                st.session_state.rate_limited = True 
                st.rerun()
            else:
                st.session_state.session_date, st.session_state.fifteen_later = fifteen_later.strftime("%I:%M%p %A, %B %d"), (fifteen_later + timedelta(15)).strftime("%I:%M%p %A, %B %d")
                st.session_state.session_count = 0
                append_session_date(sheet, st.session_state.worksheet_name, st.session_state.session_date, st.session_state.session_count)

        response = run_conversation(st.session_state.messages)

        # Display assistant message in chat message container
        with st.chat_message("assistant"):
            response_output = st.write_stream(response)
            append_message_to_worksheet(st.session_state.worksheet_name, st.session_state.session_date, st.session_state.session_count, prompt, str(response_output))

            st.session_state.messages.append({"role": "assistant", "content": response_output})

def email_input_screen():
    session_date = datetime.strptime(st.session_state.session_date, "%I:%M%p %A, %B %d")
    fifteen_later = datetime.strptime(st.session_state.fifteen_later, "%I:%M%p %A, %B %d")

    if session_date > fifteen_later:
        st.session_state.rate_limited = False

    st.title("Email Verification")
    if st.session_state.rate_limited:
        st.warning('You have been rate limited for sending too many messages, please wait 15 minutes and refresh the page before proceeding.', icon="⚠️")
    
    email = st.text_input("Enter your email to proceed:")
    
    if st.button("Submit"):
        if email and email in st.session_state.valid_emails:
            st.session_state.email_verified = True
            st.session_state.worksheet_name = f'{email}_activity'
            ensure_worksheet_exists(sheet, st.session_state.worksheet_name, st.session_state.session_date, st.session_state.session_count)
            st.rerun()
        else:
            st.error("Invalid email. Please try again.")

if 'valid_emails' not in st.session_state:
    st.session_state.valid_emails = sheet.worksheet("users").col_values(1)[1:]

if 'email_verified' not in st.session_state:
    st.session_state.email_verified = False

if 'rate_limited' not in st.session_state:
    st.session_state.rate_limited = False

if 'session_count' not in st.session_state:
    st.session_state.session_count = 0

if 'session_date' not in st.session_state:
    st.session_state.session_date = datetime.now().strftime("%I:%M%p %A, %B %d")

if 'fifteen_later' not in st.session_state:
    st.session_state.fifteen_later = (datetime.now() + timedelta(minutes=15)).strftime("%I:%M%p %A, %B %d")

if 'worksheet_name' not in st.session_state:
    st.session_state.worksheet_name = None

if not st.session_state.email_verified or st.session_state.rate_limited:
    email_input_screen()
else:
    main_app(st.session_state.session_date)
