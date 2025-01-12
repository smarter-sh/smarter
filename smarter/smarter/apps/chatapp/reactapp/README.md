[![OpenAI](https://a11ybadges.com/badge?logo=openai)](https://platform.openai.com/)
[![ReactJS](https://a11ybadges.com/badge?logo=react)](https://react.dev/)

# React Client Application

This application implements the interactive chatbot in the web console. It is created with [React](https://react.dev/) leveraging [@chatscope/chat-ui-kit-react](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react) and [react-pro-sidebar](https://www.npmjs.com/package/react-pro-sidebar).

This app interacts with two api's from the [Smarter backend](https://github.com/smarter-sh/smarter):

## Backend integration

### Config

A Json dict containing all configuration data for the chatbot. This is downloaded at run-time when the reactapp is initializing.
Example: [/chatbots/example/config/?session_key=YOUR-SESSION-KEY](http://localhost:8000/chatbots/example/config/)

See: [sample config](../../../../../doc/json/reactapp.config.json)

### Api

A REST Api for sending and receiving chat prompt requests. The url comes from the config dict (above): data.chatbot.url_chatbot.
example: `http://localhost:8000/api/v1/chatbots/smarter/example/`

example http request:

```json
{
    "method": "POST",
    "credentials": "include",
    "mode": "cors",
    "headers": {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": "q9WXqqIhYJMI3ZSBIOE18JMORBMqAHri",
        "Origin": "http://localhost:8000",
        "Cookie": "session_key=a07593ecfaecd24008ca4251096732663ac0213b8cc6bdcce4f4c043276ab0b5;  _ga_2VG1QMYW93=GS1.1.1734966738.12.1.1734968666.60.0.0;  _ga=GA1.1.1265813193.1736184055;  sidebar_minimize_state=on;  debug=true;  _ga_SK81M5HQYS=GS1.1.1736531373.18.1.1736532907.0.0.0"
    },
    "body": "{\"session_key\":\"a07593ecfaecd24008ca4251096732663ac0213b8cc6bdcce4f4c043276ab0b5\",\"messages\":[{\"role\":\"system\",\"content\":\"You are a helpful chatbot."},{\"role\":\"assistant\",\"content\":\"Welcome to the Smarter demo!\"}]}"
}
```

example http response:

```json
{
    "data": {
        "isBase64Encoded": false,
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": "{\"id\": \"chatcmpl-AoDpMvoAhf8iSJuEm6pMqkX62HK4G\", \"choices\": [{\"finish_reason\": \"stop\", \"index\": 0, \"logprobs\": null, \"message\": {\"content\": \"Hello! While I'm not your mom, I'm here to help you with any questions or tasks you have. What can I assist you with today?\", \"refusal\": null, \"role\": \"assistant\", \"audio\": null, \"function_call\": null, \"tool_calls\": null}}], \"created\": 1736532916, \"model\": \"gpt-4-turbo-2024-04-09\", \"object\": \"chat.completion\", \"service_tier\": \"default\", \"system_fingerprint\": \"fp_f17929ee92\", \"usage\": {\"completion_tokens\": 33, \"prompt_tokens\": 1122, \"total_tokens\": 1155, \"completion_tokens_details\": {\"accepted_prediction_tokens\": 0, \"audio_tokens\": 0, \"reasoning_tokens\": 0, \"rejected_prediction_tokens\": 0}, \"prompt_tokens_details\": {\"audio_tokens\": 0, \"cached_tokens\": 0}}, \"metadata\": {\"tool_calls\": null, \"model\": \"gpt-4-turbo\", \"temperature\": 0.5, \"max_tokens\": 256, \"input_text\": \"hi mom\"}}"
    },
    "api": "smarter.sh/v1",
    "thing": "Chatbot",
    "metadata": {
        "command": "chat"
    }
}
```

## Getting Started

```console
make client-init
make client-run
```

## Architecture

- [Vite](https://vitejs.dev/)
- [React](https://react.dev/)
- [Chat UI Kit React](https://www.npmjs.com/package/@chatscope/chat-ui-kit-react)
- [React Pro Sidebar](https://www.npmjs.com/package/react-pro-sidebar)

## Requirements

- React 16.8+
- node 20.8+
- npm 10.1+

## Vite Scripts for React

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)

## Support

To get community support, go to the official [Issues Page](https://github.com/FullStackWithLawrence/aws-openai/issues) for this project.

## Contributing

We welcome contributions! There are a variety of ways for you to get involved, regardless of your background. In addition to Pull requests, this project would benefit from contributors focused on documentation and how-to video content creation, testing, community engagement, and stewards to help us to ensure that we comply with evolving standards for the ethical use of AI.

You can also contact [Lawrence McDaniel](https://lawrencemcdaniel.com/contact) directly.
