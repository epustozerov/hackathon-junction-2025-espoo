import argparse

import pypandoc


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a markdown file to PDF using pypandoc. "
            "Requires wkhtmltopdf (install with: sudo apt install wkhtmltopdf)."
        )
    )
    parser.add_argument("input_file", help="Path to the input markdown file.")
    parser.add_argument("output_file", help="Path to the output PDF file.")

    args = parser.parse_args()

    pypandoc.convert_file(
        args.input_file,
        to="pdf",
        outputfile=args.output_file,
        extra_args=["--pdf-engine=wkhtmltopdf"],
    )

    print(f"PDF created: {args.output_file}")


if __name__ == "__main__":
    main()
