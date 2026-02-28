import gradio as gr
from backend.auth.auth_service import authenticate
from backend.state.global_state import GLOBAL_STATE

def reset_login_fields():
    return (
        gr.update(visible=True),   # login_col
        gr.update(visible=False),  # driver_col
        gr.update(visible=False),  # coach_col
        0,                          # driver_refresh_state
        0,                          # coach_refresh_state
        "",                         # username_box
        "",                         # password_box
        None                        # error_box
    )


def build_login_view():
    with gr.Column(elem_classes=["fixed-width-container"]):
        gr.Markdown("# DriveCoach AI", elem_classes=["center-header"])
        gr.Markdown("Drive smarter. Get real-time AI coaching for safer, smoother journeys.", elem_classes=["center-header_subtitle"])

        username_box = gr.Textbox(
            label="Username",
            placeholder="Enter username",
        )
        gr.HTML("<div style='height: 10px;'></div>")
        password_box = gr.Textbox(
            type="password",
            placeholder="Enter password",
            label="Password"
        )

        login_btn = gr.Button("Login", elem_classes=["login-btn"])

        error_box = gr.Markdown("", visible=False)

    user_id_state = gr.State(None)
    role_state = gr.State(None)

    def do_login(username, password):
        print(f">>> UI: login attempt for user={username}")
        user = authenticate(username, password)
        if user is None:
            print(">>> UI: login failed")
            return None, None, gr.update(value="❌ Invalid username or password", visible=True)

        success, role = user
        if not success:
            print(">>> UI: login failed (success=False)")
            return None, None, gr.update(value="❌ Authentication failed", visible=True)

        user_id = username
        print(f">>> UI: login success user_id={user_id} role={role}")

        if role == "driver":
            GLOBAL_STATE.driver_login(driver_id=user_id, name=user_id)

        return user_id, role, gr.update(visible=False)

    login_btn.click(
        fn=do_login,
        inputs=[username_box, password_box],
        outputs=[user_id_state, role_state, error_box],
        show_progress=False
    )
    username_box.submit(
        fn=do_login,
        inputs=[username_box, password_box],
        outputs=[user_id_state, role_state, error_box],
        show_progress=False
    )

    password_box.submit(
        fn=do_login,
        inputs=[username_box, password_box],
        outputs=[user_id_state, role_state, error_box],
        show_progress=False
    )
    
    return user_id_state, role_state, username_box, password_box, error_box


