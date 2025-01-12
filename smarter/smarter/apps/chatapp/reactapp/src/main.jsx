import React, { useContext } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { ConfigProvider, ConfigContext } from "./ConfigContext.jsx";
import "./index.css";

function ConfigConsumer() {
  const { config } = useContext(ConfigContext);

  return config ? <App config={config} /> : <div>Loading...</div>;
}

function Main() {
  return (
    <ConfigProvider>
      <ConfigConsumer />
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById("smarter_chatapp_root")).render(
  <React.StrictMode>
    <Main />
  </React.StrictMode>,
);
