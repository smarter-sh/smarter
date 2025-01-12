//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React, { useRef } from "react";
import { useState } from "react";
import PropTypes from "prop-types";

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheckCircle, faTimesCircle, faRocket } from '@fortawesome/free-solid-svg-icons';

// Chat UI stuff
import "@chatscope/chat-ui-kit-styles/dist/default/styles.min.css";
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator,
  ConversationHeader,
  InfoButton,
  AddUserButton,
} from "@chatscope/chat-ui-kit-react";

// This project
import { setSessionCookie } from "../../cookies.js";
import { fetchConfig, setConfig } from "../../config.js";

// This component
import "./Component.css";
import { messageFactory, chatMessages2RequestMessages, chat_init } from "./utils.jsx";
import { MESSAGE_DIRECTION, SENDER_ROLE } from "./constants.js";
import { ChatModal } from "./Modal.jsx";
import { processApiRequest } from "./ApiRequest.js";
import { ErrorBoundary } from "./errorBoundary.jsx";


// Creates a fancier title for the chat app which includes
// fontawesome icons for validation and deployment status.
function AppTitle({ username, is_valid, is_deployed }) {
  return (
    <div>
      {username}&nbsp;
      {is_valid ? (
        <FontAwesomeIcon icon={faCheckCircle} style={{ color: 'green' }} />
      ) : (
        <FontAwesomeIcon icon={faTimesCircle} style={{ color: 'red' }} />
      )}
      {is_deployed ? (
        <>
        &nbsp;<FontAwesomeIcon icon={faRocket} style={{ color: 'orange' }} />
        </>
      ) : null }
    </div>
  );
}

// The main chat app component. This is the top-level component that
// is exported and used in the index.js file. It is responsible for
// managing the chat message thread, sending messages to the backend
// API, and rendering the chat UI.
function ChatApp(props) {

  // app configuration
  const config = props.config;    // see ../../data/sample-config.json for an example of this object.
  const welcome_message = config.chatbot.app_welcome_message;
  const placeholder_text = config.chatbot.app_placeholder;
  const api_url = config.chatbot.url_chatbot;
  const api_key = config.api_key;
  const background_image_url = config.chatbot.app_background_image_url;
  const app_name = config.chatbot.app_name;
  const system_role = config.chatbot.default_system_role;
  const assistant_name = config.chatbot.app_assistant;
  const info_url = config.chatbot.app_info_url;
  const example_prompts = config.chatbot.app_example_prompts;
  const file_attach_button = config.chatbot.app_file_attachment;
  const provider = config.chatbot.provider;
  const default_model = config.chatbot.default_model;
  const version = config.chatbot.version || "0.1.0";

  // chatbot state
  const is_valid = config.meta_data.is_valid;
  const is_deployed = config.meta_data.is_deployed;
  const sandbox_mode = config.sandbox_mode;
  const debug_mode = config.debug_mode;

  const [isTyping, setIsTyping] = useState(false);
  const fileInputRef = useRef(null);

  const session_key = config.session_key ? config.session_key : 'undefined';
  const chatHistory = config && config.history && config.history.chat_history ? config.history.chat_history : [];
  const message_thread = chat_init(welcome_message, system_role, example_prompts, session_key, chatHistory, "BACKEND_CHAT_MOST_RECENT_RESPONSE");
  const [messages, setMessages] = useState(message_thread);

  const username = app_name + " v" + version;

  const total_plugins = config.plugins.meta_data.total_plugins;
  let info = provider + " " + default_model;
  if (total_plugins > 0) {
    info += ` with ${total_plugins} additional plugins`;
  }


  // Error modal state management
  function openChatModal(title, msg) {
    setIsModalOpen(true);
    setmodalTitle(title);
    setmodalMessage(msg);
  };

  function closeChatModal() {
    setIsModalOpen(false);
  };
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMessage, setmodalMessage] = useState("");
  const [modalTitle, setmodalTitle] = useState("");

  // UI widget event handlers
  const handleStateChange = () => {

    fetchConfig().then(config => setConfigState(setConfig(config)));

  };

  const handleInfoButtonClick = () => {
    window.open(info_url, "_blank");
  };

  const handleAddUserButtonClick = () => {
    setSessionCookie("", true);
    handleStateChange();
  };

  async function handleApiRequest(input_text, base64_encode = true) {
    // API request handler. This function is indirectly called by UI event handlers
    // inside this module. It asynchronously sends the user's input to the
    // backend API using the fetch() function. The response from the API is
    // then used to update the chat message thread and the UI via React state.
    const newMessage = messageFactory(input_text, MESSAGE_DIRECTION.OUTGOING, SENDER_ROLE.USER);
    if (base64_encode) {
      console.error("base64 encoding not implemented yet.");
    }

    setMessages((prevMessages) => {
      const updatedMessages = [...prevMessages, newMessage];
      setIsTyping(true);

      (async () => {
        try {
          const msgs = chatMessages2RequestMessages(updatedMessages);
          const response = await processApiRequest(
            props,
            msgs,
            api_url,
            openChatModal,
          );

          if (response) {
            const assistantResponse = response.choices.find(message => message.message.role === 'assistant');
            const newResponseMessage = messageFactory(assistantResponse.message.content, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT);
            setMessages((prevMessages) => [...prevMessages, newResponseMessage]);
            setIsTyping(false);
            handleStateChange();
          }
        } catch (error) {
          setIsTyping(false);
          console.error("API Error: ", error);
          openChatModal("API Error", error.message);
        }
      })();

      return updatedMessages;
    });
  }

  // file upload event handlers
  const handleAttachClick = async () => {
    fileInputRef.current.click();
  };
  function handleFileChange(event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = (event) => {
      const fileContent = event.target.result;
      handleApiRequest(fileContent, true);
    };
    reader.readAsText(file);
  }

  // send button event handler
  const handleSend = (input_text) => {
    // remove any HTML tags from the input_text. Pasting text into the
    // input box (from any source) tends to result in HTML span tags being included
    // in the input_text. This is a problem because the API doesn't know how to
    // handle HTML tags. So we remove them here.
    const sanitized_input_text = input_text.replace(/<[^>]+>/g, "");

    // check if the sanitized input text is empty or only contains whitespace
    if (!sanitized_input_text.trim()) {
      return;
    }
    handleApiRequest(sanitized_input_text, false);
  };

  // UI widget styles
  // note that most styling is intended to be created in Component.css
  // these are outlying cases where inline styles are required in order to override the default styles
  const fullWidthStyle = {
    width: "100%",
  }
  const transparentBackgroundStyle = {
    backgroundColor: "rgba(0,0,0,0.10)",
    color: "lightgray",
  };
  const mainContainerStyle = {
    // backgroundImage:
    //   "linear-gradient(rgba(255, 255, 255, 0.95), rgba(255, 255, 255, .75)), url('" +
    //   background_image_url +
    //   "')",
    // backgroundSize: "cover",
    // backgroundPosition: "center",
    width: "100%",
    height: "100%",
  };
  const chatContainerStyle = {...fullWidthStyle, ...transparentBackgroundStyle};

  // render the chat app
  return (
    <div className="chat-app">
      <MainContainer style={mainContainerStyle}>
        <ErrorBoundary>
          <ChatModal
            isModalOpen={isModalOpen}
            title={modalTitle}
            message={modalMessage}
            onCloseClick={closeChatModal}
          />
        </ErrorBoundary>
        <ChatContainer style={chatContainerStyle}>
          <ConversationHeader>
            <ConversationHeader.Content
              userName={<AppTitle username={username} is_valid={is_valid} is_deployed={is_deployed} />}
              info={info}
            />
          <ConversationHeader.Actions>
            <AddUserButton onClick={handleAddUserButtonClick} title="New" />
            <InfoButton onClick={handleInfoButtonClick} title={info_url} />
          </ConversationHeader.Actions>
          </ConversationHeader>
          <MessageList
            style={transparentBackgroundStyle}
            scrollBehavior="auto"
            typingIndicator={
              isTyping ? (
                <TypingIndicator content={assistant_name + " is typing"} />
              ) : null
            }
          >
            {messages.filter(message => message.sender !== 'system').map((message, i) => {
              return <Message
                key={i}
                model={message}
                style={message.sender === 'smarter' ? { color: 'brown' } : {}}
              />;
            })}
          </MessageList>
          <MessageInput
            placeholder={placeholder_text}
            onSend={handleSend}
            onAttachClick={handleAttachClick}
            attachButton={file_attach_button}
            fancyScroll={false}
          />
        </ChatContainer>
        <input
          type="file"
          accept=".py"
          title="Select a Python file"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
      </MainContainer>
    </div>
  );
}

// define the props that are expected to be passed in and also
// make these immutable.
ChatApp.propTypes = {
  config: PropTypes.object.isRequired,
};

export default ChatApp;
