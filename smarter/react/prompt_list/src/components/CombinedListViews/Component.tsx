import type { Chatbot } from "@/lib/Types";
import { ListView } from "@/components/ListView/Component";

import "./styles.css";

interface CombinedListViewsProps {
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
}

function CombinedListViews({ chatbots }: CombinedListViewsProps) {
  return (
    <div>
      <div className={"list-view"}>
        {chatbots.user.length > 0 ? (
          <ListView
            title="Your Chatbots"
            chatbots={chatbots.user}
            cardClassName="mt-15"
          />
        ) : null}
        <ListView
          title="Shared Chatbots"
          chatbots={chatbots.shared}
          cardClassName={chatbots.user.length > 0 ? "mt-5" : "mt-15"}
        />
      </div>
    </div>
  );
}

export default CombinedListViews;
