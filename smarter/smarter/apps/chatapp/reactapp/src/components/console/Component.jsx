//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React, { useState, useEffect } from 'react';
import ReactJson from 'react-json-view';

// This project
import { ConsoleLayout } from "../../components/Layout/";
import { fetchConfig } from "../../config.js";

// This component
import "./Component.css";
import HelmetHeadStyles from "./HeadStyles"

function Console() {
  // state
  const [config, setConfig] = useState({});
  const [consoleText, setConsoleText] = useState([{}]);
  const [selectedMenuItem, setSelectedMenuItem] = useState("chatbot_request_history");
  const [debugMode, setDebugMode] = useState(false);
  const [chat_tool_call_history, setChatToolCallHistory] = useState([]);
  const [chat_plugin_usage_history, setChatPluginUsageHistory] = useState([]);
  const [chatbot_request_history, setChatbotRequestHistory] = useState([]);
  const [plugin_selector_history, setPluginSelectorHistory] = useState([]);


  const fetchAndSetConsoleConfig = async () => {
    try {
      const newConfig = await fetchConfig();

      if (newConfig?.debug_mode) {
        console.log("fetchAndSetConsoleConfig()...");
        console.log("fetchAndSetConsoleConfig() config:", newConfig);
      }

      setConfig(newConfig);
      setDebugMode(newConfig.debug_mode);

      // app configuration
      setChatToolCallHistory(newConfig.history.chat_tool_call_history || []);
      setChatPluginUsageHistory(newConfig.history.chat_plugin_usage_history || []);
      setChatbotRequestHistory(newConfig.history.chatbot_request_history || []);
      setPluginSelectorHistory(newConfig.history.plugin_selector_history || []);

      if (newConfig?.debug_mode) {
        console.log("fetchAndSetConsoleConfig() done!");
      }

    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  };

  // Lifecycle hooks
  useEffect(() => {
    if (debugMode) {
      console.log('Console() component mounted');
    }

    fetchAndSetConsoleConfig();

    return () => {
      if (debugMode) {
        console.log('Console() component unmounted');
      }
    };

  }, []);

  // simulated bash shell environment
  const pod_hash = Math.floor(Math.random() * 0xFFFFFFFF).toString(16);
  const last_login = new Date().toString();
  const getRandomIpAddress = () => {
    return `192.168.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`;
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
      switch (selected) {
        case "chat_config":
          newData = Array.isArray(config) ? config : [config] || newData;
          break;
        case "chat_tool_call_history":
          newData = chat_tool_call_history || newData;
          break;
        case "chat_plugin_usage_history":
          newData = chat_plugin_usage_history || newData;
          break;
        case "chatbot_request_history":
          newData = chatbot_request_history || newData;
          break;
        case "plugin_selector_history":
          newData = plugin_selector_history || newData;
          break;
      }
      setSelectedMenuItem(selected);
      setConsoleText(newData);
    }

    return (
      <li className="nav-item my-1">
        <a
          className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
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
          <ConsoleNavItem label="Config" selected="chat_config" />
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

  const ConsoleScreen = () => {
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
    <ConsoleLayout>
      <div className="console">
        <HelmetHeadStyles />
        {/*begin::Main*/}
        <div className="app-main flex-column flex-row-fluid" id="chatapp_console_app_main">
          {/*begin::Content wrapper*/}
          <div className="d-flex flex-column flex-column-fluid">
            {/*begin::Content*/}
            <div id="chatapp_console_app_content" className="app-content flex-column-fluid p-0 pb-5">
              {/*begin::Content container*/}
              <div
                id="chatapp_console_app_content_container"
                className="app-container container-xxl"
              >
                <ConsoleMenu />
                <ConsoleScreen />
              </div>
              {/*end::Content container*/}
            </div>
            {/*end::Content*/}
          </div>
          {/*end::Content wrapper*/}
        </div>
        {/*end:::Main*/}
      </div>
    </ConsoleLayout>
  );
}

export default Console;
