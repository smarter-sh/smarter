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

// chatApp definitions
import { getSmarterSandbox } from "./applications/SmarterSandbox";
import { getOpenaiPassthrough } from "./applications/OpenaiPassthrough";
import { getLangchainPassthrough } from "./applications/LangchainPassthrough";

const App = ({ config }) => {

  if (!config) {
    return <div>Loading Config...</div>;
  }

  const [selectedItem, setSelectedItem] = useState(
    config.APPLICATIONS.SmarterSandbox,
  );

  return (
    <div className="App">
      <ContainerLayout>
        <ContentLayout>
          {selectedItem === config.APPLICATIONS.SmarterSandbox && (
            <ChatApp {...getSmarterSandbox(config)} />
          )}
        </ContentLayout>
        <ContentLayout>
          {selectedItem === config.APPLICATIONS.OpenaiPassthrough && (
            <ChatApp {...getOpenaiPassthrough(config)} />
          )}
        </ContentLayout>
        <ContentLayout>
          {selectedItem === config.APPLICATIONS.LangchainPassthrough && (
            <ChatApp {...getLangchainPassthrough(config)} />
          )}
        </ContentLayout>
      </ContainerLayout>
    </div>
  );
};

export default App;
