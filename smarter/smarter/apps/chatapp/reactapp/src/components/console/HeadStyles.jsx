import React from 'react';
import { Helmet } from 'react-helmet';
import { REACT_LOCAL_DEV_MODE } from '../../constants';

// add Keen menu styles when we're in REACT_LOCAL_DEV_MODE
const HelmetHeadStyles = () => (
  <>
    <Helmet>
    {REACT_LOCAL_DEV_MODE && (
        <link
          href="/style.bundle.css"
          rel="stylesheet"
          type="text/css"
        />
      )}
    </Helmet>
  </>
);

export default HelmetHeadStyles;
