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
`;

export const ChatAppWrapper = styled.div`
  flex-basis: 33.33%;
`;

export const ConsoleOutputWrapper = styled.div`
  flex-basis: 66.67%;
  padding: 10px; /* Add padding to ensure content is not pushed against the right side */
  box-sizing: border-box; /* Ensure padding is included in the element's total width and height */
`;
