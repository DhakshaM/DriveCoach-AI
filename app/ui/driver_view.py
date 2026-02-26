import gradio as gr
from backend.state import global_state
from backend.services.driver_services import load_segment_severities_for_stream
from backend.processing.severity import build_llm_summary
from backend.llm.llm_engine import get_coaching_feedback
from pathlib import Path
from backend.registry.trip_registry import TripRegistry
from backend.db.db_writer import log_driver_response
import threading

TRIPS_ROOT = Path("data/trips")
_registry = TripRegistry(TRIPS_ROOT)
MAX_SEGMENTS = 15
_llm_lock = threading.Lock() 
_segment_results = {}  # keyed by (driver_id, trip_id, idx) — never goes through gr.State

def start_llm_for_segment(idx, summaries, llm_result_holder, driver_id=None, trip_id=None, segments=None):
    def _run():
        with _llm_lock:
            summary = summaries[idx]
            coaching = get_coaching_feedback(summary)
            llm_result_holder["result"] = coaching  # keep for backward compat

            # Also store in module-level dict — immune to gr.State copying
            if driver_id and trip_id:
                _segment_results[(driver_id, trip_id, idx)] = coaching

            if driver_id and trip_id and segments and idx < len(segments):
                try:
                    severity = segments[idx]["severity"]
                    log_driver_response(
                        driver_id=driver_id,
                        trip_id=trip_id,
                        segment_index=int(idx),
                        severity=severity,
                        summary=summary,
                        coaching=coaching,
                    )
                    print(f"[DB_WRITER] Queued segment {idx} for driver {driver_id}")
                except Exception as e:
                    print(f"[DB_WRITER] log_driver_response error (non-fatal): {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

def build_driver_view():
    with gr.Column(elem_classes=["fixed-width-container"]):
        gr.Markdown("# Driver Dashboard", elem_classes=["center-header_driver"])
        gr.Markdown("Live feedback about driving behaviour.")
        gr.Markdown("---")
        start_btn = gr.Button("Start Trip", variant="primary")
        stop_btn = gr.Button("Stop Trip", variant="secondary")

        segment_dropdown = gr.Dropdown(
            choices=["Waiting for stream..."],
            label="Current Trip",
            interactive=False
        )
        gr.Markdown("---")
        
        output_box = gr.HTML("<h3>Driving Behaviour Feedback</h3>", elem_classes=["feedback-box"], visible=True)


    current_trip_state = gr.State(None)
    next_llm_idx_state = gr.State(None)
    next_llm_result_state = gr.State(None)
    segment_summaries_state = gr.State(None)
    segment_stream_state = gr.State([])   # list of severities
    segment_pointer_state = gr.State(0)   # current index
    streaming_state = gr.State(False)
    trip_df_state = gr.State(None)
    refresh_state = gr.State(0)
    def start_streaming():
        driver_id = global_state.current_user_id
        print(f">>> DRIVER VIEW: starting stream for driver={driver_id}")

        if not driver_id:
            return [], 0, None, None, gr.update(choices=["Waiting for stream..."], value="Waiting for stream..."), gr.update(value="<h3>Driving Behaviour Feedback</h3><p>❌ No driver ID</p>"), False

        driver_dir = TRIPS_ROOT / driver_id
        if not driver_dir.exists():
            return [], 0, None, None, gr.update(choices=["Waiting for stream..."], value="Waiting for stream..."), gr.update(value="<h3>Driving Behaviour Feedback</h3><p>❌ No trips directory</p>"), False

        raw_trips = sorted([p.name for p in driver_dir.iterdir() if p.is_dir()])
        if not raw_trips:
            return [], 0, None, None, gr.update(choices=["Waiting for stream..."], value="Waiting for stream..."), gr.update(value="<h3>Driving Behaviour Feedback</h3><p>❌ No trips available</p>"), False

        trip_id = raw_trips[0]  # Implicitly use the first trip as "day 1"
        df = _registry._load_trip_df(driver_id, trip_id)
        segments = load_segment_severities_for_stream(driver_id, trip_id)
        summaries = {
            i: build_llm_summary(df.iloc[i].to_dict())
            for i in range(len(segments))
        }
        if not segments:
            return [], 0, None, None, gr.update(choices=["Waiting for stream..."], value="Waiting for stream..."), gr.update(value="<h3>Driving Behaviour Feedback</h3><p>❌ No Trips</p>"), False

        first_seg = segments[0]
        severity = first_seg["severity"]

        label = f"Segment 1 — Severity: {severity}"
        dropdown_update = gr.update(choices=[label], value=label)
        feedback_update = gr.update()

        # 🔑 SEED LLM PIPELINE FOR FIRST SEGMENT
        holder = {"result": None}
        start_llm_for_segment(0, summaries, holder, driver_id=driver_id, trip_id=trip_id, segments=segments)
                

        return (
            segments,            # segment_stream_state
            0,                   # segment_pointer_state
            trip_id,             # current_trip_state
            dropdown_update,     # segment_dropdown
            feedback_update,     # output_box
            True,                 # streaming_state (start streaming)
            df,
            summaries,
            0,
            holder
        )

    def stop_streaming():
        return (
            [],                  # segment_stream_state
            0,                   # segment_pointer_state
            None,                # current_trip_state
            gr.update(choices=["Waiting for stream..."], value="Waiting for stream..."),  # segment_dropdown
            gr.update(value="<h3>Driving Behaviour Feedback</h3>"),  # output_box
            False,                # streaming_state (stop streaming)
            None
        )


    def advance_segment_stream(segments, idx, trip_id, streaming, df, summaries, next_llm_idx, next_llm_result):
        if not streaming or not segments:
            return idx, gr.update(), gr.update(), next_llm_idx, next_llm_result

        seg = segments[idx]
        severity = seg["severity"]
        label = f"Segment {idx + 1} — Severity: {severity}"
        dropdown_update = gr.update(choices=[label], value=label)
        feedback_update = gr.update()

        # Check if current segment's result is ready
        driver_id = global_state.current_user_id
        result_ready = (
            driver_id and trip_id and
            (driver_id, trip_id, idx) in _segment_results
        )

        if result_ready:
            # Display it
            feedback_update = gr.update(
                value=(
                    "<h3>Driving Behaviour Feedback</h3>"
                    f"<p>{_segment_results[(driver_id, trip_id, idx)]}</p>"
                )
            )
            next_idx = min(idx + 1, len(segments) - 1)

            # Start LLM for next_idx immediately so it's ready when timer ticks
            if next_idx != idx and (driver_id, trip_id, next_idx) not in _segment_results:
                start_llm_for_segment(
                    next_idx, summaries, {"result": None},
                    driver_id=driver_id,
                    trip_id=trip_id,
                    segments=segments
                )

            return next_idx, dropdown_update, feedback_update, next_idx, next_llm_result

        else:
            # Result not ready yet — stay on same idx, start LLM for current if not started
            if next_llm_idx != idx:
                holder = {"result": None}
                start_llm_for_segment(
                    idx, summaries, holder,
                    driver_id=global_state.current_user_id,
                    trip_id=trip_id,
                    segments=segments
                )
                return idx, dropdown_update, feedback_update, idx, holder

            return idx, dropdown_update, feedback_update, next_llm_idx, next_llm_result
    
    def reset_driver_view():
        return (
            [],                                  # segment_stream_state
            0,                                   # segment_pointer_state
            None,                                # current_trip_state
            gr.update(
                choices=["Waiting for stream..."],
                value="Waiting for stream..."
            ),                                   # segment_dropdown
            gr.update(
                value="<h3>Driving Behaviour Feedback</h3>"
            ),                                   # output_box
            False,                               # streaming_state
            None,                                # trip_df_state
            None,                                # segment_summaries_state
            None,                                # next_llm_idx_state
            None                                 # next_llm_result_state
        )

    start_btn.click(
        fn=start_streaming,
        inputs=[],
        outputs=[
            segment_stream_state,
            segment_pointer_state,
            current_trip_state,
            segment_dropdown,
            output_box,
            streaming_state,
            trip_df_state,
            segment_summaries_state,
            next_llm_idx_state,
            next_llm_result_state
        ],
        show_progress=False
    )
    stop_btn.click(
        fn=stop_streaming,
        inputs=[],
        outputs=[
            segment_stream_state,
            segment_pointer_state,
            current_trip_state,
            segment_dropdown,
            output_box,
            streaming_state,
            trip_df_state
        ],
        show_progress=False
    )
    refresh_state.change(
        fn=reset_driver_view,
        inputs=[],
        outputs=[
            segment_stream_state,
            segment_pointer_state,
            current_trip_state,
            segment_dropdown,
            output_box,
            streaming_state,
            trip_df_state,
            segment_summaries_state,
            next_llm_idx_state,
            next_llm_result_state
        ],
        show_progress=False
    )


    logout_btn = gr.Button("Logout", elem_classes=["logout-btn"])

    STREAM_INTERVAL_SEC = 15.0  # 🔧 adjust freely

    gr.Timer(STREAM_INTERVAL_SEC).tick(
        fn=advance_segment_stream,
        inputs=[
            segment_stream_state,
            segment_pointer_state,
            current_trip_state,
            streaming_state,
            trip_df_state,
            segment_summaries_state,
            next_llm_idx_state,
            next_llm_result_state 
        ],
        outputs=[
            segment_pointer_state,
            segment_dropdown,
            output_box,
            next_llm_idx_state,
            next_llm_result_state
        ],
        show_progress=False
    )

    return refresh_state, logout_btn