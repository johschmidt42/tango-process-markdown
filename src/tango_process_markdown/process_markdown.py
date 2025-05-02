import re
from pathlib import Path
from re import Match
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
import pyperclip
import typer
from httpx import Response


def remove_outer_content(text: str) -> str:
    """
    Removes content outside a '***' block

    Args:
        text: markdown content

    Returns: processed markdown content

    """
    # Find the block using a regular expression
    block_regex: str = r"\*\*\*(.*?)\*\*\*"
    match: Match = re.search(block_regex, text, re.DOTALL)
    if match:
        # Return the block if it was found
        return match.group(1)
    else:
        # Return the original string if no block was found
        return text


def remove_blend_params(url: str) -> str:
    """
    Removes query parameters that start with 'blend' from a given URL.
    This removes the watermark.

    Args:
        url (str): The URL from which 'blend' parameters should be removed.

    Returns:
        str: The URL without query parameters that start with 'blend'.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Filter out parameters that start with "blend"
    filtered_params = {
        k: v for k, v in query_params.items() if not k.startswith("blend")
    }

    # Reconstruct the query string
    new_query_string = urlencode(filtered_params, doseq=True)

    # Reconstruct the full URL without blend parameters
    return urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query_string,
            parsed_url.fragment,
        )
    )


def download_image(url: str) -> bytes:
    """
    Downloads an image using the httpx library.

    Args:
        url: image url

    Returns: downloaded image

    """
    try:
        response: Response = httpx.get(url=url)
    except ConnectionError:
        print(f"Could not download {url}")
        return bytes()

    if response.status_code == 200:
        assert isinstance(response.content, bytes)
        image: bytes = response.content
        return image
    else:
        print(f"Could not download {url}")
        return bytes()


def save_image(image: bytes, name: str) -> None:
    """
    Stores an image to disk

    Args:
        image: downloaded image
        name: name of the image

    Returns: None

    """
    with open(file=name, mode="wb") as f:
        f.write(image)

    return None


def extract_urls(text: str) -> List[str]:
    """
    Find URLs that start with https://images.tango.us/workflows/

    Args:
        text: markdown content

    Returns: URLs matching the pattern

    """

    pattern: str = r"https://images\.tango\.us/workflows/[^)]+"
    return re.findall(pattern, text)


def replace_urls(text: str, old_urls: List[str], new_urls: List[str]) -> str:
    """
    Replace all URLs in the markdown content with the new URLs.

    Args:
        text: markdown content
        old_urls: list of old URLs
        new_urls: list of new URLs

    Returns: processed markdown content

    """
    assert len(old_urls) == len(new_urls)
    for old_url, new_url in zip(old_urls, new_urls):
        text: str = text.replace(old_url, new_url)

    return text


def main(
    markdown_file: Optional[str] = None,
    image_dir: str = "images",
    header: str = "Step-by-Step Guide",
    output: str = "out.md",
    clipboard: bool = False,
):
    """

    Args:
        markdown_file: markdown filename to process
        image_dir: directory in which the images should be stored
        header: the header of the markdown file to be created
        output: the output filename
        clipboard: if True, the clipboard content is used instead of the markdown file

    Returns: None

    """

    if not clipboard and not markdown_file:
        raise ValueError("Either markdown_file or clipboard must be set.")

    if clipboard:
        content: str = pyperclip.paste()
    else:
        with open(markdown_file, "r") as f:
            content: str = f.read()

    processed_content: str = remove_outer_content(text=content)
    urls_old: List[str] = extract_urls(processed_content)
    urls_without_watermark: List[str] = [
        remove_blend_params(url_old) for url_old in urls_old
    ]

    urls_new: List[str] = list()

    # download & store images
    for idx, url in enumerate(urls_without_watermark):
        image: bytes = download_image(url)
        assert image

        full_name: Path = (Path(image_dir) / str(idx + 1).zfill(3)).with_suffix(".png")

        # create a dir if it does not already exist
        if not full_name.parent.exists():
            full_name.parent.mkdir(parents=True, exist_ok=True)

        urls_new.append(f"./{full_name}")
        save_image(image=image, name=str(full_name))

    # replace urls
    processed_content: str = replace_urls(
        text=processed_content, old_urls=urls_old, new_urls=urls_new
    )

    # add header
    processed_content: str = f"# {header}{processed_content}"

    # TODO: apply markdown linter to the processed content

    # create markdown file
    with open(output, "w") as f:
        f.write(processed_content)


if __name__ == "__main__":
    typer.run(main)
