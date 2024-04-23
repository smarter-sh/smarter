import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { fetchConfig, setConfig } from "./config.js";
import "./index.css";

function Main() {
  console.log("Main() - entry point");
  const [config, setConfigState] = useState(null);

  useEffect(() => {
    console.log("Main() useEffect()");
    fetchConfig().then(config => setConfigState(setConfig(config)));
  }, []);

  console.log("Main() config:", config);

  return <App config={config} />;

}


ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Main />
  </React.StrictMode>,
);
