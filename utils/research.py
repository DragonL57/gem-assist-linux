"""
Research utility functions for the gem-assist package.
These functions are used for accessing academic papers and research information.
"""

import os
import requests
import re
import tempfile
from typing import Dict, Any, Optional
import io
from bs4 import BeautifulSoup

from .core import tool_message_print, tool_report_print

# Check for optional dependencies
PYPDF_AVAILABLE = False
try:
    import PyPDF2
    PYPDF_AVAILABLE = True
except ImportError:
    pass

def get_arxiv_paper(paper_id: str, extract_text: bool = True) -> Dict[str, Any]:
    """
    Get metadata and optionally extract text from an arXiv paper.
    
    Args:
        paper_id: arXiv ID (e.g., "2503.16385" or full URL "https://arxiv.org/abs/2503.16385")
        extract_text: Whether to extract text from the PDF (requires PyPDF2)
        
    Returns:
        Dictionary containing paper metadata and optionally extracted text
    """
    # Extract paper ID from URL if needed
    if "arxiv.org" in paper_id:
        match = re.search(r'arxiv\.org\/(?:abs|pdf)\/([0-9]+\.[0-9]+)', paper_id)
        if match:
            paper_id = match.group(1)
    
    tool_message_print("get_arxiv_paper", [
        ("paper_id", paper_id),
        ("extract_text", str(extract_text))
    ])
    
    # Initialize result dictionary
    result = {
        "id": paper_id,
        "abs_url": f"https://arxiv.org/abs/{paper_id}",
        "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf"
    }
    
    try:
        # First, get metadata from the abstract page
        abs_response = requests.get(result["abs_url"], timeout=10)
        abs_response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(abs_response.text, 'html.parser')
        
        # Extract title
        title_tag = soup.select_one("h1.title")
        result["title"] = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown title"
        
        # Extract authors
        authors_tag = soup.select_one("div.authors")
        result["authors"] = authors_tag.text.replace("Authors:", "").strip() if authors_tag else "Unknown authors"
        
        # Extract abstract
        abstract_tag = soup.select_one("blockquote.abstract")
        result["abstract"] = abstract_tag.text.replace("Abstract:", "").strip() if abstract_tag else "No abstract available"
        
        # Extract categories
        categories_tag = soup.select_one("div.subjects")
        result["categories"] = categories_tag.text.replace("Subjects:", "").strip() if categories_tag else ""
        
        # Extract date
        date_tag = soup.select_one("div.dateline")
        result["date"] = date_tag.text.strip() if date_tag else "Unknown date"
        
        # Extract PDF text if requested and PyPDF is available
        if extract_text and PYPDF_AVAILABLE:
            # Download PDF
            pdf_response = requests.get(result["pdf_url"], timeout=30)
            pdf_response.raise_for_status()
            
            # Read PDF with PyPDF2
            pdf_file = io.BytesIO(pdf_response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from each page
            text_content = []
            num_pages = len(pdf_reader.pages)
            
            # Limit to a reasonable number of pages to avoid token limits
            max_pages = min(num_pages, 20)  # Limit to first 20 pages
            
            for i in range(max_pages):
                page = pdf_reader.pages[i]
                text_content.append(page.extract_text())
            
            # Store the extracted text in the result
            result["text"] = "\n\n".join(text_content)
            result["page_count"] = num_pages
            result["extracted_pages"] = max_pages
            
            tool_report_print("Paper processing complete:", 
                             f"Extracted {max_pages} of {num_pages} pages from {result['title']}")
        elif extract_text and not PYPDF_AVAILABLE:
            result["error_text_extraction"] = "PyPDF2 is not installed. Install with: pip install PyPDF2"
            tool_report_print("PDF text extraction skipped:", "PyPDF2 not installed", is_error=True)
        
        return result
        
    except Exception as e:
        tool_report_print("Error retrieving arXiv paper:", str(e), is_error=True)
        return {"error": f"Failed to retrieve arXiv paper: {str(e)}"}

def summarize_research_paper(text: str, max_length: int = 5000) -> Dict[str, Any]:
    """
    Extract key information from a research paper's text.
    
    Args:
        text: The text content of the research paper
        max_length: Maximum length of text to process to avoid token limits
        
    Returns:
        Dictionary containing extracted sections and summary information
    """
    tool_message_print("summarize_research_paper", [
        ("text_length", str(len(text))),
        ("max_length", str(max_length))
    ])
    
    # Truncate text if needed to avoid token limits
    if len(text) > max_length:
        processed_text = text[:max_length] + "... [truncated due to length]"
    else:
        processed_text = text
    
    # Initialize result
    result = {
        "sections": {},
        "key_findings": [],
        "identified_sections": []
    }
    
    try:
        # Extract common paper sections using regex
        section_patterns = {
            "abstract": r"(?i)abstract[\s\n]*(.+?)(?=\n\s*(?:introduction|keywords|related work|\d\.|contribution|methodology|conclusion))",
            "introduction": r"(?i)(?:\d\.\s*)?introduction[\s\n]*(.+?)(?=\n\s*(?:\d\.|related work|background|preliminaries|methodology|approach))",
            "methodology": r"(?i)(?:\d\.\s*)?(?:methodology|method|approach|proposed method)[\s\n]*(.+?)(?=\n\s*(?:\d\.|experiments|evaluation|results|discussion))",
            "results": r"(?i)(?:\d\.\s*)?(?:results|evaluation|experiments)[\s\n]*(.+?)(?=\n\s*(?:\d\.|discussion|conclusion|limitations|future work))",
            "conclusion": r"(?i)(?:\d\.\s*)?(?:conclusion|conclusions|concluding remarks)[\s\n]*(.+?)(?=\n\s*(?:\d\.|references|acknowledgements|appendix))"
        }
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, processed_text, re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                result["sections"][section_name] = section_content
                result["identified_sections"].append(section_name)
        
        # Identify key findings (sentences that contain important indicators)
        key_finding_patterns = [
            r"(?i)we (?:show|demonstrate|find|found|observe|observed|conclude|concluded) that (.+?\.)",
            r"(?i)our (?:results|experiments|analysis|evaluation) (?:show|demonstrate|suggest|indicate|reveal) that (.+?\.)",
            r"(?i)this paper (?:presents|proposes|introduces|describes) (.+?\.)",
            r"(?i)the main contribution(?:s)? (?:of this paper|of this work|are) (.+?\.)",
            r"(?i)we propose (.+?\.)"
        ]
        
        for pattern in key_finding_patterns:
            for match in re.finditer(pattern, processed_text):
                finding = match.group(1).strip()
                if finding and len(finding) > 20:  # Avoid very short matches
                    result["key_findings"].append(finding)
        
        # Remove duplicates from key findings
        result["key_findings"] = list(set(result["key_findings"]))
        
        tool_report_print("Paper summary complete:", 
                         f"Identified {len(result['identified_sections'])} sections and {len(result['key_findings'])} key findings")
        return result
        
    except Exception as e:
        tool_report_print("Error summarizing paper:", str(e), is_error=True)
        return {"error": f"Failed to summarize paper: {str(e)}"}
