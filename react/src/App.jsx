// React code
import React from "react";
import { useState } from "react";

// Third party components
import { Sidebar, Menu, MenuItem, SubMenu } from "react-pro-sidebar";
import {
  ContainerLayout,
  SidebarLayout,
  ContentLayout,
  Logo,
} from "./components/Layout/";
import {
  FaInfo,
  FaDatabase,
  FaCode,
  FaChartLine,
  FaClipboardList,
  FaGamepad,
} from "react-icons/fa";

// Our code
import "./App.css";
import ChatApp from "./components/chatApp/Component";
import AboutPage from "./components/about/Component";
import { APPLICATIONS } from "./config";

// chatApp definitions
import SarcasticChat from "./applications/SarcasticChat";

const currentYear = new Date().getFullYear();

const Footer = () => {
  return (
    <div className="footer hide-small">
      <p>
        © {currentYear}{" "}
        <a href="https://lawrencemcdaniel.com">lawrencemcdaniel.com</a> |{" "}
        <a href="https://openai.com/">
          <img src="openai-logo.svg" /> OpenAI Python API
        </a>{" "}
        |{" "}
        <a href="https://react.dev/">
          <img src="/react-logo.svg" /> React
        </a>{" "}
        |{" "}
        <a href="https://aws.amazon.com/">
          <img src="/aws-logo.svg" />
        </a>{" "}
        |{" "}
        <a href="https://www.terraform.io/">
          <img src="terraform-logo.svg" /> Terraform
        </a>{" "}
        |{" "}
        <a
          href="https://github.com/QueriumCorp/smarter"
          target="_blank"
          rel="noreferrer"
        >
          <img src="/github-logo.svg" /> Source code
        </a>
      </p>
    </div>
  );
};

const App = () => {
  const [selectedItem, setSelectedItem] = useState(
    APPLICATIONS.FunctionCalling,
  );

  const handleItemClick = (item) => {
    setSelectedItem(item);
  };
  return (
    <div className="App">
      <h1 className="app-title hide-small">OpenAI Code Samples</h1>
      <ContainerLayout>
        <SidebarLayout className="hide-small">
          <div style={{ display: "flex", height: "100%", minHeight: "400px" }}>
            <Sidebar backgroundColor="#1d5268">
              <Menu
                menuItemStyles={{
                  button: ({ level, active, disabled }) => {
                    // only apply styles on first level elements of the tree
                    if (level === 0)
                      return {
                        color: disabled ? "gray" : "lightgray",
                        backgroundColor: active ? "#eecef9" : undefined,
                      };
                  },
                }}
              >
                <a href="https://openai.com/" target="_blank" rel="noreferrer">
                  <img
                    src="/OpenAI_Logo.png"
                    alt="OpenAI Logo"
                    className="app-logo"
                    style={{ position: "absolute", top: 0, left: 0 }}
                  />
                </a>
                <h5 className="sample-applications">Sample Applications</h5>
                <SubMenu label="Fun Apps" defaultOpen icon={<FaGamepad />}>
                  <MenuItem
                    onClick={() => handleItemClick(APPLICATIONS.SarcasticChat)}
                  >
                    {SarcasticChat.sidebar_title}
                  </MenuItem>
                </SubMenu>
                <hr />
                <MenuItem
                  icon={<FaInfo />}
                  onClick={() => handleItemClick("AboutPage")}
                >
                  About
                </MenuItem>
              </Menu>
            </Sidebar>
          </div>
        </SidebarLayout>
        <ContentLayout>
          {selectedItem === "AboutPage" && <AboutPage />}
          {selectedItem === APPLICATIONS.SarcasticChat && (
            <ChatApp {...SarcasticChat} />
          )}
        </ContentLayout>
      </ContainerLayout>
      <Footer />
    </div>
  );
};

export default App;
