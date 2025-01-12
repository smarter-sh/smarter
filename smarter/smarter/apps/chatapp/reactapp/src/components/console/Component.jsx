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


  const ConsoleNavItem = (props) => {

    // set the console output text based on the selected menu item
    function consoleNavItemClicked(event, selected="chatbot_request_history") {
      // set the 'active' menu item
      requestAnimationFrame(() => {
        document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
        event.target.classList.add('active');
      });

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
      setConsoleText(newData);
    }

    return (
      <li className="nav-item my-1">
        <a
          className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
          href="#"
          onClick={(event) => consoleNavItemClicked(event, props.selected)}
        >
          {props.label}
        </a>
      </li>
    );
  };

  const ConsoleMenu = () => {
    return (
      <div
        id="chatapp_console"
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
        <ul className="nav flex-wrap border-transparent">
          <ConsoleNavItem label="Api Calls" selected="chatbot_request_history" />
          <ConsoleNavItem label="Plugin Selectors" selected="plugin_selector_history" />
          <ConsoleNavItem label="Tool Calls" selected="chat_tool_call_history" />
          <ConsoleNavItem label="Plugin Usage" selected="chat_plugin_usage_history" />
        </ul>
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
  config: PropTypes.object.isRequired
};

export default Console;
