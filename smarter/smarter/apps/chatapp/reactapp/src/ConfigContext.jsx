import React, { createContext, useState, useEffect } from "react";
import { fetchConfig, setConfig } from "./config.js";

const ConfigContext = createContext();

const ConfigProvider = ({ children }) => {
  const [config, setConfigState] = useState(null);

  useEffect(() => {
    fetchConfig().then(config => setConfigState(setConfig(config)));
  }, []);

  const updateConfig = (newConfig) => {
    setConfigState(newConfig);
  };

  return (
    <ConfigContext.Provider value={{ config, updateConfig }}>
      {config === null ? <div>Loading...</div> : children}
    </ConfigContext.Provider>
  );
};

export { ConfigContext, ConfigProvider };
