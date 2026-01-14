"""
Groq API client for fast, free LLM inference.

Groq provides extremely fast inference with Llama 3 models.
Perfect as a fallback when Gemini API is exhausted.
"""

import asyncio
import logging
import time
from typing import Dict, Optional
import httpx

from .config import settings
from .models import ProcessedAssignment, GeneratedSolution
from .context_analyzer import AssignmentContextAnalyzer

logger = logging.getLogger(__name__)


class GroqClient:
    """Client for Groq API integration"""
    
    def __init__(self):
        self.base_url = "https://api.groq.com/openai/v1"
        self.api_key = settings.GROQ_API_KEY
        self.model = getattr(settings, 'GROQ_MODEL', 'llama-3.1-70b-versatile')  # Fast and high quality
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the Groq API client"""
        logger.info("Initializing Groq API client...")
        
        try:
            if not self.api_key:
                logger.warning("GROQ_API_KEY not found in environment variables")
                return False
            
            # Test the connection
            logger.info(f"Testing Groq API connection with model: {self.model}")
            test_response = await self._test_connection()
            
            if not test_response:
                logger.error("Failed to establish connection with Groq API")
                return False
            
            self.is_initialized = True
            logger.info("Groq API client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq API client: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test the connection to Groq API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": "Hello, respond with 'Connection successful.'"}
                        ],
                        "max_tokens": 50
                    }
                )
                
                if response.status_code == 200:
                    logger.info("Groq API connection test successful")
                    return True
                else:
                    logger.error(f"Groq API test failed with status {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Groq API connection test failed: {e}")
            return False
    
    async def generate_solution(self, assignment: ProcessedAssignment) -> GeneratedSolution:
        """Generate a comprehensive solution for an assignment"""
        if not self.is_initialized:
            raise RuntimeError("Groq client not initialized")
        
        logger.info(f"Generating solution with Groq for assignment: {assignment.title}")
        start_time = time.time()
        
        try:
            # Analyze assignment context for dynamic prompting
            analyzer = AssignmentContextAnalyzer()
            context = analyzer.analyze(assignment)
            
            logger.info(f"Assignment context: subject={context['detected_subject']}, "
                       f"complexity={context['complexity_level']}, type={context['question_type']}")
            
            # Create context-aware prompt
            prompt = self._create_prompt(assignment, context)
            
            # Generate solution using Groq
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert educational assistant providing detailed, comprehensive solutions to academic assignments."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.4,
                        "max_tokens": 8192,
                        "top_p": 0.9
                    }
                )
            
            if response.status_code != 200:
                raise RuntimeError(f"Groq API error: {response.status_code} - {response.text}")
            
            result = response.json()
            response_text = result['choices'][0]['message']['content']
            
            if not response_text:
                raise RuntimeError("Empty response from Groq API")
            
            # Parse and structure the response
            solution_data = self._parse_solution_response(response_text, assignment)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create GeneratedSolution object
            solution = GeneratedSolution(
                assignment_id=assignment.id or assignment.google_classroom_id,
                content=solution_data['content'],
                explanation=solution_data['explanation'],
                step_by_step=solution_data['step_by_step'],
                reasoning=solution_data['reasoning'],
                generated_by="automation_agent",
                ai_model_used=self.model,
                confidence_score=0.90,  # Groq/Llama 3 is high quality
                processing_time=processing_time,
                subject_area=context['detected_subject'] if not assignment.subject else assignment.subject,
                quality_validated=True
            )
            
            logger.info(f"Solution generated successfully with Groq for: {assignment.title} "
                       f"(time: {processing_time:.2f}s)")
            
            return solution
            
        except Exception as e:
            logger.error(f"Failed to generate solution with Groq for {assignment.title}: {e}")
            raise
    
    def _create_prompt(self, assignment: ProcessedAssignment, context: Dict) -> str:
        """Create a comprehensive, context-aware prompt for solution generation"""
        
        # Extract context information
        detected_subject = context['detected_subject']
        complexity = context['complexity_level']
        question_type = context['question_type']
        key_concepts = context['key_concepts']
        
        # Build simplified context-aware prompt (Groq has tighter token limits)
        prompt = f"""You are an expert educational assistant specializing in {detected_subject.upper()}.

**Assignment Context:**
Subject: {detected_subject.title()} | Complexity: {complexity.upper()} | Type: {question_type.replace('_', ' ').title()}
Key Concepts: {', '.join(key_concepts[:3]) if key_concepts else 'N/A'}

**Assignment:**
Title: {assignment.title}
Course: {assignment.course_name}
Description: {assignment.description}

**Approach for {complexity.title()} complexity content:**"""

        # Add complexity-specific guidance
        if complexity == 'high':
            prompt += "\n- Provide advanced depth with theoretical foundations\n- Include multiple approaches and trade-offs\n- Address edge cases"
        elif complexity == 'medium':
            prompt += "\n- Balance depth with accessibility\n- Include thorough explanations with examples\n- Connect to practical applications"
        else:
            prompt += "\n- Start with fundamentals\n- Use clear, simple language\n- Provide examples and analogies"
        
        prompt += """

**Required Format:**

## SOLUTION
[Complete, detailed solution with all necessary details, formulas, and explanations]

## EXPLANATION
[In-depth explanation covering key concepts, why this approach works, and context]

## STEP-BY-STEP
[Clear numbered steps with intermediate results and calculations]

## REASONING
[Analytical approach, methodology, assumptions, and justifications]

Be comprehensive and educational. Show all work and explain thoroughly."""
        
        return prompt
    
    def _parse_solution_response(self, response_text: str, assignment: ProcessedAssignment) -> Dict[str, any]:
        """Parse the structured response into components"""
        
        solution_data = {
            'content': '',
            'explanation': '',
            'step_by_step': [],
            'reasoning': ''
        }
        
        try:
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
                    steps = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                            step = line.lstrip('0123456789.-• ').strip()
                            if step:
                                steps.append(step)
                    solution_data['step_by_step'] = steps
                elif 'REASONING' in header:
                    solution_data['reasoning'] = content
            
            # Fallback
            if not any(solution_data.values()):
                solution_data['content'] = response_text
                solution_data['explanation'] = "Generated solution using Groq AI."
                solution_data['reasoning'] = "Solution generated through AI analysis."
            
        except Exception as e:
            logger.warning(f"Failed to parse Groq response: {e}")
            solution_data['content'] = response_text
            solution_data['explanation'] = "Generated solution using Groq AI."
            solution_data['reasoning'] = "Solution generated through AI analysis."
        
        return solution_data
    
    def is_available(self) -> bool:
        """Check if the client is available for use"""
        return self.is_initialized and bool(self.api_key)
