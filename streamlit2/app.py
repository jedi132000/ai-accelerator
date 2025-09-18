import streamlit as st
import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

# --- Personality profiles ---
PERSONALITIES = {
    "Professional": {
        "emoji": "💼",
        "description": "Formal, structured, business-focused assistant",
        "system_prompt": (
            "You are a professional business assistant. Respond with formal, structured, business-focused advice. "
            "Use polite, efficient, and results-oriented tone. Expertise: business strategy, communication."
        ),
        "example": "I recommend a structured approach to managing client interactions: 1. Preparation 2. Active Listening 3. Solution-Focused Discussion..."
    },
    "Creative": {
        "emoji": "🎨",
        "description": "Imaginative, expressive creative helper",
        "system_prompt": (
            "You are a creative writing helper. Respond imaginatively for artistic, story-driven projects. "
            "Be enthusiastic, artistic, and encouraging. Expertise: storytelling, creative writing, artistic projects."
        ),
        "example": "Ah, the art of navigating stormy client waters! Picture this: you're weaving a story where everyone wins..."
    },
    "Technical": {
        "emoji": "🖥️",
        "description": "Precise, detailed, code-focused technical expert",
        "system_prompt": (
            "You are a technical expert. Respond with precise, detailed, code-focused explanations. "
            "Be analytical and educational. Expertise: programming, technology, problem-solving."
        ),
        "example": "To solve this, start by analyzing the requirements, then design a scalable architecture, and finally implement modular code with examples..."
    },
    "Friendly": {
        "emoji": "😊",
        "description": "Casual, supportive, conversational companion",
        "system_prompt": (
            "You are a friendly companion. Respond casually, warmly, and with conversational advice. "
            "Be supportive and empathetic. Expertise: general chat, emotional support, casual advice."
        ),
        "example": "That sounds tough, but I know you’ve got this! Let me know how I can help or if you just need to vent."
    },
    "Custom": {
        "emoji": "✨",
        "description": "User-defined personality",
        "system_prompt": "You are a helpful assistant with a custom style specified by the user below.",  # will be overwritten
        "example": "Custom personality response here."
    }
}

st.set_page_config(page_title="AI Personality Assistant", page_icon="🤖")  # Optional

# --- Sidebar personality selection and indicators ---

# --- URL-based personality persistence ---
query_params = st.query_params
if "personality" in query_params:
    url_personality = query_params["personality"]
    if url_personality in PERSONALITIES:
        st.session_state.current_personality = url_personality

if "current_personality" not in st.session_state:
    st.session_state.current_personality = "Friendly"
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("OpenAI Model Selection")
    openai_models = [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o"
    ]
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = openai_models[0]
    selected_model = st.selectbox("Model", openai_models, index=openai_models.index(st.session_state.openai_model))
    st.session_state.openai_model = selected_model
    st.header("🧑‍🎤 Choose Personality")
    persona_options = list(PERSONALITIES.keys())
    default_idx = persona_options.index(st.session_state.current_personality)
    personality = st.selectbox("Personality", persona_options, index=default_idx)
    st.session_state.current_personality = personality
    st.query_params["personality"] = personality

    persona = PERSONALITIES[personality]
    st.write(f"{persona['emoji']} **{personality}**: {persona['description']}")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("What each personality is good for:")
    for p_name, p in PERSONALITIES.items():
        st.markdown(f"<b>{p['emoji']} {p_name}</b>: {p['description']}", unsafe_allow_html=True)
        st.caption(f"_Example:_ {p['example']}")
    st.markdown("<hr>", unsafe_allow_html=True)
    if personality == "Custom":
        custom_prompt = st.text_area("Define your custom personality prompt:", value=st.session_state.get("custom_prompt", ""), height=100, help="Describe the style, tone, expertise, etc.")
        if custom_prompt and custom_prompt.strip():
            st.session_state["custom_prompt"] = custom_prompt
            persona["system_prompt"] = custom_prompt
        else:
            persona["system_prompt"] = PERSONALITIES["Custom"]["system_prompt"]

# --- Main area: Title and personality indicator ---
current_persona_obj = PERSONALITIES[st.session_state.current_personality]
st.title(f"🤖 AI Personality Assistant - {current_persona_obj['emoji']} {st.session_state.current_personality} Mode")
st.info(f"Responding as: {current_persona_obj['description']}")

# --- Detect personality switch and optionally add a system message ---
if st.session_state.messages:
    previous_persona = st.session_state.messages[-1].get('personality', st.session_state.current_personality)
else:
    previous_persona = st.session_state.current_personality

# Personality switching: allow mid-conversation changes and show in chat
if personality != previous_persona and st.session_state.messages:
    st.session_state.messages.append({
        "role": "system",
        "content": f"🔄 Switched to {personality} mode."
    })

# --- Chat input ---
user_input = st.text_input("Type your message...", key="chat_input")
if st.button("Send", type="primary") or (user_input and not st.session_state.get("submitted_once")):
    if user_input:
        # Store personality with message for accurate switch detection
        st.session_state.messages.append({"role": "user", "content": user_input, "personality": personality})

        # Compose messages for OpenAI API (system prompt, then full chat history, using current personality's prompt)
        current_persona = PERSONALITIES[personality]
        system_prompt = current_persona['system_prompt']
        messages = [{"role": "system", "content": str(system_prompt)}]
        for m in st.session_state.messages:
            if m["role"] in ("user", "assistant", "system"):
                messages.append({"role": m["role"], "content": str(m["content"])})

        # --- Call OpenAI Chat API --- (Fill in with your own key)
        openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else "sk-..."
        try:
            response = openai.chat.completions.create(
                model=st.session_state.openai_model,
                messages=messages
            )
            ai_response = response.choices[0].message.content
        except Exception as e:
            ai_response = f"Error: {e}"

        # Add AI response to history
        st.session_state.messages.append({"role": "assistant", "content": ai_response, "personality": personality})
        # Note: Do not directly reset st.session_state["chat_input"] after widget instantiation.
        # If you want to clear the input, use an on_change callback or st.experimental_rerun().
        st.session_state["submitted_once"] = True
    else:
        st.warning("Please enter a message to send.")

# --- Display chat history with persona indicators ---
st.markdown(f"<div style='font-size:1.3em; margin-bottom:10px;'><b>Current Personality:</b> {PERSONALITIES[personality]['emoji']} <b>{personality}</b></div>", unsafe_allow_html=True)
for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f"**You:** {m['content']}")
    elif m["role"] == "assistant":
        persona = PERSONALITIES[m.get('personality', st.session_state.current_personality)]
        st.markdown(f"**{persona['emoji']} {m.get('personality', personality)}:** {m['content']}")
    elif m["role"] == "system":
        st.info(m["content"])

# Optionally add a clear chat button
import io
import json
import csv
from datetime import datetime

# --- Export options ---
def get_metadata():
    return {
        "timestamp": datetime.now().isoformat(),
        "message_count": len(st.session_state.messages),
        "personality": st.session_state.current_personality,
        "session_info": {
            "custom_prompt": st.session_state.get("custom_prompt", "")
        }
    }

def export_txt():
    meta = get_metadata()
    lines = [f"Session Personality: {meta['personality']}", f"Timestamp: {meta['timestamp']}", f"Message Count: {meta['message_count']}"]
    lines.append("")
    for i, m in enumerate(st.session_state.messages, 1):
        role = m['role'].capitalize()
        persona = m.get('personality', meta['personality'])
        content = m['content']
        lines.append(f"[{i}] {role} ({persona}): {content}")
    return "\n".join(lines)

def export_json():
    meta = get_metadata()
    data = {
        "metadata": meta,
        "messages": st.session_state.messages
    }
    return json.dumps(data, indent=2)

def export_csv():
    meta = get_metadata()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session Personality", meta['personality']])
    writer.writerow(["Timestamp", meta['timestamp']])
    writer.writerow(["Message Count", meta['message_count']])
    writer.writerow([])
    writer.writerow(["Index", "Role", "Personality", "Content"])
    for i, m in enumerate(st.session_state.messages, 1):
        writer.writerow([i, m['role'], m.get('personality', meta['personality']), m['content']])
    return output.getvalue()

st.markdown("**Export Conversation:**")
st.download_button("Download TXT", export_txt(), file_name="chat_history.txt")
st.download_button("Download JSON", export_json(), file_name="chat_history.json")
st.download_button("Download CSV", export_csv(), file_name="chat_history.csv")
if st.button("Clear Conversation"):
    st.session_state.messages = []
    st.session_state["submitted_once"] = False

