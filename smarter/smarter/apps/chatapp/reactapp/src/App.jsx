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
import SmarterSandbox from "./applications/SmarterSandbox";
import OpenaiPassthrough from "./applications/OpenaiPassthrough";
import LangchainPassthrough from "./applications/LangchainPassthrough";

const App = () => {
  const [selectedItem, setSelectedItem] = useState(
    APPLICATIONS.SmarterSandbox,
  );

  return (
    <div className="App">
      <ContainerLayout>
        <ContentLayout>
          {selectedItem === APPLICATIONS.SmarterSandbox && (
            <ChatApp {...SmarterSandbox} />
          )}
        </ContentLayout>
        <ContentLayout>
          {selectedItem === APPLICATIONS.OpenaiPassthrough && (
            <ChatApp {...OpenaiPassthrough} />
          )}
        </ContentLayout>
        <ContentLayout>
          {selectedItem === APPLICATIONS.LangchainPassthrough && (
            <ChatApp {...LangchainPassthrough} />
          )}
        </ContentLayout>
      </ContainerLayout>
    </div>
  );
};

export default App;
