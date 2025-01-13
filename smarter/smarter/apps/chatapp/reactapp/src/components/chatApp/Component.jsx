//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React, { useRef, useState, useEffect } from "react";

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
import { fetchConfig } from "../../config.js";
import { ChatAppLayout } from "../../components/Layout/";


// This component
import "./Component.css";
import { messageFactory, chatMessages2RequestMessages, chat_init, chat_intro } from "./utils.jsx";
import { MESSAGE_DIRECTION, SENDER_ROLE } from "./constants.js";
import { ChatModal } from "./Modal.jsx";
import { processApiRequest } from "./ApiRequest.js";
import { ErrorBoundary } from "./errorBoundary.jsx";


// The main chat app component. This is the top-level component that
// is exported and used in the index.js file. It is responsible for
// managing the chat message thread, sending messages to the backend
// API, and rendering the chat UI.
function ChatApp() {

  const [config, setConfig] = useState({});
  const [placeholderText, setPlaceholderText] = useState('');
  const [apiUrl, setApiUrl] = useState('');
  const [assistantName, setAssistantName] = useState('');
  const [infoUrl, setInfoUrl] = useState('');
  const [fileAttachButton, setFileAttachButton] = useState(false);
  const [isValid, setIsValid] = useState(false);
  const [isDeployed, setIsDeployed] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [messages, setMessages] = useState([]);
  const [title, setTitle] = useState('');
  const [info, setInfo] = useState('');

  // future use
  // const [apiKey, setApiKey] = useState('');
  // const [backgroundImageUrl, setBackgroundImageUrl] = useState('');
  // const [sandboxMode, setSandboxMode] = useState(false);

  // component internal state
  const [isTyping, setIsTyping] = useState(false);
  const fileInputRef = useRef(null);

  const fetchAndSetConfig = async () => {
    try {
      const newConfig = await fetchConfig();

      if (newConfig?.debug_mode) {
        console.log("fetchAndSetConfig()...");
        console.log("fetchAndSetConfig() config:", newConfig);
      }

      setConfig(newConfig);
      setPlaceholderText(newConfig.chatbot.app_placeholder);
      setApiUrl(newConfig.chatbot.url_chatbot);
      setAssistantName(newConfig.chatbot.app_assistant);
      setInfoUrl(newConfig.chatbot.app_info_url);
      setFileAttachButton(newConfig.chatbot.app_file_attachment);
      setIsValid(newConfig.meta_data.is_valid);
      setIsDeployed(newConfig.meta_data.is_deployed);
      setDebugMode(newConfig.debug_mode);


      // wrap up the rest of the initialization
      const newHistory = newConfig.history?.chat_history || [];
      const newThread = chat_init(newConfig.chatbot.app_welcome_message, newConfig.chatbot.default_system_role, newConfig.chatbot.app_example_prompts, newConfig.session_key, newHistory, "BACKEND_CHAT_MOST_RECENT_RESPONSE");
      setMessages(newThread);

      const newTitle = `${newConfig.chatbot.app_name} v${newConfig.chatbot.version || "1.0.0"}`;
      setTitle(newTitle);
      let newInfo = `${newConfig.chatbot.provider} ${newConfig.chatbot.default_model}`;
      if (newConfig.plugins.meta_data.total_plugins > 0) {
        newInfo += ` with ${newConfig.plugins.meta_data.total_plugins} additional plugins`;
      }
      setInfo(newInfo);

      if (newConfig?.debug_mode) {
        console.log("fetchAndSetConfig() done!");
      }

    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  };

  // Lifecycle hooks
  useEffect(() => {
    if (debugMode) {
      console.log('ChatApp() component mounted');
    }

    fetchAndSetConfig();

    return () => {
      if (debugMode) {
        console.log('ChatApp() component unmounted');
      }
    };

  }, []);


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

  const handleInfoButtonClick = () => {
    window.open(infoUrl, "_blank");
  };

  const handleAddUserButtonClick = () => {
    setSessionCookie("", debugMode);
    fetchAndSetConfig();
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
          const response = await processApiRequest(config, msgs, apiUrl, openChatModal);

          if (response) {
            const responseMessages = response.smarter.messages.map((message) => {
              return messageFactory(message.content, MESSAGE_DIRECTION.INCOMING, message.role);
            }
            );
            setMessages((prevMessages) => [...prevMessages, ...responseMessages]);
            setIsTyping(false);
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

  // Creates a fancier title for the chat app which includes
  // fontawesome icons for validation and deployment status.
  function AppTitle({ title, isValid, isDeployed }) {
    return (
      <div>
        {title}&nbsp;
        {isValid ? (
          <FontAwesomeIcon icon={faCheckCircle} style={{ color: 'green' }} />
        ) : (
          <FontAwesomeIcon icon={faTimesCircle} style={{ color: 'red' }} />
        )}
        {isDeployed ? (
          <>
          &nbsp;<FontAwesomeIcon icon={faRocket} style={{ color: 'orange' }} />
          </>
        ) : null }
      </div>
    );
  }


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
    <ChatAppLayout>
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
                userName={<AppTitle title={title} isValid={isValid} isDeployed={isDeployed} />}
                info={info}
              />
            <ConversationHeader.Actions>
              <AddUserButton onClick={handleAddUserButtonClick} title="New" />
              <InfoButton onClick={handleInfoButtonClick} title={infoUrl} />
            </ConversationHeader.Actions>
            </ConversationHeader>
            <MessageList
              style={transparentBackgroundStyle}
              scrollBehavior="auto"
              typingIndicator={
                isTyping ? (
                  <TypingIndicator content={assistantName + " is typing"} />
                ) : null
              }
            >
              {messages.filter(message => message.sender !== 'system').map((message, i) => {
                return <Message
                  key={i}
                  model={message}
                  className={message.sender === 'smarter' ? 'smarter-message' : ''}
                />;
              })}
            </MessageList>
            <MessageInput
              placeholder={placeholderText}
              onSend={handleSend}
              onAttachClick={handleAttachClick}
              attachButton={fileAttachButton}
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
    </ChatAppLayout>
  );
}

export default ChatApp;
