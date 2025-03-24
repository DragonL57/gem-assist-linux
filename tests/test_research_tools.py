"""
Test script for research tools.
Run with: python -m tests.test_research_tools
"""

import sys
import os
import unittest

# Add the parent directory to sys.path to allow importing from utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.research import get_arxiv_paper, summarize_research_paper

class TestResearchTools(unittest.TestCase):
    def test_get_arxiv_paper(self):
        """Test retrieving arXiv paper metadata."""
        # Use a known arXiv paper
        paper_id = "2103.00020"  # A simple test paper
        
        print(f"Testing arXiv paper retrieval for ID: {paper_id}")
        result = get_arxiv_paper(paper_id, extract_text=False)  # Don't extract text for faster testing
        
        self.assertNotIn("error", result, f"Error retrieving paper: {result.get('error', '')}")
        self.assertIn("title", result)
        self.assertIn("authors", result)
        self.assertIn("abstract", result)
        
        print(f"Successfully retrieved paper: '{result['title']}'")
        print(f"Authors: {result['authors']}")
        print(f"Abstract preview: {result['abstract'][:100]}...")
        
        return True

    def test_paper_summary(self):
        """Test paper summarization with a sample text."""
        sample_text = """
        Abstract
        This paper introduces a novel approach to machine learning that improves performance by 20%.
        
        1. Introduction
        Machine learning has become increasingly important in recent years. This work addresses key limitations.
        
        2. Methodology
        We propose a new algorithm that combines the strengths of previous approaches while mitigating their weaknesses.
        
        3. Results
        Our experiments show that the proposed method outperforms existing methods by a significant margin.
        
        4. Conclusion
        We have demonstrated the effectiveness of our approach and identified several directions for future work.
        """
        
        print("Testing research paper summarization")
        result = summarize_research_paper(sample_text)
        
        self.assertNotIn("error", result)
        self.assertTrue(len(result["identified_sections"]) > 0)
        
        print(f"Identified sections: {', '.join(result['identified_sections'])}")
        print(f"Found {len(result['key_findings'])} key findings")
        
        return True

if __name__ == "__main__":
    unittest.main()
