// React code
import React from "react";
import { useState } from "react";

// Third party components
import {
  ContainerLayout,
  ContentLayout,
} from "./components/Layout/";

// Our code
import "./App.css";
import ChatApp from "./components/chatApp/Component";
import { APPLICATIONS } from "./config";

// chatApp definitions
import FunctionCalling from "./applications/FunctionCalling";
import SarcasticChat from "./applications/SarcasticChat";

const currentYear = new Date().getFullYear();

const Footer = () => {
  return (
    <div className="footer hide-small">
      <p>© {currentYear}{" "} Querium Corp. All rights reserved.</p>
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
      <h1 className="app-title hide-small">Smarter Sandbox</h1>
      <ContainerLayout>
        <ContentLayout>
          {selectedItem === APPLICATIONS.SarcasticChat && (
            <ChatApp {...SarcasticChat} />
          )}
        </ContentLayout>
        <ContentLayout>
          {selectedItem === APPLICATIONS.FunctionCalling && (
            <ChatApp {...FunctionCalling} />
          )}
        </ContentLayout>
      </ContainerLayout>
      <Footer />
    </div>
  );
};

export default App;
