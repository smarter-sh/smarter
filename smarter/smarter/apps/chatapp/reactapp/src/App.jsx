// React code
import React from "react";
import { useState } from "react";

// Third party components
import {
  ContainerLayout,
  ContentLayout,
  ChatAppWrapper,
  ConsoleOutputWrapper,
} from "./components/Layout/";

// Our code
import "./App.css";
import ChatApp from "./components/chatApp/Component";
import ConsoleOutput from "./components/consoleOutput/Component";

// chatApp definitions
import { getSmarterSandbox } from "./applications/SmarterSandbox";

const App = ({ config }) => {

  if (!config) {
    return <div>Loading Config...</div>;
  }

  // const [selectedItem, setSelectedItem] = useState(
  //   config.APPLICATIONS.SmarterSandbox,
  // );

  if (config.debug_mode) {
    console.log("App() - config:", config);
  }

  return (
    <div className="App">
      <ContainerLayout>
        <ContentLayout>
          <ChatAppWrapper>
            <ChatApp {...getSmarterSandbox(config)} />
          </ChatAppWrapper>
          <ConsoleOutputWrapper>
            <ConsoleOutput config={config} />
          </ConsoleOutputWrapper>
        </ContentLayout>
      </ContainerLayout>
    </div>
  );
};

export default App;
