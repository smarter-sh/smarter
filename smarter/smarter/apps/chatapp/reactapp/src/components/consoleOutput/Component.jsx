//---------------------------------------------------------------------------------
//  written by: Lawrence McDaniel
//              https://lawrencemcdaniel.com
//
//  date:       Mar-2024
//---------------------------------------------------------------------------------

// React stuff
import React from "react";
import PropTypes from 'prop-types';

// Our stuff
import "./Component.css";



function ConsoleOutput(props) {

  // app configuration
  const config = props.config;    // see ../../data/sample-config.json for an example of this object.
  const chat_tool_call_history = config.history.chat_tool_call_history || [];
  const chat_plugin_usage_history = config.history.chat_plugin_usage_history || [];
  const chatbot_request_history = config.history.chatbot_request_history || [];
  const plugin_selector_history = config.history.plugin_selector_history || [];

  return (
    <div className="console-output">
      {/*begin::Main*/}
      <div className="app-main flex-column flex-row-fluid" id="kt_app_main">
        {/*begin::Content wrapper*/}
        <div className="d-flex flex-column flex-column-fluid">
          {/*begin::Toolbar*/}
          <div id="kt_app_toolbar" className="app-toolbar py-3 py-lg-6">
            {/*begin::Toolbar container*/}
            <div
              id="kt_app_toolbar_container"
              className="app-container container-xxl d-flex flex-stack"
            >
              {/*begin::Page title*/}
              <div className="page-title d-flex flex-column justify-content-center flex-wrap me-3">
                {/*begin::Title*/}
                <h1 className="page-heading d-flex text-gray-900 fw-bold fs-3 flex-column justify-content-center my-0">
                  Logs
                </h1>
                {/*end::Title*/}
              </div>
              {/*end::Page title*/}
            </div>
            {/*end::Toolbar container*/}
          </div>
          {/*end::Toolbar*/}
          {/*begin::Content*/}
          <div id="kt_app_content" className="app-content flex-column-fluid">
            {/*begin::Content container*/}
            <div
              id="kt_app_content_container"
              className="app-container container-xxl"
            >
              {/*begin::Nav items*/}
              <div
                id="kt_user_profile_nav"
                className="rounded bg-gray-200 d-flex flex-stack flex-wrap mb-9 p-2"
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
                      href="/dashboard/account/dashboard/overview/"
                    >
                      Prompts
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href="/dashboard/account/dashboard/settings/"
                    >
                      Plugin Selectors
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href="/dashboard/account/dashboard/users/"
                    >
                      Tool Calls
                    </a>
                  </li>
                  {/*end::Nav item*/}
                  {/*begin::Nav item*/}
                  <li className="nav-item my-1">
                    <a
                      className="btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1"
                      href="/dashboard/account/dashboard/activity/"
                    >
                      Plugin Usage
                    </a>
                  </li>
                  {/*end::Nav item*/}
                </ul>
                {/*end::Nav*/}
              </div>
              {/*end::Nav items*/}
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
  plugin_selector_history: PropTypes.array.isRequired
};

ConsoleOutput.defaultProps = {
  plugin_selector_history: [],
  chat_tool_call_history: [],
  chat_plugin_usage_history: [],
  chatbot_request_history: [],
};
export default ConsoleOutput;
