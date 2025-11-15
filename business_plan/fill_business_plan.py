import argparse
import os

import yaml
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    base_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(
        description="Fill a business plan markdown template using answers from a YAML file via an OpenAI model.",
    )
    parser.add_argument(
        "--template-markdown",
        default=os.path.join(base_dir, "business_plan_template.md"),
        help="Path to the input markdown business plan template.",
    )
    parser.add_argument(
        "--answers-yaml",
        default=os.path.join(base_dir, "dummy_filled_business_plan.yaml"),
        help="Path to the YAML file containing business plan answers.",
    )
    parser.add_argument(
        "--output-markdown",
        default=os.path.join(base_dir, "filled_business_plan.md"),
        help="Path to the filled markdown file that will be written.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="OpenAI chat model to use for filling the template.",
    )   
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, prints the filled markdown instead of writing a file.",
    )
    return parser.parse_args()


def load_yaml_answers(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_messages(template_markdown: str, answers: dict) -> str:
    yaml_text = yaml.safe_dump(answers, sort_keys=False, allow_unicode=True)
    parts: list[str] = []
    parts.append(
        "You are helping to fill in a business plan document.\n"
        "You will receive:\n"
        "1) A markdown version of a business plan template.\n"
        "2) A YAML structure containing questions and prepared answers.\n\n"
        "Goal:\n"
        "- Produce a single markdown document that follows the structure of the template\n"
        "  but with the YAML answers woven into the appropriate sections.\n"
        "- Preserve all headings and checklists from the template.\n"
        "- Where the template expects free-text answers, insert or replace with the\n"
        "  corresponding YAML answer text. Where there are no answers, keep the '...' placeholder.\n"
        "- Do not add explanations of what you are doing; return only the final filled markdown.\n\n",
    )
    parts.append("Here is the template in markdown:\n\n```markdown\n")
    parts.append(template_markdown)
    parts.append("\n```\n\n")
    parts.append("Here are the answers in YAML:\n\n```yaml\n")
    parts.append(yaml_text)
    parts.append("\n```\n\n")
    parts.append(
        "Please return the fully filled business plan as markdown.\n"
        "\n"
        "Important formatting instructions:\n"
        "- Add blank lines before and after all headings, lists, and tables.\n"
        "- Remove all <br> tags inside tables; replace them with '-' or paragraph formatting as appropriate.\n"
        "- Ensure nested lists use consistent indentation.\n"
        "- Do not insert manual line breaks within paragraphs; let Markdown handle text wrapping naturally.\n"
    )
    return "".join(parts)


def call_openai_filling_model(
    model: str,
    prompt: str,
) -> str:
    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=prompt,
    )
    output_item = response.output[0]
    content_item = output_item.content[0]
    text = getattr(content_item, "text", None)
    if isinstance(text, str):
        content = text
    else:
        value = getattr(text, "value", None) if text is not None else None
        if isinstance(value, str):
            content = value
        else:
            raise RuntimeError("OpenAI response did not contain any content.")
    return content


def main() -> None:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable must be set.")
    with open(args.template_markdown, "r", encoding="utf-8") as f:
        template_markdown = f.read()
    answers = load_yaml_answers(args.answers_yaml)
    prompt = build_messages(template_markdown, answers)
    if args.dry_run:
        print(prompt)
        return
    filled_markdown = call_openai_filling_model(args.model, prompt)
    output_dir = os.path.dirname(os.path.abspath(args.output_markdown))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output_markdown, "w", encoding="utf-8") as f:
        f.write(filled_markdown)


if __name__ == "__main__":
    main()


