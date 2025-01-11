// see: https://www.npmjs.com/package/styled-components
import styled from "styled-components";

export const ContainerLayout = styled.div`
  height: 89vh;
  display: flex;
  flex-direction: row;
`;

export const ContentLayout = styled.div`
  flex: 1;
  display: flex;
  flex-direction: row;
  margin: 0;
  padding: 0;
`;

export const ChatAppWrapper = styled.div`
  flex-basis: 33.33%;
  margin: 0;
  padding: 5px;
`;

export const ConsoleOutputWrapper = styled.div`
  flex-basis: 66.67%;
  padding: 5px;
  margin: 0;
  box-sizing: border-box; /* Ensure padding is included in the element's total width and height */
`;
