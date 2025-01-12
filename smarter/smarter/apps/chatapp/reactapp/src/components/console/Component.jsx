//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React, { useState } from 'react';
import PropTypes from "prop-types";
import ReactJson from 'react-json-view';

// Our stuff
import "./Component.css";
import HelmetHeadStyles from "./HeadStyles"

function Console(props) {
  // state
  const [consoleText, setConsoleText] = useState([{}]);
  const [selectedMenuItem, setSelectedMenuItem] = useState("chatbot_request_history");

  // app configuration
  const config = props.config; // see ../../data/sample-config.json for an example of this object.
  const chat_tool_call_history = config.history.chat_tool_call_history || [];
  const chat_plugin_usage_history =
    config.history.chat_plugin_usage_history || [];
  const chatbot_request_history = config.history.chatbot_request_history || [];
  const plugin_selector_history = config.history.plugin_selector_history || [];


  // simulated bash shell environment
  const pod_hash = Math.floor(Math.random() * 0xFFFFFFFF).toString(16);
  const last_login = new Date().toString();
  const getRandomIpAddress = () => {
    return `192.10.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`;
  };
  const system_prompt = "smarter_user@smarter-" + pod_hash + ":~/smarter$";

  // set the console output text based on the selected menu item
  function setSelection(selected="chatbot_request_history") {
    let newData = [{}];
    if (selected === "chat_tool_call_history") {
      setSelectedMenuItem("chat_tool_call_history");
      newData = chat_tool_call_history || newData;
    }
    if (selected === "chat_plugin_usage_history") {
      setSelectedMenuItem("chat_plugin_usage_history");
      newData = chat_plugin_usage_history || newData;
    }
    if (selected === "chatbot_request_history") {
      setSelectedMenuItem("chatbot_request_history");
      newData = chatbot_request_history || newData;
    }
    if (selected === "plugin_selector_history") {
      setSelectedMenuItem("plugin_selector_history");
      newData = plugin_selector_history || newData;
    }
    console.log("selected: ", newData);
    setConsoleText(newData);
  }

  const ConsoleMenu = () => {
    return (
      <div
        id="kt_user_profile_nav"
        className="bg-gray-200 d-flex flex-stack flex-wrap mb-2 p-2 console-nav-items"
        data-kt-sticky="true"
        data-kt-sticky-name="sticky-profile-navs"
        data-kt-sticky-offset="{default: false, lg: '200px'}"
        data-kt-sticky-width="{target: '#kt_app_content_container'}"
        data-kt-sticky-left="auto"
        data-kt-sticky-top="70px"
        data-kt-sticky-animation="false"
        data-kt-sticky-zindex={95}
      >
        {/*begin::Nav*/}
        <ul className="nav flex-wrap border-transparent">
          {/*begin::Nav item*/}
          <li className="nav-item my-1">
            <a
              className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
              href="#"
              onClick={() => setSelection("chatbot_request_history")}
            >
              Api Calls
            </a>
          </li>
          {/*end::Nav item*/}
          {/*begin::Nav item*/}
          <li className="nav-item my-1">
            <a
              className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
              href="#"
              onClick={() => setSelection("plugin_selector_history")}
            >
              Plugin Selectors
            </a>
          </li>
          {/*end::Nav item*/}
          {/*begin::Nav item*/}
          <li className="nav-item my-1">
            <a
              className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
              href="#"
              onClick={() => setSelection("chat_tool_call_history")}
            >
              Tool Calls
            </a>
          </li>
          {/*end::Nav item*/}
          {/*begin::Nav item*/}
          <li className="nav-item my-1">
            <a
              className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
              href="#"
              onClick={() => setSelection("chat_plugin_usage_history")}
            >
              Plugin Usage
            </a>
          </li>
          {/*end::Nav item*/}
        </ul>
        {/*end::Nav*/}
      </div>
    );
  };

  const ConsoleOutputInitializing = () => {
    return (
      <div>
        <p className="mb-0">Last login: {last_login} from {getRandomIpAddress()}</p>
        <p className="mb-0">{system_prompt}</p>
      </div>
    );
  };

  const ConsoleOutput = () => {
    return (
      <div className="console-output rounded">
        <div className="console-output-content">
          <ConsoleOutputInitializing />
          {consoleText.length === 1 && JSON.stringify(consoleText[0]) === '{}' ? null : (
            <>
              {consoleText.map((item, index) => (
                <ReactJson key={index} src={item} theme="monokai" />
              ))}
              <p className="mb-0">{system_prompt}</p>
            </>
          )}
        </div>
      </div>
    );
  };


  return (
    <div className="console">
      <HelmetHeadStyles />
      {/*begin::Main*/}
      <div className="app-main flex-column flex-row-fluid" id="kt_app_main">
        {/*begin::Content wrapper*/}
        <div className="d-flex flex-column flex-column-fluid">
          {/*begin::Content*/}
          <div id="kt_app_content" className="app-content flex-column-fluid p-0 pb-5">
            {/*begin::Content container*/}
            <div
              id="kt_app_content_container"
              className="app-container container-xxl"
            >
              <ConsoleMenu />
              <ConsoleOutput />
            </div>
            {/*end::Content container*/}
          </div>
          {/*end::Content*/}
        </div>
        {/*end::Content wrapper*/}
      </div>
      {/*end:::Main*/}
    </div>
  );
}

// define the props that are expected to be passed in and also
// make these immutable.
Console.propTypes = {
  config: PropTypes.object.isRequired,
  chat_tool_call_history: PropTypes.array.isRequired,
  chat_plugin_usage_history: PropTypes.array.isRequired,
  chatbot_request_history: PropTypes.array.isRequired,
  plugin_selector_history: PropTypes.array.isRequired,
};

export default Console;
