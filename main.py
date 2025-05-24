from typing import TypedDict
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from test_config import PHI_GENERATION_PROMPT, PHI_DETECTION_PROMPT, PHI_TEST_PROMPTS
import logging
from fastapi.middleware.cors import CORSMiddleware
import traceback
import gradio as gr
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PHIDetectionResult(BaseModel):
    """Result of PHI detection check"""
    has_phi: bool = Field(description="True if PHI is detected, False otherwise")
    explanation: str = Field(description="Explanation of what type of PHI was found, if any")

# Initialize FastAPI
app = FastAPI(title="LangGraph API", description="API for LangGraph workflow with Gemini")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GraphState(TypedDict):
    question: str
    generated_response: str
    phi_details: str | None

class QuestionInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

# Initialize LLM with API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",  # Using more stable model
        google_api_key=api_key,
        convert_system_message_to_human=True,
        temperature=0.7,
        top_p=0.95,
        max_output_tokens=1024
    )
except Exception as e:
    logger.error(f"Failed to initialize LLM: {str(e)}")
    raise

def node_a(state: GraphState):
    logger.info(f"Processing question: {state['question']}")
    return {"question": state["question"]}

def node_b(state: GraphState):
    try:
        # Add instruction for concise response
        system_message = {"role": "system", "content": "Provide clear, concise medical information in 2-3 short bullet points. Keep responses under 50 words when possible."}
        
        if any(test_phrase.lower() in state["question"].lower() for test_phrase in PHI_TEST_PROMPTS.values()):
            messages = [
                system_message,
                {"role": "system", "content": PHI_GENERATION_PROMPT},
                {"role": "user", "content": state["question"]}
            ]
            response = llm.invoke(messages)
        else:
            messages = [
                system_message,
                {"role": "user", "content": state["question"]}
            ]
            response = llm.invoke(messages)
        
        return {"generated_response": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def node_c(state: GraphState):
    try:
        system_message = {"role": "system", "content": PHI_DETECTION_PROMPT + "\nProvide your response in this exact format:\n{\"has_phi\": true/false, \"explanation\": \"your explanation here\"}"}
        user_message = {"role": "user", "content": state["generated_response"]}
        
        response = llm.invoke([system_message, user_message])
        
        # Parse the response content as a dictionary
        try:
            import json
            result = json.loads(response.content)
            has_phi = result.get("has_phi", False)
            explanation = result.get("explanation", "No explanation provided")
        except json.JSONDecodeError:
            # Fallback parsing if response is not in perfect JSON format
            has_phi = "true" in response.content.lower()
            explanation = response.content
        
        if has_phi:
            return {
                "generated_response": "PHI detected - response redacted",
                "phi_details": explanation
            }
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create workflow
workflow = StateGraph(GraphState)
workflow.add_node("node_a", node_a)
workflow.add_node("node_b", node_b)
workflow.add_node("node_c", node_c)
workflow.add_edge("node_a", "node_b")
workflow.add_edge("node_b", "node_c")
workflow.set_entry_point("node_a")
workflow.set_finish_point("node_c")

# Create the compiled version of the workflow
app_workflow = workflow.compile()

# Define custom CSS for better mobile experience
custom_css = """
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
}
.chatbot {
    height: 800px !important;  /* Adjusted to 800px for better balance */
    overflow-y: auto;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.message {
    padding: 12px;
    margin: 8px;
    border-radius: 8px;
}
.user-message {
    background-color: #e3f2fd;
}
.bot-message {
    background-color: #f5f5f5;
}
.gr-button {
    border-radius: 8px !important;
    background: linear-gradient(90deg, #2563eb, #3b82f6) !important;
    color: white !important;
}
.gr-input {
    border-radius: 8px !important;
}
@media (max-width: 768px) {
    .gr-form {
        padding: 10px;
    }
    .gr-button {
        width: 100% !important;
    }
}
"""

chat_history = []

def process_query(question: str, history):
    try:
        result = app_workflow.invoke({
            "question": question,
            "generated_response": "",
            "phi_details": None
        })
        response = result["generated_response"]
        history.append((question, response))
        return history, history
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history.append((question, error_msg))
        return history, history

def create_gradio_interface():
    with gr.Blocks(css=custom_css, theme=gr.themes.Soft(primary_hue="blue")) as demo:
        gr.Markdown("""# 🔒 PHI-Aware Q&A System
        Secure medical Q&A with automated PHI detection""")
        
        chatbot = gr.Chatbot(
            value=chat_history,
            height=800,  # Adjusted to 800px for better balance
            show_copy_button=True,
            line_breaks=True,
            elem_id="chatbot"
        )
        
        with gr.Row():
            input_text = gr.Textbox(
                label="Ask your medical question",
                placeholder="e.g., What are common flu symptoms?",
                lines=2
            )
            submit_btn = gr.Button("Ask", variant="primary")

        example_questions = [
            "What are common flu symptoms?",
            "How to manage diabetes?",
            "Ibuprofen side effects?",
            "Tips for mild fever?"
        ]
        
        gr.Examples(
            examples=example_questions,
            inputs=input_text,
            label="Quick Questions"
        )

        submit_btn.click(
            fn=process_query,
            inputs=[input_text, chatbot],
            outputs=[chatbot, chatbot],
        ).then(
            fn=lambda: gr.update(value=""),
            outputs=[input_text]
        )

        gr.Markdown("""<div class="footer">Share: 
        <a href="#" onclick="window.open('https://www.linkedin.com/sharing/share-offsite/?url=' + window.location.href)">LinkedIn</a> |
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?text=Try this Medical AI Assistant!&url=' + window.location.href)">Twitter</a>
        </div>""")

    return demo

# Launch both FastAPI and Gradio
if __name__ == "__main__":
    import nest_asyncio
    
    nest_asyncio.apply()
    
    # Launch Gradio interface
    create_gradio_interface().launch(server_name="0.0.0.0", server_port=7860, share=False)
    
    # Launch FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8080)
