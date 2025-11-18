"""
Google Gemini API client for generating assignment solutions.

This module handles:
- Authentication with Google Gemini API
- Prompt engineering for different assignment types and subjects
- Solution generation with step-by-step explanations and reasoning
- Quality validation and confidence scoring
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .config import settings
from .models import ProcessedAssignment, GeneratedSolution

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for Google Gemini API integration"""
    
    def __init__(self):
        self.model = None
        self.is_initialized = False
        
        # Safety settings to allow educational content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Generation configuration for detailed, educational responses
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.4,  # Balanced temperature for detailed yet accurate content
            top_p=0.85,
            top_k=50,
            max_output_tokens=8192,  # Increased for more comprehensive solutions
            candidate_count=1
        )
    
    async def initialize(self) -> bool:
        """Initialize the Gemini API client"""
        logger.info("Initializing Google Gemini API client...")
        
        try:
            if not settings.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY not found in environment variables")
                return False
            
            logger.info(f"Using Gemini model: {settings.GEMINI_MODEL}")
            
            # Configure the API key
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            # Test the connection with a simple prompt
            logger.info("Testing Gemini API connection...")
            test_response = await self._test_connection()
            if not test_response:
                logger.error("Failed to establish connection with Gemini API")
                logger.error("Please check: 1) API key is valid, 2) Model name is correct, 3) Gemini API is enabled")
                return False
            
            self.is_initialized = True
            logger.info("Google Gemini API client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API client: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("Hint: Check if the GEMINI_API_KEY is valid and the model name is supported")
            return False
    
    async def _test_connection(self) -> bool:
        """Test the connection to Gemini API"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                "Hello, this is a test message. Please respond with 'Connection successful.'"
            )
            
            if response and response.text:
                logger.info("Gemini API connection test successful")
                return True
            else:
                logger.error("Gemini API connection test failed - no response")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
    
    async def generate_solution(self, assignment: ProcessedAssignment) -> GeneratedSolution:
        """Generate a comprehensive solution for an assignment"""
        if not self.is_initialized:
            raise RuntimeError("Gemini client not initialized")
        
        logger.info(f"Generating solution for assignment: {assignment.title}")
        start_time = time.time()
        
        try:
            # Create subject-specific and type-specific prompt
            prompt = self._create_prompt(assignment)
            
            # Generate solution using Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini API")
            
            # Parse and structure the response
            solution_data = self._parse_solution_response(response.text, assignment)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Validate solution quality
            confidence_score = self._calculate_confidence_score(solution_data, assignment)
            quality_validated = self._validate_solution_quality(solution_data)
            
            # Create GeneratedSolution object
            solution = GeneratedSolution(
                assignment_id=assignment.id or assignment.google_classroom_id,
                content=solution_data['content'],
                explanation=solution_data['explanation'],
                step_by_step=solution_data['step_by_step'],
                reasoning=solution_data['reasoning'],
                generated_by="automation_agent",
                ai_model_used=settings.GEMINI_MODEL,
                confidence_score=confidence_score,
                processing_time=processing_time,
                subject_area=assignment.subject,
                quality_validated=quality_validated
            )
            
            logger.info(f"Solution generated successfully for: {assignment.title} "
                       f"(confidence: {confidence_score:.2f}, time: {processing_time:.2f}s)")
            
            return solution
            
        except Exception as e:
            logger.error(f"Failed to generate solution for {assignment.title}: {e}")
            raise
    
    def _create_prompt(self, assignment: ProcessedAssignment) -> str:
        """Create a comprehensive prompt for solution generation"""
        
        # Base prompt template with enhanced instructions
        base_prompt = f"""
You are a highly knowledgeable expert educational assistant with deep expertise across multiple academic disciplines. Your goal is to provide exceptionally detailed, precise, and comprehensive solutions that demonstrate thorough understanding and help students learn deeply.

**Assignment Details:**
- Title: {assignment.title}
- Subject: {assignment.subject}
- Course: {assignment.course_name}
- Type: {assignment.assignment_type}
- Description: {assignment.description}

**Your Approach:**
- Treat this as if you are explaining to a dedicated student who wants to master the material
- Go beyond surface-level answers - provide deep insights and comprehensive coverage
- Make no assumptions about prior knowledge - explain all concepts thoroughly
- Show your expertise by including nuanced details and advanced considerations
- Balance rigor with clarity - be technically precise yet understandable
"""
        
        # Add processed materials if available
        if assignment.processed_materials:
            base_prompt += "\n**Additional Materials:**\n"
            for material in assignment.processed_materials:
                material_info = f"- {material['type']}: {material['metadata'].get('title', 'Unknown')}"
                if material.get('content'):
                    material_info += f"\n  Content: {material['content'][:200]}..."
                base_prompt += material_info + "\n"
        
        # Add subject-specific instructions
        subject_instructions = self._get_subject_specific_instructions(assignment.subject)
        base_prompt += f"\n{subject_instructions}\n"
        
        # Add assignment type-specific instructions
        type_instructions = self._get_type_specific_instructions(assignment.assignment_type)
        base_prompt += f"\n{type_instructions}\n"
        
        # Add output format requirements
        format_instructions = """
**Required Output Format:**
Please structure your response exactly as follows:

## SOLUTION
[Provide the complete, detailed solution/answer here. Be thorough and comprehensive - include all relevant details, formulas, concepts, and explanations needed for full understanding.]

## EXPLANATION
[Provide an in-depth explanation of the solution:
- Explain all key concepts and terminology used
- Describe why this approach works and is appropriate
- Connect to broader theoretical frameworks or principles
- Include context and background information
- Explain any assumptions or prerequisites
- Discuss real-world applications or relevance]

## STEP-BY-STEP
[Break down the solution into detailed, numbered steps:
- Each step should be clear and self-contained
- Include sub-steps for complex procedures
- Explain the purpose of each step
- Show intermediate results and calculations
- Add clarifying notes where needed
- Use specific examples to illustrate each step]

## REASONING
[Provide comprehensive reasoning:
- Explain your analytical approach and methodology
- Discuss why you chose this method over alternatives
- List all assumptions made and their justifications
- Consider edge cases or special conditions
- Compare with alternative approaches (pros/cons)
- Discuss limitations or potential improvements
- Connect to related concepts or problems]

**Critical Guidelines for Precision and Detail:**
- Be exhaustively thorough - prefer more detail over brevity
- Define all technical terms and jargon
- Include specific examples, calculations, and data points
- Show your work completely - no steps should be skipped
- Use precise language and exact terminology
- Provide numerical examples with complete calculations
- Include relevant formulas with variable definitions
- Add context that helps understand WHY, not just WHAT
- Anticipate follow-up questions and address them preemptively
- Cross-reference related concepts and build connections
- Ensure accuracy - double-check all facts, formulas, and calculations
"""
        
        return base_prompt + format_instructions
    
    def _get_subject_specific_instructions(self, subject: str) -> str:
        """Get subject-specific instructions for solution generation"""
        
        instructions = {
            'mathematics': """
**Mathematics Instructions:**
- Show ALL mathematical work with complete step-by-step calculations
- Write out formulas in full before substituting values
- Define all variables and their units clearly
- Explain the mathematical reasoning for each step
- Include relevant theorems, laws, or principles with their statements
- Provide alternative solution methods when applicable and compare them
- Show intermediate results and simplification steps
- Verify the answer using different methods or by substitution
- Discuss the mathematical significance and properties of the result
- Include domain, range, or constraints where relevant
- Add graphs, diagrams, or visual representations descriptions
- Connect to broader mathematical concepts and patterns
""",
            'science': """
**Science Instructions:**
- Use precise scientific terminology with definitions
- Explain ALL underlying scientific principles in detail
- State relevant scientific laws, theories, and principles explicitly
- Describe experimental procedures and methodologies thoroughly
- Include detailed observations, data, and analysis
- Provide molecular/atomic level explanations where applicable
- Connect to real-world applications with specific examples
- Discuss cause-and-effect relationships comprehensively
- Address safety considerations and precautions
- Include units for all measurements and calculations
- Describe visual elements (diagrams, graphs, molecular structures)
- Compare and contrast related concepts or phenomena
- Discuss historical context or scientific discoveries related to the topic
""",
            'english': """
**English/Literature Instructions:**
- Provide textual evidence to support analysis
- Use proper literary terminology
- Structure arguments clearly with introduction, body, and conclusion
- Consider multiple interpretations where appropriate
- Focus on critical thinking and analysis skills
""",
            'history': """
**History Instructions:**
- Provide historical context and background
- Use specific dates, names, and events
- Analyze cause and effect relationships
- Consider multiple perspectives on historical events
- Connect past events to their broader significance
""",
            'computer_science': """
**Computer Science Instructions:**
- Include complete, working code examples with proper syntax and formatting
- Add detailed inline comments explaining each code section
- Explain algorithms step-by-step with pseudocode when helpful
- Describe data structures used and why they were chosen
- Analyze time complexity and space complexity in detail
- Provide multiple implementation approaches and compare them
- Include edge cases and error handling
- Discuss optimization opportunities and trade-offs
- Add example inputs and outputs with walkthroughs
- Explain design patterns or programming paradigms used
- Include debugging strategies and common pitfalls
- Discuss best practices, code style, and maintainability
- Reference relevant computer science theory or concepts
""",
            'general': """
**General Instructions:**
- Adapt your approach to the specific subject matter with depth
- Use precise academic language and define all terminology
- Provide exhaustively comprehensive coverage of the topic
- Include multiple relevant examples with detailed explanations
- Add context, background, and historical perspective where applicable
- Discuss theoretical foundations and practical applications
- Address multiple perspectives or interpretations
- Include supporting evidence, data, or references
- Build logical arguments with clear reasoning
- Focus on deep educational value and thorough understanding
- Anticipate questions and provide preemptive clarifications
- Make connections to related topics and broader concepts
"""
        }
        
        return instructions.get(subject, instructions['general'])
    
    def _get_type_specific_instructions(self, assignment_type: str) -> str:
        """Get assignment type-specific instructions"""
        
        instructions = {
            'essay': """
**Essay Instructions:**
- Provide a clear thesis statement
- Structure with introduction, body paragraphs, and conclusion
- Use topic sentences and transitions
- Include evidence and examples to support arguments
- Ensure proper grammar and style
""",
            'problem_set': """
**Problem Set Instructions:**
- Solve each problem completely
- Show all work and intermediate steps
- Explain the reasoning for each solution approach
- Double-check calculations and final answers
- Organize solutions clearly by problem number
""",
            'research': """
**Research Instructions:**
- Identify key research questions or hypotheses
- Suggest reliable sources and research methods
- Outline the research process and methodology
- Discuss potential findings and implications
- Include proper citation format guidance
""",
            'lab': """
**Lab Instructions:**
- Explain the scientific method and experimental design
- Describe procedures and safety considerations
- Discuss expected results and data analysis
- Address potential sources of error
- Connect results to theoretical concepts
""",
            'assessment': """
**Assessment Instructions:**
- Provide comprehensive answers to all questions
- Show understanding of key concepts
- Use examples to illustrate points
- Organize answers clearly and logically
- Review and verify all responses
""",
            'general': """
**General Assignment Instructions:**
- Address all parts of the assignment thoroughly
- Use appropriate academic structure and format
- Provide clear explanations and reasoning
- Include relevant examples and evidence
- Ensure completeness and accuracy
"""
        }
        
        return instructions.get(assignment_type, instructions['general'])
    
    def _parse_solution_response(self, response_text: str, assignment: ProcessedAssignment) -> Dict[str, any]:
        """Parse the structured response from Gemini into components"""
        
        # Initialize default structure
        solution_data = {
            'content': '',
            'explanation': '',
            'step_by_step': [],
            'reasoning': ''
        }
        
        try:
            # Split response by section headers
            sections = response_text.split('##')
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                lines = section.split('\n', 1)
                if len(lines) < 2:
                    continue
                
                header = lines[0].strip().upper()
                content = lines[1].strip()
                
                if 'SOLUTION' in header:
                    solution_data['content'] = content
                elif 'EXPLANATION' in header:
                    solution_data['explanation'] = content
                elif 'STEP-BY-STEP' in header or 'STEP BY STEP' in header:
                    # Parse numbered steps
                    steps = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                            # Remove numbering and bullet points
                            step = line.lstrip('0123456789.-• ').strip()
                            if step:
                                steps.append(step)
                    solution_data['step_by_step'] = steps
                elif 'REASONING' in header:
                    solution_data['reasoning'] = content
            
            # Fallback: if sections weren't properly parsed, use the entire response as content
            if not any(solution_data.values()):
                solution_data['content'] = response_text
                solution_data['explanation'] = "Generated solution for the assignment."
                solution_data['reasoning'] = "Solution generated using AI analysis of the assignment requirements."
            
        except Exception as e:
            logger.warning(f"Failed to parse structured response: {e}")
            # Fallback to using entire response as content
            solution_data['content'] = response_text
            solution_data['explanation'] = "Generated solution for the assignment."
            solution_data['reasoning'] = "Solution generated using AI analysis of the assignment requirements."
        
        return solution_data
    
    def _calculate_confidence_score(self, solution_data: Dict[str, any], assignment: ProcessedAssignment) -> float:
        """Calculate confidence score based on solution quality indicators"""
        
        score = 0.0
        max_score = 1.0
        
        # Check if all required sections are present and non-empty
        required_sections = ['content', 'explanation', 'reasoning']
        present_sections = sum(1 for section in required_sections if solution_data.get(section, '').strip())
        score += (present_sections / len(required_sections)) * 0.4
        
        # Check content length (reasonable but not too short)
        content_length = len(solution_data.get('content', ''))
        if content_length > 100:
            score += 0.2
        elif content_length > 50:
            score += 0.1
        
        # Check if step-by-step is provided for appropriate assignment types
        if assignment.assignment_type in ['problem_set', 'lab', 'assessment']:
            if solution_data.get('step_by_step'):
                score += 0.2
        else:
            score += 0.2  # Not required for this type
        
        # Check explanation quality (basic heuristics)
        explanation = solution_data.get('explanation', '')
        if len(explanation) > 100:
            score += 0.2
        elif len(explanation) > 50:
            score += 0.1
        
        return min(score, max_score)
    
    def _validate_solution_quality(self, solution_data: Dict[str, any]) -> bool:
        """Validate that the solution meets basic quality standards"""
        
        # Check that essential components are present
        if not solution_data.get('content', '').strip():
            return False
        
        if not solution_data.get('explanation', '').strip():
            return False
        
        # Check minimum content length
        if len(solution_data.get('content', '')) < 50:
            return False
        
        # Check for obvious errors or incomplete responses
        content = solution_data.get('content', '').lower()
        explanation = solution_data.get('explanation', '').lower()
        
        # Red flags that indicate poor quality
        red_flags = [
            'i cannot', 'i can\'t', 'unable to', 'sorry', 'i don\'t know',
            'not possible', 'cannot provide', 'insufficient information'
        ]
        
        for flag in red_flags:
            if flag in content or flag in explanation:
                return False
        
        return True
    
    def is_authenticated(self) -> bool:
        """Check if the client is properly authenticated and initialized"""
        return self.is_initialized and self.model is not None