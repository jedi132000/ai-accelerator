import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load model and tokenizer only once (using smaller model for faster startup)
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")

def gen_reply(user_message, history):
    """Generate a response using DialoGPT with proper attention masking and message format.
    
    Args:
        user_message: str, the user's input message
        history: list of dicts with keys: role, content, chat_history_ids (optional)
    Returns:
        tuple: (empty input, display messages, full history with ids)
    """
    # Encode with attention mask (1s for all tokens since we want to attend to all)
    inputs = tokenizer(
        user_message + tokenizer.eos_token,
        return_tensors='pt',
        add_special_tokens=True,
        return_attention_mask=True
    )
    new_user_input_ids = inputs.input_ids
    attention_mask = inputs.attention_mask

    # Get previous context if available
    if history and isinstance(history[-1], dict) and 'chat_history_ids' in history[-1]:
        chat_history_ids = torch.tensor(history[-1]['chat_history_ids'])
        # Extend attention mask for history
        attention_mask = torch.cat([torch.ones_like(chat_history_ids), attention_mask], dim=-1)
    else:
        chat_history_ids = None

    # Combine history with new input if we have it
    if chat_history_ids is not None:
        bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1)
    else:
        bot_input_ids = new_user_input_ids

    # Generate response with attention mask
    chat_history_ids = model.generate(
        bot_input_ids,
        attention_mask=attention_mask,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True,
        temperature=0.7  # Add some variety to responses
    )

    # Decode ONLY the new tokens (skip input context)
    reply = tokenizer.decode(
        chat_history_ids[:, bot_input_ids.shape[-1]:][0],
        skip_special_tokens=True
    )

    # Save messages in new format with chat history
    history.append({
        "role": "user",
        "content": user_message,
        "chat_history_ids": chat_history_ids.tolist()
    })
    history.append({
        "role": "assistant",
        "content": reply
    })

    # Format display messages for Gradio's Chatbot (messages format)
    display_history = [
        {"role": turn["role"], "content": turn["content"]}
        for turn in history if "role" in turn
    ]
    
    return "", display_history, history

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(
        label="DialoGPT Chat",
        type="messages",  # Use OpenAI-style message format
        height=400
    )
    state = gr.State([])  # holds detailed history (with chat_history_ids for context)
    txt = gr.Textbox(
        placeholder="Say something...",
        show_label=False,
        container=False
    )
    txt.submit(gen_reply, [txt, state], [txt, chatbot, state])
    gr.Markdown("""
    Chat with DialoGPT-small (faster, smaller model)
    - History persists until reload
    - Uses attention masking for better responses
    """)

demo.launch()
