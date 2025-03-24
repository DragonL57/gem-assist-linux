"""
Research plugin providing academic paper search and analysis.
"""
import os
import requests
import re
from typing import Dict, Any, List, Optional, Union

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print  # Updated import path

class ResearchPlugin(Plugin):
    """Plugin providing research tools."""
    
    @staticmethod
    @tool(
        categories=["research", "academic"],
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
                return {"error": f"Paper {paper_id} not found"}
                
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
            return {"error": f"Error retrieving paper: {e}"}
    
    @staticmethod
    @tool(
        categories=["research", "analysis"],
        requires_network=True
    )
    def summarize_research_paper(text: str, max_length: int = 1500) -> Dict[str, Any]:
        """
        Extract and summarize key sections from a research paper.
        
        Args:
            text: Full text of the research paper
            max_length: Maximum length for section extracts (default: 1500 chars)
            
        Returns:
            Dictionary containing structured summary of the paper
        """
        tool_message_print("Summarizing research paper")
        
        # List of common section headers in research papers
        section_patterns = [
            r'abstract',
            r'introduction',
            r'background',
            r'related work',
            r'methodology',
            r'methods',
            r'experimental setup',
            r'experiments',
            r'results',
            r'discussion',
            r'conclusion',
            r'future work',
            r'acknowledgments',
            r'references'
        ]
        
        # Compile case-insensitive patterns for section headers
        # Look for headers that are standalone or followed by a colon or number
        section_regexes = [
            re.compile(rf'\b{pattern}\b(?::|\.|\s*\d)?', re.IGNORECASE) 
            for pattern in section_patterns
        ]
        
        # Split text into lines
        lines = text.split('\n')
        
        # Identify potential section headers
        sections = {}
        current_section = "preamble"
        sections[current_section] = []
        
        for i, line in enumerate(lines):
            # Check if the line matches any section header pattern
            for pattern, regex in zip(section_patterns, section_regexes):
                if regex.search(line) and len(line.strip()) < 100:  # Avoid matching sentences containing pattern words
                    current_section = pattern
                    if current_section not in sections:
                        sections[current_section] = []
                    break
            
            # Add line to current section
            sections[current_section].append(line)
        
        # Join lines within each section
        for section in sections:
            sections[section] = '\n'.join(sections[section])
            # Trim to max_length if needed
            if len(sections[section]) > max_length:
                sections[section] = sections[section][:max_length] + "..."
        
        # Find and extract any numerical references
        references = []
        ref_pattern = re.compile(r'\[\d+\]')
        ref_matches = ref_pattern.findall(text)
        if ref_matches:
            references = sorted(list(set(ref_matches)))
        
        # Extract potential citations (names with years)
        citations = []
        citation_pattern = re.compile(r'(?:[A-Z][a-z]+(?:\s+and\s+|\s*,\s*)?)+\s+et\s+al\.?\s*\(\d{4}\)')
        citation_matches = citation_pattern.findall(text)
        if citation_matches:
            citations = sorted(list(set(citation_matches)))[:20]  # Limit to 20 citations max
        
        # Create the summary result
        result = {
            "sections": sections,
            "section_names": list(sections.keys()),
            "has_abstract": "abstract" in sections,
            "has_conclusion": any(s in sections for s in ["conclusion", "conclusions"]),
            "references_count": len(references),
            "citations_sample": citations[:10],  # Include up to 10 sample citations
        }
        
        # Count words and estimate pages
        word_count = len(text.split())
        result["word_count"] = word_count
        result["estimated_pages"] = round(word_count / 500)  # Rough estimate: ~500 words per page
        
        # Print summary info
        tool_report_print(f"Paper summary: {result['estimated_pages']} pages, {len(sections)} sections identified")
        
        return result
