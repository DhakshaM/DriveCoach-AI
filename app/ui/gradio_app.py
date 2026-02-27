import gradio as gr
from ui.login_view import build_login_view
from ui.driver_view import build_driver_view
from ui.coach_view import build_coach_view
from backend.state import global_state
from backend.state.global_state import GLOBAL_STATE
from backend.llm.load_llm import load_llm_once
from ui.login_view import build_login_view, reset_login_fields

load_llm_once()

custom_css = """
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    min-height: 100vh;
}
.gradio-container {
    max-width: 1200px !important;
    margin: auto;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
}
h1, h2, h3 {
    color: #2c3e50;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}
.button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    padding: 10px 20px !important;
}
.button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
.input, .output {
    border-radius: 8px !important;
    border: 1px solid #ddd !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
}
.dropdown {
    background-color: #fff !important;
}
.login-box {
    background: white;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    max-width: 450px;
    margin: 50px auto;
}
.dashboard {
    animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
.logout-btn {
    background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
    color: white !important;
}
.login-btn {
    background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
    color: white !important;
    margin-top: 20px !important;
}
.logout-btn:hover {
    box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4) !important;
}
.center-header {
    text-align: center;
    margin-bottom: 20px;
    margin-top:30px;
}
.center-header_coach {
    text-align: center;
    margin-bottom: 5px;
}
.center-header_driver {
    text-align: center;
    margin-bottom: 20px;
}
.center-header_subtitle {
    text-align: center;
    margin-bottom: 10px;
}
.feedback-box {
    background: white;
    border-radius: 10px;
    border: none !important;
    margin-top: 10px;
    margin-bottom: 10px;
}
footer {
    display: none !important;
}

.fixed-width-container {
    width: 500px !important;
    max-width: 500px !important;
    min-width: 500px !important;
    margin: 0 auto !important;
}

.fixed-width-container > * {
    max-width: 100% !important;
}
"""

def route_after_login(user_id, role):
    print(f">>> ROUTER: user_id={user_id}, role={role}")
    global_state.current_user_id = user_id
    global_state.current_role = role
    print(">>> GLOBAL STATE CHECK")
    print("   user_id:", global_state.current_user_id)
    print("   role:", global_state.current_role)

    if role == "driver":
        GLOBAL_STATE.driver_login(driver_id=user_id, name=user_id)
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value=1),
            gr.update(value=0),
        )
    if role == "coach":
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value=0),
            gr.update(value=1),
        )
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=0),
        gr.update(value=0),
    )

def logout():
    print(">>> LOGOUT")
    user_id = global_state.current_user_id
    role = global_state.current_role
    if role == "driver":
        GLOBAL_STATE.driver_logout(user_id)
    global_state.current_user_id = None
    global_state.current_role = None
    return (
        None, None
    )

def create_app():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", secondary_hue="gray", radius_size="lg"), css=custom_css) as app:
        
        with gr.Column(visible=True) as login_col:
            user_id_state, role_state, username_box, password_box, error_box = build_login_view()


        with gr.Column(visible=False) as driver_col:
            driver_refresh_state, driver_logout_btn = build_driver_view()

        with gr.Column(visible=False) as coach_col:
            coach_refresh_state, coach_logout_btn = build_coach_view()

        role_state.change(
            fn=route_after_login,
            inputs=[user_id_state, role_state],
            outputs=[
                login_col,
                driver_col,
                coach_col,
                driver_refresh_state,
                coach_refresh_state,
            ],
            show_progress=False
        )

        driver_logout_btn.click(
            fn=lambda: (*logout(), *reset_login_fields()),
            inputs=[],
            outputs=[
                user_id_state,
                role_state,
                login_col,
                driver_col,
                coach_col,
                driver_refresh_state,
                coach_refresh_state,
                username_box,
                password_box,
                error_box
            ],
            show_progress=False
        )

        coach_logout_btn.click(
            fn=lambda: (*logout(), *reset_login_fields()),
            inputs=[],
            outputs=[
                user_id_state,
                role_state,
                login_col,
                driver_col,
                coach_col,
                driver_refresh_state,
                coach_refresh_state,
                username_box,
                password_box,
                error_box
            ],
            show_progress=False
        )


    return app