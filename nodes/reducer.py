import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from config import GEMINI_IMAGE_MODEL, _output_dir
from llm import _get_chat_model
from schemas import GlobalImagePlan
from state import State
from utils import _as_plan, _safe_slug


def merge_content(state: State) -> dict:
    plan = _as_plan(state["plan"])
    if plan is None:
        topic = state.get("topic", "Blog")
        merged_md = f"# {topic}\n\n_(No plan available.)_"
        return {"merged_md": merged_md}

    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}


DECIDE_IMAGES_SYSTEM = """You are an expert technical editor.
Decide if images/diagrams are needed for THIS blog.

Rules:
- Max 3 images total.
- Each image must materially improve understanding (diagram/flow/table-like visual).
- Insert placeholders exactly: [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]].
- If no images needed: md_with_placeholders must equal input and images=[].
- Avoid decorative images; prefer technical diagrams with short labels.
Return strictly GlobalImagePlan.
"""


def decide_images(state: State) -> dict:
    planner = _get_chat_model().with_structured_output(GlobalImagePlan)
    merged_md = state["merged_md"]
    plan = _as_plan(state["plan"])
    assert plan is not None

    image_plan = planner.invoke(
        [
            SystemMessage(content=DECIDE_IMAGES_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Topic: {state['topic']}\n\n"
                    "Insert placeholders + propose image prompts.\n\n"
                    f"{merged_md}"
                )
            ),
        ]
    )

    return {
        "md_with_placeholders": image_plan.md_with_placeholders,
        "image_specs": [img.model_dump() for img in image_plan.images],
    }


def _gemini_generate_image_bytes(prompt: str) -> bytes:
    """Raw image bytes from Gemini image model (google-genai). Uses GOOGLE_API_KEY."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    resp = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_ONLY_HIGH",
                )
            ],
        ),
    )

    parts = getattr(resp, "parts", None)
    if not parts and getattr(resp, "candidates", None):
        try:
            parts = resp.candidates[0].content.parts
        except Exception:
            parts = None

    if not parts:
        raise RuntimeError("No image content returned (safety/quota/SDK change).")

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            return inline.data

    raise RuntimeError("No inline image bytes found in response.")


def generate_and_place_images(state: State) -> dict:
    plan = _as_plan(state["plan"])
    assert plan is not None

    md = state.get("md_with_placeholders") or state["merged_md"]
    image_specs = state.get("image_specs", []) or []

    out_dir = _output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    md_filename = f"{_safe_slug(plan.blog_title)}.md"
    md_path = out_dir / md_filename

    if not image_specs:
        md_path.write_text(md, encoding="utf-8")
        return {"final": md, "markdown_path": str(md_path)}

    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for spec in image_specs:
        placeholder = spec["placeholder"]
        filename = spec["filename"]
        out_path = images_dir / filename

        try:
            img_bytes = _gemini_generate_image_bytes(spec["prompt"])
            out_path.write_bytes(img_bytes)
        except Exception as e:
            prompt_block = (
                f"> **[IMAGE GENERATION FAILED]** {spec.get('caption', '')}\n>\n"
                f"> **Alt:** {spec.get('alt', '')}\n>\n"
                f"> **Prompt:** {spec.get('prompt', '')}\n>\n"
                f"> **Error:** {e}\n"
            )
            md = md.replace(placeholder, prompt_block)
            continue

        # Relative to md_path so previews (VS Code, Jupyter Markdown, etc.) resolve like the notebook.
        img_md = f"![{spec['alt']}](images/{filename})\n*{spec['caption']}*"
        md = md.replace(placeholder, img_md)

    md_path.write_text(md, encoding="utf-8")
    return {"final": md, "markdown_path": str(md_path)}


reducer_graph = StateGraph(State)
reducer_graph.add_node("merge_content", merge_content)
reducer_graph.add_node("decide_images", decide_images)
reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
reducer_graph.add_edge(START, "merge_content")
reducer_graph.add_edge("merge_content", "decide_images")
reducer_graph.add_edge("decide_images", "generate_and_place_images")
reducer_graph.add_edge("generate_and_place_images", END)
reducer_subgraph = reducer_graph.compile()
