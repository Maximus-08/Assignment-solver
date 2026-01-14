"""
Context analyzer for assignments - detects subject, complexity, and question type.

Analyzes assignment content to provide context-aware prompting.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from .models import ProcessedAssignment

logger = logging.getLogger(__name__)


class AssignmentContextAnalyzer:
    """Analyzes assignment context for intelligent prompt generation"""
    
    def __init__(self):
        # Subject detection keywords
        self.subject_keywords = {
            'mathematics': ['equation', 'calculate', 'solve', 'derivative', 'integral', 'algebra', 
                          'geometry', 'trigonometry', 'calculus', 'theorem', 'proof', 'formula',
                          'variable', 'function', 'graph', 'matrix', 'vector', 'polynomial'],
            'computer_science': ['code', 'program', 'algorithm', 'function', 'class', 'method',
                                'variable', 'loop', 'array', 'data structure', 'python', 'java',
                                'javascript', 'compile', 'debug', 'api', 'database', 'sql'],
            'physics': ['force', 'energy', 'momentum', 'velocity', 'acceleration', 'mass',
                       'newton', 'quantum', 'thermodynamics', 'mechanics', 'wave', 'particle',
                       'electric', 'magnetic', 'circuit', 'joule', 'watt'],
            'chemistry': ['molecule', 'atom', 'reaction', 'compound', 'element', 'bond',
                         'chemical', 'solution', 'acid', 'base', 'ph', 'periodic', 'organic',
                         'inorganic', 'oxidation', 'reduction', 'catalyst'],
            'biology': ['cell', 'organism', 'dna', 'protein', 'gene', 'evolution', 'ecology',
                       'metabolism', 'photosynthesis', 'enzyme', 'bacteria', 'virus', 'tissue',
                       'organ', 'species', 'ecosystem'],
            'english': ['essay', 'analyze', 'theme', 'character', 'plot', 'metaphor', 'symbolism',
                       'author', 'literature', 'poem', 'novel', 'prose', 'rhetoric', 'argument',
                       'paragraph', 'thesis', 'narrative'],
            'history': ['war', 'revolution', 'empire', 'dynasty', 'treaty', 'constitution',
                       'century', 'civilization', 'ancient', 'medieval', 'modern', 'colonial',
                       'independence', 'political', 'economic', 'social'],
            'economics': ['market', 'supply', 'demand', 'price', 'inflation', 'gdp', 'trade',
                         'economy', 'fiscal', 'monetary', 'investment', 'stock', 'capital',
                         'profit', 'cost', 'revenue'],
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            'high': ['advanced', 'complex', 'sophisticated', 'comprehensive', 'in-depth',
                    'detailed', 'rigorous', 'extensive', 'thorough', 'graduate', 'research'],
            'medium': ['explain', 'describe', 'compare', 'analyze', 'discuss', 'evaluate',
                      'demonstrate', 'justify', 'interpret'],
            'low': ['simple', 'basic', 'introduction', 'overview', 'list', 'define',
                   'identify', 'name', 'what is', 'elementary']
        }
        
        # Question type indicators
        self.question_types = {
            'problem_solving': ['solve', 'calculate', 'compute', 'find', 'determine', 'derive'],
            'analytical': ['analyze', 'examine', 'investigate', 'evaluate', 'assess', 'critique'],
            'explanatory': ['explain', 'describe', 'discuss', 'elaborate', 'clarify', 'illustrate'],
            'comparative': ['compare', 'contrast', 'differentiate', 'distinguish', 'relate'],
            'creative': ['design', 'create', 'develop', 'propose', 'construct', 'formulate'],
            'research': ['research', 'investigate', 'survey', 'review', 'study', 'explore'],
        }
    
    def analyze(self, assignment: ProcessedAssignment) -> Dict[str, any]:
        """
        Analyze assignment and return context information.
        
        Returns:
            Dict with detected_subject, confidence, complexity, question_type, key_concepts
        """
        text = f"{assignment.title} {assignment.description}".lower()
        
        # Detect subject
        detected_subject, subject_confidence = self._detect_subject(text, assignment.subject)
        
        # Detect complexity
        complexity = self._detect_complexity(text)
        
        # Detect question type
        question_type = self._detect_question_type(text)
        
        # Extract key concepts
        key_concepts = self._extract_key_concepts(text, detected_subject)
        
        # Detect mathematical content
        has_equations = self._has_equations(text)
        
        # Detect code
        has_code = self._has_code(text)
        
        context = {
            'detected_subject': detected_subject,
            'subject_confidence': subject_confidence,
            'complexity_level': complexity,
            'question_type': question_type,
            'key_concepts': key_concepts,
            'has_equations': has_equations,
            'has_code': has_code,
            'word_count': len(text.split()),
        }
        
        logger.info(f"Context analysis: subject={detected_subject} ({subject_confidence:.2f}), "
                   f"complexity={complexity}, type={question_type}")
        
        return context
    
    def _detect_subject(self, text: str, provided_subject: Optional[str]) -> Tuple[str, float]:
        """Detect subject from content or use provided subject"""
        
        # If subject provided, use it with high confidence
        if provided_subject:
            normalized_subject = provided_subject.lower()
            # Map to standard categories
            for category, keywords in self.subject_keywords.items():
                if category in normalized_subject or normalized_subject in category:
                    return category, 0.95
            return provided_subject, 0.90  # Use as-is if not in categories
        
        # Detect from keywords
        scores = {}
        for subject, keywords in self.subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[subject] = score
        
        if not scores:
            return 'general', 0.5
        
        # Get highest scoring subject
        best_subject = max(scores, key=scores.get)
        confidence = min(scores[best_subject] / 10.0, 0.95)  # Normalize to 0-0.95
        
        return best_subject, confidence
    
    def _detect_complexity(self, text: str) -> str:
        """Detect complexity level: low, medium, high"""
        
        scores = {'high': 0, 'medium': 0, 'low': 0}
        
        for level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    scores[level] += 1
        
        # Consider word count
        word_count = len(text.split())
        if word_count > 500:
            scores['high'] += 2
        elif word_count > 200:
            scores['medium'] += 2
        else:
            scores['low'] += 1
        
        # Check for technical terms
        technical_terms = len(re.findall(r'\b[A-Z][a-z]*[A-Z][a-z]*\b', text))  # CamelCase
        if technical_terms > 5:
            scores['high'] += 1
        
        return max(scores, key=scores.get)
    
    def _detect_question_type(self, text: str) -> str:
        """Detect the type of question being asked"""
        
        scores = {}
        for q_type, indicators in self.question_types.items():
            score = sum(1 for indicator in indicators if indicator in text)
            if score > 0:
                scores[q_type] = score
        
        if not scores:
            return 'explanatory'  # Default
        
        return max(scores, key=scores.get)
    
    def _extract_key_concepts(self, text: str, subject: str) -> List[str]:
        """Extract key concepts from text based on subject"""
        
        concepts = []
        
        # Get subject-specific keywords that appear in text
        if subject in self.subject_keywords:
            keywords = self.subject_keywords[subject]
            for keyword in keywords:
                if keyword in text:
                    concepts.append(keyword)
        
        # Extract capitalized terms (likely important concepts)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        concepts.extend(capitalized[:5])  # Limit to 5
        
        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for concept in concepts:
            if concept.lower() not in seen:
                seen.add(concept.lower())
                unique_concepts.append(concept)
        
        return unique_concepts[:10]  # Return top 10
    
    def _has_equations(self, text: str) -> bool:
        """Detect if text contains mathematical equations"""
        
        # Look for common math symbols and patterns
        math_patterns = [
            r'\d+\s*[+\-*/=]\s*\d+',  # Basic arithmetic
            r'[xy]\s*=\s*\d+',         # Variable assignments
            r'\b(sin|cos|tan|log|ln)\b',  # Functions
            r'\^|\u00b2|\u00b3',       # Exponents
            r'∫|∑|∏|√',                # Math symbols
            r'\([^)]*[+\-*/][^)]*\)',  # Expressions in parentheses
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _has_code(self, text: str) -> bool:
        """Detect if text contains code snippets"""
        
        code_indicators = [
            'def ', 'function ', 'class ', 'import ', 'include ',
            'public ', 'private ', 'void ', 'return ',
            '{', '}', '=>', '==', '!=',
        ]
        
        return any(indicator in text for indicator in code_indicators)


# Global instance
_analyzer = None

def get_context_analyzer() -> AssignmentContextAnalyzer:
    """Get or create global context analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = AssignmentContextAnalyzer()
    return _analyzer
