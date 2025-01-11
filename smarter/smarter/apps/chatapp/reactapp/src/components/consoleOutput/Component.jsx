//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React from "react";
import PropTypes from "prop-types";

// Our stuff
import "./Component.css";
import HelmetHeadStyles from "./HeadStyles"

function ConsoleOutput(props) {
  // app configuration
  const config = props.config; // see ../../data/sample-config.json for an example of this object.
  const chat_tool_call_history = config.history.chat_tool_call_history || [];
  const chat_plugin_usage_history =
    config.history.chat_plugin_usage_history || [];
  const chatbot_request_history = config.history.chatbot_request_history || [];
  const plugin_selector_history = config.history.plugin_selector_history || [];

  const pod_hash = Math.floor(Math.random() * 0xFFFFFFFF).toString(16);
  const last_login = new Date().toString();
  const getRandomIpAddress = () => {
    return `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`;
  };

  return (
    <div className="console">
      <HelmetHeadStyles />
      {/*begin::Main*/}
      <div className="app-main flex-column flex-row-fluid" id="kt_app_main">
        {/*begin::Content wrapper*/}
        <div className="d-flex flex-column flex-column-fluid">
          {/*begin::Toolbar*/}
          <div id="kt_app_toolbar" className="app-toolbar mt-0 pt-0">
            {/*begin::Toolbar container*/}
            <div
              id="kt_app_toolbar_container"
              className="app-container container-xxl d-flex flex-stack"
            >
              {/*end::Page title*/}
            </div>
            {/*end::Toolbar container*/}
          </div>
          {/*end::Toolbar*/}
          {/*begin::Content*/}
          <div id="kt_app_content" className="app-content flex-column-fluid p-0 pb-5">
            {/*begin::Content container*/}
            <div
              id="kt_app_content_container"
              className="app-container container-xxl"
            >
              {/*begin::Nav items*/}
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
                      href=""
                    >
                      Api Calls
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href=""
                    >
                      Plugin Selectors
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href=""
                    >
                      Tool Calls
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href=""
                    >
                      Plugin Usage
                    </a>
                  </li>
                  {/*end::Nav item*/}
                </ul>
                {/*end::Nav*/}
              </div>
              {/*end::Nav items*/}
              <div className="console-output rounded">
                <div className="console-output-content">
                  <p className="mb-0">Last login: {last_login} from {getRandomIpAddress()}</p>
                  <p className="mb-0">smarter_user@smarter-{pod_hash}:~/smarter$</p>
                </div>
              </div>
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
ConsoleOutput.propTypes = {
  config: PropTypes.object.isRequired,
  chat_tool_call_history: PropTypes.array.isRequired,
  chat_plugin_usage_history: PropTypes.array.isRequired,
  chatbot_request_history: PropTypes.array.isRequired,
  plugin_selector_history: PropTypes.array.isRequired,
};

export default ConsoleOutput;
