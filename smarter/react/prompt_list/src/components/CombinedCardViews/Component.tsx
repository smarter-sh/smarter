import type { Chatbot, SessionContext } from "@/lib/Types";
import { CardView } from "@/components/CardView/Component";
import { renderDetailRow } from "@/lib/renderDetail";

import "./styles.css";

interface CombinedCardViewsProps {
  sessionContext: SessionContext;
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
}

function CombinedCardViews({ sessionContext, chatbots }: CombinedCardViewsProps) {
  return (
    <div>
      <div className={"card-view"}>
        <section className="row g-5 g-xl-10 mb-l-10">
          {chatbots.user.length > 0 ? (
            <CardView
              sessionContext={sessionContext}
              title="Your Chatbots"
              chatbots={chatbots.user}
              cardClassName="mt-15"
              renderDetailRow={renderDetailRow}
            />
          ) : null}
          {chatbots.shared.length > 0 ? (
            <CardView
              sessionContext={sessionContext}
              title="Shared Chatbots"
              chatbots={chatbots.shared}
              cardClassName={chatbots.user.length > 0 ? "mt-5" : "mt-15"}
              renderDetailRow={renderDetailRow}
            />
          ) : null}
        </section>
      </div>
    </div>
  );
}

export default CombinedCardViews;
