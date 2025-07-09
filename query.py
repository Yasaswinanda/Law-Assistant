import os
import google.generativeai as genai
import ast

class QueryBuilder:
    def __init__(self):
        """
        Initializes the Google Gemini API client using API key from environment variable.
        """
        api_key = os.environ.get("GEMINI_API_KEY_QUERY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY_QUERY not set in environment variables.")
        genai.configure(api_key=api_key)
    
    def convert_query(self, text: str):
        text = text.strip()
        array_response = text.split("```")

        for i in array_response:
            i = i.strip("python") #remove python after the start of code block
            if isinstance(i, str) and i.strip().startswith('[') and i.strip().endswith(']'):
                try:
                    return ast.literal_eval(i)
                except Exception as ex:
                    print("Exception in query.py (convert query) : ", ex)
        print("DEBUG : Invalid")
        return "Invalid"

                  

    def get_and_process_query(self, topic: str, number_of_queries: int = 10) -> str:
        """
        Sends the user's query to the Gemini model and returns the processed text response.
        """
        SYSTEM_PROMPT = """
    Act as an **expert note-taker and tutor**. You are researching on the topics from a vector database. 
    You are to query the vector database for generating appropriate answers for the given topic.
    There are few rules you must follow : 
    1. The number of queries is limited and the number is provided by the user.
    2. You must privide the response in a code block as a list parsable in pyton.
    3. You must never exceed that given number.
    4. Very crutial that you give the code block as the below example : 
        ```
        ["Query 1", "Query 2", ...] 
        ```
    Remember to not give anything other than this. There should be nothing after the code block start other than the actual list.
    Bad / unwanted / rejected responses are :
    -    ```python
        ["Query 1", "Query 2", ...] 
        ``` 

    -   Sure here is the requested list : 
        ```
        ["Query 1", "Query 2", ...] 
        ```
    -   Sure here is the requested list : 
        ```python
        ["Query 1", "Query 2", ...] 
        ```

    NOTE : Do NOT prefix the code block with `python` or any language tag. Only use ``` + list + ```.
        """
        model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 0.65,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            },
        )
        
        chat = model.start_chat(history=[])
        response = chat.send_message([
            SYSTEM_PROMPT,
            f"Topic : {topic}, Number of queries: {number_of_queries}"
        ])

        print("\nDEBUG : (Returned response)", response.text)

        result_list = self.convert_query(response.text)
        return result_list


if __name__ == "__main__":
    client = QueryBuilder()
    test_queries = [
        "Explain register allocation strategies.",
        "What is peephole optimization?",
        "How do cross-compilers work?",
        "What is bootstrapping in compiler design?",
        "Explain self-hosting compilers with an example.",
        "What is the role of linkers and loaders in compilation?",
        "Explain garbage collection strategies in runtime environments.",
        "What is the impact of intermediate representation choice on performance?",

        # 🧩 MULTI-QUESTION STRINGS
        "Explain dead code elimination and constant folding. How are they implemented?",
        "What is loop unrolling? Give examples and explain its effect on performance.",
        "What is the difference between Lex and Flex? When should I use each?",
        "Compare LL(1) and LR(1) parsers — what are the pros and cons?",
        "What are syntax-directed translation schemes? How are they used in semantic analysis?",
        "Explain SSA form and how it helps with optimizations. What tools generate SSA?",
    ]
    for query in test_queries:
        print("Query :", query)
        result = client.get_and_process_query(query)
        for i, text in enumerate(result):
            print(f"{i} : {text}")
        
        print('-' * 15)