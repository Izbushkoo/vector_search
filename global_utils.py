import tiktoken


def tokens_from_string(string: str) -> int:

    """Method counts tokens per string"""

    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens