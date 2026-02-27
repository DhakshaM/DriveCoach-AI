# Fleet Management LLM Dashboard – Gradio App
LLM-powered driving behavior analysis using sensor data.

## File Structure:
```
driving-coach-app/
│
├── README.md
├── .env.example
├── .gitignore
│
└── app/
    │
    ├── main.py                         
    ├── requirements.txt
    │
    ├── backend/
    │   │
    │   ├── auth/
    │   │   ├── auth_service.py         # Prompting + inference wrapper
    │   │   ├── seed_users.py           # Create users
    │   │   └── user_registry.py        # Empty file
    │   │
    │   ├── llm/
    │   │   ├── llm_engine.py          # Prompting + inference wrapper
    │   │   ├── load_llm.py            # Loads GGUF model once
    │   │   └── driving-coach-f16.gguf # (optional, large file – gitignored)
    │   │
    |   ├── processing/
    |   |   ├── merger.py              # CSV Merger merging and segment extraction
    │   │   └── severity.py            # Severity labels for Sensor Summary
    |   |
    │   ├── registry/
    │   │   └── trip_registry.py       # Trip + segment processing logic
    │   │
    │   ├── services/
    │   │   ├── driver_services.py     # Driver-facing operations
    │   │   └── coach_services.py      # Coach/fleet-facing operations
    │   │   
    │   └── state/
    │       └── global_state.py        # Logged-in users & online status
    │  
    │
    ├── ui/
    │   │
    │   ├── gradio_app.py              # App layout + routing
    │   ├── login_view.py              # Login UI
    │   ├── driver_view.py             # Driver dashboard UI
    │   └── coach_view.py              # Coach dashboard UI
    │   
    │
    └── data/
        │
        ├── users.csv                  # Seed users (auth)
        │
        └── trips/
            │
            ├── driver_01/
            │   ├── trip_001/
            │   |   ├── location_data.csv
            │   |   ├── accelerometer_data.csv
            │   |   └── gyroscope_data.csv
            |   |
            │   └── trip_002/
            │       ├── location_data.csv
            │       ├── accelerometer_data.csv
            │       └── gyroscope_data.csv   
            │
            ├── driver_02/
            │   └── trip_001/
            │       └── ...
            │
            └── ...
```

## Requirements:
Python 3.10+

pip (pip install -r requirements.txt)

8GB+ RAM recommended

Local GGUF model (not included) - https://www.kaggle.com/datasets/amudhans07/finetuning-toolkit
