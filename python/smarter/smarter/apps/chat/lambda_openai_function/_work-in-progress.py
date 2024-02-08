# -*- coding: utf-8 -*-
"""scaffolding for nlp functions"""

# -*- coding: utf-8 -*-
import nltk  # NLTK is a leading platform for building Python programs to work with human language data https://www.nltk.org/
from openai_api.lambda_openai_function.plugin_loader import Plugin
from textblob import (  # TextBlob is a Python library for processing textual data https://pypi.org/project/textblob/
    TextBlob,
)


# https://textblob.readthedocs.io/en/dev/


def customized_prompt(plugin: Plugin, messages: list) -> list:
    """Modify the system prompt based on the plugin object and gauge sentiment of the most recent user message"""

    # Identify the most recent user message
    user_messages = [message for message in messages if message.get("role") == "user"]
    if user_messages:
        last_user_message = user_messages[-1].get("content")

        # Perform sentiment analysis
        sentiment = TextBlob(last_user_message).sentiment.polarity
        print(f"Sentiment of the last user message: {sentiment}")

    for i, message in enumerate(messages):
        if message.get("role") == "system":
            system_prompt = message.get("content")
            custom_prompt = {
                "role": "system",
                "content": system_prompt + "\n\n and also " + plugin.prompting.system_prompt,
            }
            messages[i] = custom_prompt
            break

    return messages


def customized_prompt2(plugin: Plugin, messages: list, word_list: list) -> list:
    """Modify the system prompt based on the plugin object, gauge sentiment of the most recent user message, and map words to a word list"""

    # Identify the most recent user message
    user_messages = [message for message in messages if message.get("role") == "user"]
    if user_messages:
        last_user_message = user_messages[-1].get("content")

        # Perform sentiment analysis
        sentiment = TextBlob(last_user_message).sentiment.polarity
        print(f"Sentiment of the last user message: {sentiment}")

        # Tokenize the text and tag each word with its part of speech
        tokens = nltk.word_tokenize(last_user_message)
        pos_tags = nltk.pos_tag(tokens)

        # Filter the words based on their POS tags
        nouns = [word for word, pos in pos_tags if pos in ["NN", "NNS", "NNP", "NNPS"]]
        verbs = [word for word, pos in pos_tags if pos in ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]]
        adjectives = [word for word, pos in pos_tags if pos in ["JJ", "JJR", "JJS"]]

        # Map the words to the word list
        mapped_nouns = [word for word in nouns if word in word_list]
        mapped_verbs = [word for word in verbs if word in word_list]
        mapped_adjectives = [word for word in adjectives if word in word_list]

        print(f"Mapped nouns: {mapped_nouns}")
        print(f"Mapped verbs: {mapped_verbs}")
        print(f"Mapped adjectives: {mapped_adjectives}")

    for i, message in enumerate(messages):
        if message.get("role") == "system":
            system_prompt = message.get("content")
            custom_prompt = {
                "role": "system",
                "content": system_prompt + "\n\n and also " + plugin.prompting.system_prompt,
            }
            messages[i] = custom_prompt
            break

    return messages
