from ui.gradio_app import create_app
from dotenv import load_dotenv
load_dotenv()
if __name__ == "__main__":
    app = create_app()
    app.launch(share=True)

