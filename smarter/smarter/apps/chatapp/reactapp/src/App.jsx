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
      <div style={{position: 'relative', display: 'flex', alignItems: 'center'}}>
        <a href="/" target="_self">
          <img
            src="https://www.querium.com/wp-content/uploads/2022/04/Querium-logo_white_transparency.png"
            style={{position: 'absolute', top: 0, left: 5, maxWidth: '285px', maxHeight: '50px'}} alt="logo" />
        </a>
        <h1 className="app-title hide-small">Smarter Sandbox</h1>
      </div>

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
