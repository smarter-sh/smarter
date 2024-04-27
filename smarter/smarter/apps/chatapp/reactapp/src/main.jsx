import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { fetchConfig, setConfig } from "./config.js";
import "./index.css";

function Main() {
  const [config, setConfigState] = useState(null);

  useEffect(() => {
    fetchConfig().then(config => setConfigState(setConfig(config)));
  }, []);

  return <App config={config} />;

}


ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Main />
  </React.StrictMode>,
);
