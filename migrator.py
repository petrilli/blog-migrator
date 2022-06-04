#!/usr/bin/env python3.10
import argparse
import re
from datetime import datetime
from pathlib import Path

import bs4
from bs4 import BeautifulSoup, Comment
from dateutil.parser import parse as parse_datetime
from markdownify import markdownify
import yaml

RE_DATETIME = re.compile(
    r"""
    ^This\s+entry\s+was\s+posted\s+at\s+ # This entry was posted at
    (\d{1,2}:\d{2}\s+                    # 12:05
    (am|pm)\s+                           # am or pm
    on\s+                                # on
    \d{1,2}\s+\w{3,}\s+\d{4}             # 3 May 2022
    )""",
    flags=re.VERBOSE,
)


def to_kebab_case(v: str) -> str:
    return "-".join(v.lower().split())


def parse_command_line(command_line: list[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="migrate scraped blog")
    parser.add_argument(
        "files",
        metavar="FILE",
        type=str,
        nargs="+",
        help="collection of files to process",
    )
    parser.add_argument(
        "--output", type=str, default="", help="output directory if not $CWD"
    )

    return parser.parse_args(args=command_line)


def extract_title(soup: BeautifulSoup) -> str:
    return soup.select("h2 a")[0].text


def extract_timestamp(soup: BeautifulSoup) -> datetime:
    html = soup.select(".post .discussion p")[0].text
    extracted_datetime = RE_DATETIME.match(html).group(1)
    return parse_datetime(extracted_datetime)


def extract_category(soup: BeautifulSoup) -> str:
    try:
        category = soup.select("span.tag a")[0].text.lower()
    except Exception:
        category = ""

    return category


def extract_content(soup: BeautifulSoup):
    post = soup.select_one(".post")
    post_only = []
    for tag in post:
        if isinstance(tag, Comment):
            break
        else:
            post_only.append(tag)

    # Filter to only interesting tags. Things like "\n" and comments do not have a name.
    return [
        tag
        for tag in post.children
        if tag.name in {"p", "blockquote", "img", "table", "ul", "ol", "pre", "hr"}
    ]


def convert_to_markdown(tags: list[bs4.Tag]) -> str:
    return markdownify("\n".join([str(t) for t in tags]), strong_em_symbol="_")


def build_hugo_header(ts: datetime, title: str, category: str):
    header = {
        "title": title,
        "date": ts.isoformat(),
        "tags": [category],
        "draft": True,
        "math": False,
        "toc": False,
    }

    return yaml.safe_dump(header)


def convert_post_to_hugo(post: str) -> str:
    soup = BeautifulSoup(post, "html.parser")
    title = extract_title(soup)
    timestamp = extract_timestamp(soup)
    category = extract_category(soup)
    content = extract_content(soup)

    header = build_hugo_header(timestamp, title, category)
    body = convert_to_markdown(content)

    return "\n".join(["---", header, "---", body])


def determine_write_name_from_input(path: str) -> Path:
    """Take the input file path and figure out what the output name should be."""
    # Convert to a Path object
    path = Path(path)
    name = path.parts[-2]
    year = path.parts[-5]
    month = path.parts[-4]

    return Path(f"{year}-{month}-{name}.md")


def main():
    args = parse_command_line()

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_dir():
            print(f"{output_path} is not an existing directly.")
            exit(1)

    for f in args.files:
        output_file = output_path / determine_write_name_from_input(f)
        print(f"*** Process {f} ==> {output_file}")
        with (open(f, "r") as input, open(output_file, "w") as output):
            try:
                output.write(convert_post_to_hugo(input.read()))
            except Exception as e:
                print(f"!!! Error processing {f}: {repr(e)}")


if __name__ == "__main__":
    main()
