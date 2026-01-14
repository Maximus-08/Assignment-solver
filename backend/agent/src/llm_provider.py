"""
LLM Provider Manager - Multi-provider abstraction layer with automatic failover.

Manages multiple LLM providers (Gemini, Groq, Together, HuggingFace) and automatically
fails over to backup providers when primary is unavailable or rate-limited.
"""

import asyncio
import logging
from typing import List, Optional, Dict
from enum import Enum

from .gemini_client import GeminiClient
from .groq_client import GroqClient
from .models import ProcessedAssignment, GeneratedSolution
from .config import settings

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class NoAvailableProvidersError(Exception):
    """Raised when all LLM providers are exhausted or unavailable"""
    pass


class RateLimitError(Exception):
    """Raised when a provider hits rate limits"""
    pass


class LLMProviderManager:
    """
    Manages multiple LLM providers with automatic failover.
    
    Priority order:
    1. Gemini (Primary - high quality, generous free tier)
    2. Groq (Fallback 1 - extremely fast, free Llama 3)
    3. Together.ai (Fallback 2 - free tier)
    4. HuggingFace (Fallback 3 - free inference API)
    """
    
    def __init__(self):
        self.providers: Dict[str, any] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}
        
        # Priority order based on quality and availability
        self.priority_order = self._get_priority_order()
        
        logger.info(f"LLM Provider Manager initialized with priority: {self.priority_order}")
    
    def _get_priority_order(self) -> List[str]:
        """Get provider priority from settings or use default"""
        default_priority = ['gemini', 'groq']  # Start with these two
        
        # Allow override from settings
        priority_setting = getattr(settings, 'LLM_PROVIDER_PRIORITY', None)
        if priority_setting:
            return [p.strip() for p in priority_setting.split(',')]
        
        return default_priority
    
    async def initialize(self) -> bool:
        """Initialize all available LLM providers"""
        logger.info("Initializing LLM providers...")
        
        initialized_count = 0
        
        # Initialize Gemini (primary)
        try:
            gemini = GeminiClient()
            if await gemini.initialize():
                self.providers['gemini'] = gemini
                self.provider_status['gemini'] = ProviderStatus.AVAILABLE
                initialized_count += 1
                logger.info("✓ Gemini initialized successfully")
            else:
                self.provider_status['gemini'] = ProviderStatus.UNAVAILABLE
                logger.warning("✗ Gemini initialization failed")
        except Exception as e:
            logger.error(f"Error initializing Gemini: {e}")
            self.provider_status['gemini'] = ProviderStatus.ERROR
        
        # Initialize Groq (fast fallback)
        try:
            groq = GroqClient()
            if await groq.initialize():
                self.providers['groq'] = groq
                self.provider_status['groq'] = ProviderStatus.AVAILABLE
                initialized_count += 1
                logger.info("✓ Groq initialized successfully")
            else:
                self.provider_status['groq'] = ProviderStatus.UNAVAILABLE
                logger.warning("✗ Groq initialization failed (API key missing?)")
        except Exception as e:
            logger.error(f"Error initializing Groq: {e}")
            self.provider_status['groq'] = ProviderStatus.ERROR
        
        # TODO: Add Together.ai and HuggingFace when needed
        
        if initialized_count == 0:
            logger.error("CRITICAL: No LLM providers initialized successfully!")
            return False
        
        logger.info(f"LLM Provider Manager ready with {initialized_count} provider(s)")
        return True
    
    async def generate_solution(
        self, 
        assignment: ProcessedAssignment,
        force_provider: Optional[str] = None
    ) -> GeneratedSolution:
        """
        Generate solution using available providers with automatic failover.
        
        Args:
            assignment: The processed assignment to solve
            force_provider: Optional provider name to force use (for testing)
        
        Returns:
            GeneratedSolution object
        
        Raises:
            NoAvailableProvidersError: If all providers fail
        """
        
        # If specific provider requested
        if force_provider:
            if force_provider not in self.providers:
                raise ValueError(f"Provider '{force_provider}' not available")
            
            provider = self.providers[force_provider]
            logger.info(f"Using forced provider: {force_provider}")
            return await provider.generate_solution(assignment)
        
        # Try providers in priority order
        errors = []
        
        for provider_name in self.priority_order:
            # Check if provider is initialized
            if provider_name not in self.providers:
                logger.debug(f"Provider '{provider_name}' not initialized, skipping")
                continue
            
            # Check provider status
            status = self.provider_status.get(provider_name, ProviderStatus.UNAVAILABLE)
            if status == ProviderStatus.UNAVAILABLE:
                logger.debug(f"Provider '{provider_name}' unavailable, skipping")
                continue
            
            provider = self.providers[provider_name]
            
            # Check if provider is available
            if not provider.is_available():
                logger.warning(f"Provider '{provider_name}' reports not available")
                self.provider_status[provider_name] = ProviderStatus.UNAVAILABLE
                continue
            
            # Try to generate solution
            try:
                logger.info(f"Attempting solution generation with provider: {provider_name}")
                solution = await provider.generate_solution(assignment)
                
                # Success! Reset status to available
                self.provider_status[provider_name] = ProviderStatus.AVAILABLE
                
                logger.info(f"✓ Solution generated successfully using {provider_name}")
                return solution
                
            except RateLimitError as e:
                logger.warning(f"Provider '{provider_name}' rate limited: {e}")
                self.provider_status[provider_name] = ProviderStatus.RATE_LIMITED
                errors.append(f"{provider_name}: Rate limited")
                continue
                
            except Exception as e:
                logger.error(f"Provider '{provider_name}' failed: {e}")
                self.provider_status[provider_name] = ProviderStatus.ERROR
                errors.append(f"{provider_name}: {str(e)}")
                continue
        
        # All providers failed
        error_summary = "; ".join(errors)
        logger.error(f"All LLM providers exhausted. Errors: {error_summary}")
        
        raise NoAvailableProvidersError(
            f"Unable to generate solution - all LLM providers failed or are rate-limited. "
            f"Errors: {error_summary}"
        )
    
    def get_provider_status(self) -> Dict[str, str]:
        """Get current status of all providers"""
        return {
            name: status.value 
            for name, status in self.provider_status.items()
        }
    
    def reset_provider_status(self, provider_name: str):
        """Reset a provider's status to available (e.g., after cooldown period)"""
        if provider_name in self.provider_status:
            self.provider_status[provider_name] = ProviderStatus.AVAILABLE
            logger.info(f"Reset status for provider '{provider_name}' to AVAILABLE")
