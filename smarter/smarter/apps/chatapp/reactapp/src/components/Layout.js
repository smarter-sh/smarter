// see: https://www.npmjs.com/package/styled-components
import styled from "styled-components";

export const ContainerLayout = styled.div`
  height: 89vh;
  display: flex;
  flex-direction: row;
`;

export const ContentLayout = styled.div`
  flex: 1;
`;


export const Logo = styled.div`
  border-radius: 5%;
  position: absolute;
  bottom: 10px;
  left: 0;
  right: 0;
  display: block;
  margin: 0 auto;
  width: 90%;
  height: 125px;
  background-image: url("/youtube-banner-image.png");
  background-size: cover;
`;
