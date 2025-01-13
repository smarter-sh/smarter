import React from "react";
import { ContainerLayout, ContentLayout } from "./components/Layout/";
import ChatApp from "./components/chatApp/Component";
import Console from "./components/console/Component";
import "./App.css";


const App = () => {

  return (
    <div id="smarter_chatapp_container" className="App">
      <ContainerLayout>
        <ContentLayout>
          <ChatApp />
        </ContentLayout>
      </ContainerLayout>
    </div>
  );

};

export default App;
