import React, { useContext } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { ConfigProvider, ConfigContext } from "./ConfigContext.jsx";
import "./index.css";

function Main() {
  return (
    <ConfigProvider>
      <ConfigConsumer />
    </ConfigProvider>
  );
}

function ConfigConsumer() {
  const { config } = useContext(ConfigContext);

  return config ? <App config={config} /> : <div>Loading...</div>;
}

ReactDOM.createRoot(document.getElementById("smarter_chatapp")).render(
  <React.StrictMode>
    <Main />
  </React.StrictMode>,
);
