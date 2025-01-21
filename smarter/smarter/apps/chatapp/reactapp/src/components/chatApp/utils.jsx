import { MESSAGE_DIRECTION, SENDER_ROLE, VALID_MESSAGE_ROLES } from "./constants.js";



export function chat_restore_from_backend(chat_history, last_response) {
  /*
  Rebuild the message thread from the most recently persisted chat history.
  */
  try {
    const messages = (chat_history ? chat_history : [])
    .map((chat) => {
      if (chat.role === SENDER_ROLE.USER) {
        return messageFactory(chat, chat.content, MESSAGE_DIRECTION.OUTGOING, chat.role);
      } else if (chat.role === SENDER_ROLE.SYSTEM) {
        return messageFactory(chat, chat.content, MESSAGE_DIRECTION.INCOMING, chat.role);
      } else if (chat.role === SENDER_ROLE.ASSISTANT) {
        return messageFactory(chat, chat.content, MESSAGE_DIRECTION.INCOMING, chat.role);
      } else if (chat.role === SENDER_ROLE.SMARTER) {
        return messageFactory(chat, chat.content, MESSAGE_DIRECTION.INCOMING, chat.role);
      }
      if (chat.role !== SENDER_ROLE.TOOL) {
        console.error(`chat_restore_from_backend() Invalid role received: ${chat.role}`);
      }
    })
    .filter(message => message && typeof message === 'object' && !Array.isArray(message));


    if (last_response?.choices?.[0]?.message?.content) {
      const last_message = last_response.choices[0].message;
      const last_message_content = last_message.content;
      messages.push(messageFactory(last_message, last_message_content, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT));
    }

    return messages;
  } catch (error) {
    console.error(`chat_restore_from_backend() Error occurred while restoring chat from backend: ${error}`);
    return []; // return an empty array in case of error
  }
};


const examplePrompts = (prompts) => {
  /*
  If we have no chat history, and the Application configuration includes
  example prompts, we can display them to the user to help them get started.
  */
  if (prompts.length == 0) {
    return "";
  } else
    return (
      "Some example prompts to get you started:\r\n\r\n" +
      prompts
        .map((prompt) => {
          return prompt + "\r\n";
        })
        .join("")
    );
};

export function chat_intro(welcome_message, system_role, example_prompts) {
  /*
  Generate the initial message thread for the chat window. This includes the
  welcome message, and any example prompts that are configured in the
  Application settings.
   */
  let messages = [messageFactory({}, system_role, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.SYSTEM)];
  messages.push(messageFactory({}, welcome_message, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT));

  const examples = examplePrompts(example_prompts);
  if (examples) {
    messages.push(messageFactory({}, examples, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT));
  }

  return messages;
};

export function convertMarkdownLinksToHTML(message) {
  /*
  Convert markdown links to HTML links.
   */
  if (typeof message !== 'string') {
    console.error(`convertMarkdownLinksToHTML() Expected a string but received ${typeof message}`);
    console.error("convertMarkdownLinksToHTML() broke here", message);
    return message; // or return a default value
  }

  const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  return message.replace(markdownLinkRegex, '<a href="$2">$1</a>');
};

export function messageFactory(originalMessage, content, direction, sender) {
  /*
  Create a new message object.
   */
  const converted_content = (typeof content === 'string' && content !== null) ? convertMarkdownLinksToHTML(content) : content;
  const retVal = {
    message: converted_content,
    direction: direction,
    sender: sender,
    sentTime: new Date().toLocaleString(),
  };
  if (originalMessage) {
    retVal.originalMessage = originalMessage;
  } else {
    retVal.originalMessage = retVal;
  }
  return retVal;

};

function requestMessageFactory(message) {
  let retVal = message.originalMessage || {};
  retVal.role = message.originalMessage && message.originalMessage.role ? message.originalMessage.role : message.sender;
  retVal.content = message.originalMessage && message.originalMessage.message ? message.originalMessage.message : message.message;
  return retVal;
}

export function chatMessages2RequestMessages(messages) {
  /*
  Transform the chat message thread into a list of request messages for the
  backend API.
  */
  return messages
    // filter out smarter messages
    .filter(message => VALID_MESSAGE_ROLES.includes(message.sender))
    .map((message, index) => {
    return requestMessageFactory(message);
  });
};

export function chat_init(welcome_message, system_role, example_prompts, chat_id, chat_history, last_response) {
  /*
  Initialize the chat message thread. This function is called when the chat
  window is first opened, or when the chat window is restored from the
  backend.
   */

  let messages = [];
  messages = chat_restore_from_backend(chat_history, last_response)

  if (messages.length === 0) {
    messages = chat_intro(welcome_message, system_role, example_prompts);
  }

  return messages;
};
