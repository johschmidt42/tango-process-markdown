import re
from pathlib import Path
from re import Match
from typing import List

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


def remove_watermark(text: str, mark: str = "mark") -> str:
    """
    Delete everything that starts with "mark" and ends with "&",
    without deleting the last character

    Args:
        text: markdown content
        mark: staring character to look for

    Returns: processed markdown content

    """
    #
    marked_text_regex: str = rf"{mark}(.*?)&."
    return re.sub(marked_text_regex, "", text)


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
    markdown_file: str, image_dir: str = "images", header: str = "Step-by-Step Guide"
):
    """

    Args:
        markdown_file: markdown filename to create
        image_dir: directory in which the images should be stored
        header: the header of the markdown file to be created

    Returns: None

    """
    clipboard_content: str = pyperclip.paste()
    processed_content: str = remove_outer_content(text=clipboard_content)
    processed_content: str = remove_watermark(text=processed_content)

    urls_old: List[str] = extract_urls(processed_content)
    urls_new: List[str] = list()

    # download & store images
    for idx, url in enumerate(urls_old):
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

    # create markdown file
    with open(markdown_file, "w") as f:
        f.write(processed_content)


if __name__ == "__main__":
    typer.run(main)
