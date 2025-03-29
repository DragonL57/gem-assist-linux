import unittest
from assistant.reasoning_validator import ReasoningValidator

class TestReasoningPlans(unittest.TestCase):
    
    def setUp(self):
        self.validator = ReasoningValidator()
        self.validator.update_tools_registry()
        
    def test_reasoning_plan_sample(self):
        """Test validation of a sample reasoning plan."""
        sample_plan = """
        Problem Analysis: User needs information about Python 3.10 features
        
        Information Needs:
        - Release date of Python 3.10
        - Key new features in Python 3.10
        - Code examples for important features
        
        Tool Selection Strategy:
        1. web_search(query="Python 3.10 new features", time_period="y")
        2. get_website_content for Python.org release notes
        
        Verification Strategy:
        - Cross-reference with official Python documentation
        
        RESPONSE LANGUAGE: English
        """
        
        results = self.validator.validate_plan(sample_plan)
        self.assertTrue(results["is_valid"])
        self.assertGreaterEqual(results["score"], 0.8)
        
    def test_search_strategy_adherence(self):
        """Test that reasoning plans follow rate-limit aware search strategies."""
        sample_plan = """
        Problem Analysis: User needs information about multiple programming languages
        
        Information Needs:
        - Features of Python, JavaScript, and Rust
        - Comparison of performance characteristics
        - Use case recommendations
        
        Tool Selection Strategy:
        1. web_search(query="Python JavaScript Rust comparison features performance use cases", time_period="m")
        2. get_website_text_content on 3 most authoritative sources from results
        3. execute_python_code to create a comparison table from extracted information
        
        Verification Strategy:
        - Cross-reference information between different sources
        - Check for conflicting claims about language performance
        
        RESPONSE LANGUAGE: English
        """
        
        # Search strategy checks should be added to the validator 
        # to ensure the plan follows rate-limit awareness guidelines
        results = self.validator.validate_plan(sample_plan)
        self.assertTrue(results["is_valid"])
        # Check if the plan has minimal search calls (ideally 1-2)
        search_calls = sample_plan.lower().count("web_search(")
        self.assertLessEqual(search_calls, 2, "Plan should contain at most 2 search calls")
