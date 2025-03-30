"""
Research plugin providing academic paper search and analysis.
"""
import os
import requests
import re
from typing import Dict, Any, List, Optional, Union

from plugins import Plugin, tool, capability, PluginError
from core_utils import tool_message_print, tool_report_print  # Updated import path

class ResearchPlugin(Plugin):
    """Plugin providing research tools."""
    
    @staticmethod
    @tool(
        categories=["research"],
        requires_network=True,
        rate_limited=True
    )
    def get_arxiv_paper(paper_id: str, return_format: str = "text") -> Dict[str, Any]:
        """
        Get information and content about a paper from arXiv.
        
        Args:
            paper_id: arXiv paper ID (e.g., '2311.17096' or 'https://arxiv.org/abs/2311.17096')
            return_format: Return format, either 'text' (default) or 'full'
            
        Returns:
            Dictionary containing paper information and content
        """
        tool_message_print(f"Getting arXiv paper: {paper_id}")
        
        try:
            # Extract paper ID if a full URL was provided
            if '/' in paper_id:
                # Extract the paper ID from the URL
                paper_id = paper_id.split('/')[-1]
                # Remove any version suffix (e.g., v1, v2)
                paper_id = re.sub(r'v\d+$', '', paper_id)
                
            # Query the arXiv API
            url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse the response XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            # Define XML namespaces used in arXiv API
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # Extract entry element (contains paper info)
            entry = root.find('.//atom:entry', ns)
            
            if entry is None:
                raise PluginError(f"Paper {paper_id} not found", plugin_name=ResearchPlugin.__name__)
                
            # Extract basic information
            title = entry.find('./atom:title', ns).text.strip()
            summary = entry.find('./atom:summary', ns).text.strip()
            published = entry.find('./atom:published', ns).text.strip()
            
            # Extract authors
            authors = []
            for author_elem in entry.findall('./atom:author', ns):
                name_elem = author_elem.find('./atom:name', ns)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
                    
            # Extract categories
            categories = []
            for cat_elem in entry.findall('./atom:category', ns):
                if 'term' in cat_elem.attrib:
                    categories.append(cat_elem.attrib['term'])
                    
            # Extract links
            links = {}
            for link_elem in entry.findall('./atom:link', ns):
                if 'title' in link_elem.attrib and 'href' in link_elem.attrib:
                    links[link_elem.attrib['title']] = link_elem.attrib['href']
                elif 'rel' in link_elem.attrib and 'href' in link_elem.attrib:
                    links[link_elem.attrib['rel']] = link_elem.attrib['href']
            
            # Format the result
            result = {
                "id": paper_id,
                "title": title,
                "authors": authors,
                "published": published,
                "categories": categories,
                "summary": summary,
                "links": links
            }
            
            # Return just the formatted text content if requested
            if return_format.lower() == "text":
                formatted_text = f"Title: {title}\n\n"
                formatted_text += f"Authors: {', '.join(authors)}\n\n"
                formatted_text += f"Published: {published}\n\n"
                formatted_text += f"Categories: {', '.join(categories)}\n\n"
                formatted_text += f"Summary: {summary}\n\n"
                
                # Add links
                formatted_text += "Links:\n"
                for link_name, link_url in links.items():
                    formatted_text += f"- {link_name}: {link_url}\n"
                    
                result["formatted_text"] = formatted_text
                
            # Print summary
            tool_report_print(f"Retrieved paper: {title}")
            
            return result
            
        except Exception as e:
            raise PluginError(f"Error retrieving arxiv paper: {e}", plugin_name=ResearchPlugin.__name__) from e
    