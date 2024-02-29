//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Oct-2023
//---------------------------------------------------------------------------------

// React stuff
import React, { useRef } from "react";
import { useState } from "react";
import PropTypes from "prop-types";

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
  VoiceCallButton,
  VideoCallButton,
} from "@chatscope/chat-ui-kit-react";

// Our stuff
import "./Component.css";
import { ChatModal } from "./Modal.jsx";
import { processApiRequest } from "./ApiRequest.js";
import { ErrorBoundary } from "./errorBoundary.jsx";

const MESSAGE_DIRECTION = {
  INCOMING: "incoming",
  OUTGOING: "outgoing",
}
const SENDER_ROLE = {
  SYSTEM: "system",
  ASSISTANT: "assistant",
  USER: "user",
};

function ChatApp(props) {
  const fileInputRef = useRef(null);

  // props. These are passed in from the parent component.
  // In all fairness this probably isn't necessary, but it's a good practice
  // to define the props that are expected to be passed in and also
  // to make these immutable.
  const welcome_message = props.welcome_message;
  const placeholder_text = props.placeholder_text;
  const api_url = props.api_url;
  const api_key = props.api_key;
  const app_name = props.app_name;
  const system_role = props.system_role;
  const assistant_name = props.assistant_name;
  const info_url = props.info_url;
  const example_prompts = props.example_prompts;
  const file_attach_button = props.file_attach_button;

  // const application_logo = props.application_logo;
  // const background_image_url = props.background_image_url;
  // const uses_openai = props.uses_openai;
  // const uses_openai_api = props.uses_openai_api;
  // const uses_langchain = props.uses_langchain;
  // const uses_memory = props.uses_memory;

  const [isTyping, setIsTyping] = useState(false);

  function conversationHeaderFactory() {
    return app_name;
  }

  function convertMarkdownLinksToHTML(message) {
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    return message.replace(markdownLinkRegex, '<a href="$2">$1</a>');
  }

  function messageFactory(message, direction, sender) {
    const converted_message = convertMarkdownLinksToHTML(message);
    return {
      message: converted_message,
      direction: direction,
      sentTime: new Date().toLocaleString(),
      sender: sender,
    };
  }
  function requestMessageFactory(role, content) {
    return {
      role: role,
      content: content,
    };
  }

  function chatMessages2RequestMessages(messages) {
    return messages.map((message, index) => {
      return requestMessageFactory(message.sender, message.message);
    });
  }

  function chatHistoryFactory(message, direction, sender, sentTime) {
    return {
      message: message,
      direction: direction,
      sentTime: sentTime,
      sender: sender,
    };
  }

  // Error modal state management
  function openChatModal(title, msg) {
    setIsModalOpen(true);
    setmodalTitle(title);
    setmodalMessage(msg);
  }
  function closeChatModal() {
    setIsModalOpen(false);
  }
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMessage, setmodalMessage] = useState("");
  const [modalTitle, setmodalTitle] = useState("");

  // prompt hints
  const examplePrompts = (prompts) => {
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

  // message thread content
  let intro_messages = [messageFactory(system_role, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.SYSTEM)];

  intro_messages.push(messageFactory(welcome_message, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT));

  const examples = examplePrompts(example_prompts);
  if (examples) {
    intro_messages.push(messageFactory(examples, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT));
  }

  const [messages, setMessages] = useState(intro_messages);
  const [chatHistory, setChatHistory] = useState([]);

  // UI widget event handlers
  const handleInfoButtonClick = () => {
    window.open(info_url, "_blank");
  };

  // API request handler
  async function handleRequest(input_text, base64_encode = true) {
    const newMessage = messageFactory(input_text, MESSAGE_DIRECTION.OUTGOING, SENDER_ROLE.USER);
    if (base64_encode) {
      console.log("base64 encoding input_text");
    }

    setMessages((prevMessages) => {
      const updatedMessages = [...prevMessages, newMessage];
      setIsTyping(true);

      (async () => {
        try {
          const msgs = chatMessages2RequestMessages(updatedMessages);
          const response = await processApiRequest(
            msgs,
            chatHistory,
            api_url,
            openChatModal,
          );

          if (response) {
            const assistantResponse = response.choices.find(message => message.message.role === 'assistant');
            const newResponseMessage = messageFactory(assistantResponse.message.content, MESSAGE_DIRECTION.INCOMING, SENDER_ROLE.ASSISTANT);
            setMessages((prevMessages) => [...prevMessages, newResponseMessage]);
            setIsTyping(false);
          }
        } catch (error) {
          // handle error
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
      handleRequest(fileContent, true);
    };
    reader.readAsText(file);
  }

  // send button event handler
  const handleSendRequest = (input_text) => {
    // remove any HTML tags from the input_text. Pasting text into the
    // input box (from any source) tends to result in HTML span tags being included
    // in the input_text. This is a problem because the API doesn't know how to
    // handle HTML tags. So we remove them here.
    const sanitized_input_text = input_text.replace(/<[^>]+>/g, "");

    // check if the sanitized input text is empty or only contains whitespace
    if (!sanitized_input_text.trim()) {
      return;
    }

    handleRequest(sanitized_input_text, false);
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
              userName={app_name}
              info={app_name}
            />
            <ConversationHeader.Actions>
              <VoiceCallButton disabled />
              <VideoCallButton disabled />
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
              return <Message key={i} model={message} />;
            })}
          </MessageList>
          <MessageInput
            placeholder={placeholder_text}
            onSend={handleSendRequest}
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
  welcome_message: PropTypes.string.isRequired,
  placeholder_text: PropTypes.string.isRequired,
  api_url: PropTypes.string.isRequired,
  api_key: PropTypes.string.isRequired,
  app_name: PropTypes.string.isRequired,
  system_role: PropTypes.string.isRequired,
  assistant_name: PropTypes.string.isRequired,
  info_url: PropTypes.string.isRequired,
  example_prompts: PropTypes.array.isRequired,
  file_attach_button: PropTypes.bool.isRequired,
  // background_image_url: PropTypes.string.isRequired,
  // application_logo: PropTypes.string.isRequired,
  // uses_openai: PropTypes.bool.isRequired,
  // uses_openai_api: PropTypes.bool.isRequired,
  // uses_langchain: PropTypes.bool.isRequired,
  // uses_memory: PropTypes.bool.isRequired,
};

export default ChatApp;
