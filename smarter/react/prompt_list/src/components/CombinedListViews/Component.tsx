import type { Chatbot } from "@/lib/Types";
import { ListView } from "@/components/ListView/Component";
import type { SessionContext } from "@/lib/Types";

import "./styles.css";

interface CombinedListViewsProps {
  sessionContext: SessionContext;
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
}

function CombinedListViews({ sessionContext, chatbots }: CombinedListViewsProps) {
  return (
    <div>
      <div className={"list-view"}>
        {chatbots.user.length > 0 ? (
          <ListView
            sessionContext={sessionContext}
            title="Your Chatbots"
            chatbots={chatbots.user}
            cardClassName="mt-15"
          />
        ) : null}
        <ListView
          sessionContext={sessionContext}
          title="Shared Chatbots"
          chatbots={chatbots.shared}
          cardClassName={chatbots.user.length > 0 ? "mt-5" : "mt-15"}
        />
      </div>
    </div>
  );
}

export default CombinedListViews;
