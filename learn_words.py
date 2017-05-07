"""
Learn new words module
"""

from __future__ import print_function
import urllib
import urllib2
import json
import random

API_BASE = 'https://nsgaetxah5.execute-api.us-east-1.amazonaws.com/dev'
GET_NEW_WORDS_INTENT = 'GetNewWordsIntent'
LEARN_NEXT_WORD_INTENT = 'LearnNextWordIntent'
DEFINE_CURRENT_WORD_INTENT = 'DefineCurrentWordIntent'
GET_SENTENCE_CURRENT_WORD_INTENT = 'GetSentenceCurrentWordIntent'
REVIEW_WORDS_INTENT = 'ReviewWordsIntent'

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "To learn some new words, just ask Language Tutor."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "You can ask Alexa for a list of new words to learn."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Hope you've had a wonderful learning experience. \
        Come back to learn more words at any time!"

    reprompt_text = None
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

### fetch some words for ReviewWordsIntent
def get_words_to_review(intent, session):
    session_attributes = {}
    reprompt_text = None
    should_end_session = False

    # response is a list of raw dict words
    response = urllib2.urlopen(API_BASE + '/getReviewWordsCore')
    # status is a raw dict json object
    status = json.load(response)
    word_list = status['words'] if 'words' in status else []
    word_count = len(word_list)

    session_attributes = status
    session_attributes['reviewed_word_ids'] = [] # prepare a learned list, and perform batch update after learning

    speech_output = "Let's start reviewing the {0} {1} for you today. \
        You can start reviewing by saying give me the next word.".format(str(word_count), ("word" if (word_count == 1) else "words"))

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

### fetch the learning list for today
def get_list_of_new_words(intent, session):
    session_attributes = {}
    reprompt_text = None
    should_end_session = False

    # response is a list of raw dict words
    response = urllib2.urlopen(API_BASE + '/getNewWordsCore')
    # status is a raw dict json object
    status = json.load(response)
    word_list = status['words'] if 'words' in status else []
    word_count = len(word_list)

    session_attributes = status
    session_attributes['learned_word_ids'] = [] # prepare a learned list, and perform batch update after learning

    speech_output = "There are {0} {1} for you today. \
        You can start learning by saying give me the next word.".format(str(word_count), ("word" if (word_count == 1) else "words"))

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def learn_next_word(intent, session):
    remaining_words = session.get('attributes', {})
    should_end_session = False
    speech_output = "I can't do that. Please don't hate me."

    # Mode - learn or reviewing
    learning_mode = 'learned_word_ids' in remaining_words

    if len(remaining_words['words']) == 0:
        # finished learning all new words. Yay!
        speech_output = "You've {0} all the words today. Good job and Goodbye!".format("learned" if learning_mode else "reviewed")
        should_end_session = True
        if learning_mode:
            post_progress(remaining_words['learned_word_ids'])
    else:
        current_word = remaining_words['words'].pop() # current_word is a json object of raw dict word
        remaining_words['current_word'] = current_word
        if learning_mode:
            remaining_words['learned_word_ids'].append(current_word)
        speech_output = "The next word is {0}. To learn more about this word, \
            try ask for its definitions or a sample sentence.".format(current_word['text'])

    session_attributes = remaining_words

    reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

### get definitions for the current word being learned
def get_definitions_for_current_word(intent, session):
    session_attributes = session.get('attributes', {})
    should_end_session = False
    speech_output = "Cannot find definitions for this word"

    current_word = session_attributes['current_word']
    if current_word != None:
        word = current_word['text']
        defs = current_word['definitions']
        speech_output = read_definitions(word, defs)

    reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

### helper method to read word definitions as a string
def read_definitions(word, defs):
    output = ""
    for word_def in defs:
        output += "{0} can be used as a {1}, which means {2}. ".format(word, word_def['word_type'], word_def['def'])
    return output

### get an example sentence for the current word being learned
def get_sentence_for_current_word(intent, session):
    session_attributes = session.get('attributes', {})
    should_end_session = False
    speech_output = "Cannot find sample sentences for this word"

    current_word = session_attributes['current_word']
    if current_word != None:
        word = current_word['text']
        defs = current_word['definitions']
        speech_output = defs[0]['sentence']

    reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def word_list_to_string(list_words):
    res = "Words you just learned: "
    for word in list_words:
        res += word['text'] + "\n"
    return res

def post_progress(list_words):
    url = 'https://l.messenger.com/l.php?u=https%3A%2F%2Fapi.sparkpost.com%2Fapi%2Fv1%2Ftransmissions&h=ATOsgr9F3r-kp3tbbtXfoBNeETHdoYAhozUk7uVlTsqWIfPoX5R82Ny_48J4nKjny7bst5JooQXylcpDEKMIjBms5pYN_Gfz8ltZoTUr3rWwtHE346j5lg90TC2FTr_-kzloMfZBDKOqBQ'
    header = {
        "Authorization": "91944f1f0344382f4b39bdd4b5d4b7c290225794",
        "Content-Type": "application/json"
    }
    body = {
        "options": {
            "sandbox": True
        },
        "content": {
            "from": "sandbox@sparkpostbox.com",
            "subject": "Thundercats are GO!!!",
            "text": word_list_to_string(list_words)
        },
        "recipients": [{ "address": "edwardbai93@outlook.com" }]
    }
    request = urllib2.Request(url, data=json.dumps(body), headers=header)
    response = urllib2.urlopen(request)
    result = response.read()


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])

def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == GET_NEW_WORDS_INTENT:
        return get_list_of_new_words(intent, session)
    elif intent_name == REVIEW_WORDS_INTENT:
        return get_words_to_review(intent, session)
    elif intent_name == LEARN_NEXT_WORD_INTENT:
        return learn_next_word(intent, session)
    elif intent_name == DEFINE_CURRENT_WORD_INTENT:
        return get_definitions_for_current_word(intent, session)
    elif intent_name == GET_SENTENCE_CURRENT_WORD_INTENT:
        return get_sentence_for_current_word(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here

    session_attributes = session.get('attributes', {})
    list_of_ids = session_attributes['learned_word_ids']
    post_progress(list_of_ids)


# --------------- Main handler ------------------

def get_words_lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill.bd7e0806-959a-483e-87dc-89e10fcf0088"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

def post_words_lambda_handler(event, context):
    u = urllib2.urlopen(API_BASE + '/learnedWords', )
