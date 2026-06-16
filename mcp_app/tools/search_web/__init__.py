"""
This package contains the implementation of the search web tool,
which allows users to perform web searches and retrieve relevant information from the internet. 
The tool can be used to enhance the capabilities of AI models by providing them with access to up-to-date information from the web. 
It includes functionalities for querying search engines, processing search results, and integrating the retrieved information into AI workflows.
"""

from .duckduckgo import duckduckgo_search

search_web = duckduckgo_search

__all__ = ["duckduckgo_search", "search_web"]
