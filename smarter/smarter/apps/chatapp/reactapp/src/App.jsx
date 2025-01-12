import React, { useContext } from "react";
import { ConfigProvider, ConfigContext } from "./ConfigContext.jsx";
import { ContainerLayout, ContentLayout } from "./components/Layout/";
import ChatApp from "./components/chatApp/Component";
import Console from "./components/console/Component";
import "./App.css";

const AppBase = () => {
  const { config } = useContext(ConfigContext);

  if (!config) {
    return <div>Loading...</div>;
  }

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

const App = () => (
  <ConfigProvider>
    <AppBase />
  </ConfigProvider>
);

export default App;
