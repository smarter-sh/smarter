// React code
import React from "react";
import { useState } from "react";

// Third party components
import {
  ContainerLayout,
  ContentLayout
} from "./components/Layout/";

// Our code
import "./App.css";
import ChatApp from "./components/chatApp/Component";
import Console from "./components/console/Component";

const App = ({ config }) => {

  if (config.debug_mode) {
    console.log("App() - config:", config);
  }

  return (
    <div id="smarter_chatapp_container" className="App">
      <ContainerLayout>
        <ContentLayout>
          <ChatApp config={config} />
          <Console config={config} />
        </ContentLayout>
      </ContainerLayout>
    </div>
  );
};

export default App;
