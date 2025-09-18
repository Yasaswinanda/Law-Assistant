# agents.py
from typing import Dict, Any, Iterator, Optional, List
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # 👈 add MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import create_retriever_tool
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI

AGENT_SYSTEM = """You are a helpful assistant that provides whatever the user needs (About the case). You are free to give legal advice until you can site the sources from the given tools.
You MUST use the 'cases_retriever' tool repeatedly to gather evidence before answering.
Prioritize precision and cite sources with (filename p.#).
If the user provided a document, treat it as primary context but DO NOT store it.
Keep answers concise, bulleted where helpful, and include a brief rationale at the end.

You have access to the following tools:
{tools}

When you need information, reason step by step and, if needed, call a tool.
Use this exact format:

Thought: what the user is asking about.
Action: use one of [{tool_names}] if it is needed for answering the query of the user. If not then dont need to use it. Also you can use this tool as many times as you need. 
Observation and thought : the tool result is it enough for me? Is this answering the user's query? If not how can I answer it?

Repeat Thought/Action/Action Input/Observation as needed.
When you have enough information, respond with:

Final Answer: <your answer in as much or as little detail as required. Do not make up your own data for these answers. Try to give bullet points and a breef rationale at the end>

Important:
- Always search first with the retriever before concluding (if the user's query requires it).
- Cite each key fact like (source.pdf p.3).
- The user has no knowledge of the tools or anything in the backend. The user only knows the case they have uploaded and what you tell. 
- Do not disclose the workings of the backend to the user."""

TOOL_DESC = (
    "Use this to search preprocessed case sheets. "
    "Supply a focused query (symptoms, diagnosis term, lab markers). "
    "It returns the most relevant chunks with metadata such as filename and page."
)

class AgentOrchestrator:
    def __init__(self, gemini_api_key: str, vector_store):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.7,
        )

        self.vector_store = vector_store
        self.retriever = vector_store.as_retriever(search_kwargs={"k": 6})

        # Make memory explicit about the input and key LC expects
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="input",          # 👈 important with AgentExecutor
            return_messages=True
        )

        self.tool = create_retriever_tool(
            retriever=self.retriever,
            name="cases_retriever",
            description=TOOL_DESC,
        )

        # Use MessagesPlaceholder for BOTH placeholders
        prompt = ChatPromptTemplate.from_messages([
            ("system", AGENT_SYSTEM),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}\n\n{user_doc_hint}"),
            ("ai", "{agent_scratchpad}"),
        ])


        self.agent = create_react_agent(
            llm=self.llm,
            tools=[self.tool],
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=[self.tool],
            memory=self.memory,
            verbose=False,
            handle_parsing_errors=True,
        )

    def update_retriever(self, new_retriever):
        self.retriever = new_retriever

    def _make_user_doc_hint(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return f"<USER_DOCUMENT_BEGIN>\n{text}\n<USER_DOCUMENT_END>"

    def answer(
        self,
        user_message: str,
        session_id: Optional[str],
        user_doc_text: Optional[str],
        top_k: int
    ) -> Dict[str, Any]:
        self.retriever.search_kwargs["k"] = int(top_k)

        inputs = {
            "input": user_message,
            "user_doc_hint": self._make_user_doc_hint(user_doc_text),
        }

        out = self.executor.invoke(inputs)

        retrieved: List[Document] = self.retriever.invoke(user_message)
        cites = []
        for d in retrieved[:top_k]:
            meta = d.metadata or {}
            cites.append({
                "filename": meta.get("source") or meta.get("filename"),
                "page": meta.get("page"),
                "score": meta.get("score"),
            })

        return {
            "session_id": session_id,
            "answer": out.get("output", out),
            "citations": cites,
        }

    def stream_answer(
        self,
        user_message: str,
        session_id: Optional[str],
        user_doc_text: Optional[str],
        top_k: int
    ) -> Iterator[str]:
        self.retriever.search_kwargs["k"] = int(top_k)

        inputs = {
            "input": user_message,
            "user_doc_hint": self._make_user_doc_hint(user_doc_text),
        }

        config = RunnableConfig(configurable={"session_id": session_id or "default"})
        for event in self.executor.stream(inputs, config=config):
            try:
                yield event.model_dump_json()
            except AttributeError:
                import json
                yield json.dumps(event)
