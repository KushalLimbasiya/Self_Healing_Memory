import os
import logging
import json
import time
import hashlib
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    Utility class for processing text with LLM models.
    """
    
    def __init__(self, model="mistral", api_key=None, cache_dir=None, cache_ttl=3600):
        """
        Initialize the LLM Processor.
        
        Args:
            model: Model type to use (default: mistral)
            api_key: API key for the model service
            cache_dir: Directory to store cache files (optional)
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        
        # Create cache directory if specified and doesn't exist
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        logger.info(f"LLM Processor initialized with model: {model}")
        
    def process(self, prompt, temperature=0.7, max_tokens=1024, use_cache=True):
        """
        Process text with the LLM model.
        
        Args:
            prompt: Text prompt to process
            temperature: Generation temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use cache for this request
            
        Returns:
            Model response text
        """
        # Check cache if enabled
        if use_cache and self.cache_dir:
            cached_response = self._get_from_cache(prompt, temperature, max_tokens)
            if cached_response:
                logger.debug("Returning response from cache")
                return cached_response
        
        # Process with the appropriate model
        if self.model.lower() == "mistral":
            response = self._process_with_mistral(prompt, temperature, max_tokens)
        else:
            logger.error(f"Unsupported model: {self.model}")
            response = f"Error: Unsupported model {self.model}"
            
        # Cache the response if caching is enabled
        if use_cache and self.cache_dir and response:
            self._save_to_cache(prompt, temperature, max_tokens, response)
            
        return response
    
    def _process_with_mistral(self, prompt, temperature, max_tokens):
        """
        Process text with Mistral AI API.
        
        Args:
            prompt: Text prompt to process
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Model response text
        """
        if not self.api_key:
            logger.error("Mistral API key not provided")
            return "Error: Mistral API key not provided"
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "mistral-medium",  # Default model
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_json = response.json()
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    return response_json["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Unexpected Mistral API response format: {response_json}")
                    return "Error: Unexpected API response format"
            else:
                logger.error(f"Mistral API error: {response.status_code} - {response.text}")
                return f"Error: API request failed with status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error processing with Mistral: {str(e)}")
            return f"Error: {str(e)}"
    
    def _get_cache_key(self, prompt, temperature, max_tokens):
        """
        Generate a cache key for a request.
        
        Args:
            prompt: Text prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens
            
        Returns:
            Cache key string
        """
        key_data = f"{prompt}_{temperature}_{max_tokens}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, prompt, temperature, max_tokens):
        """
        Get a response from cache if available and not expired.
        
        Args:
            prompt: Text prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens
            
        Returns:
            Cached response or None if not found or expired
        """
        if not self.cache_dir:
            return None
            
        cache_key = self._get_cache_key(prompt, temperature, max_tokens)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            timestamp = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01T00:00:00"))
            if datetime.now() - timestamp > timedelta(seconds=self.cache_ttl):
                logger.debug(f"Cache expired for key: {cache_key}")
                return None
                
            return cache_data.get("response")
            
        except Exception as e:
            logger.warning(f"Error reading from cache: {str(e)}")
            return None
    
    def _save_to_cache(self, prompt, temperature, max_tokens, response):
        """
        Save a response to cache.
        
        Args:
            prompt: Text prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens
            response: Model response to cache
        """
        if not self.cache_dir:
            return
            
        cache_key = self._get_cache_key(prompt, temperature, max_tokens)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response": response
            }
            
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            logger.warning(f"Error saving to cache: {str(e)}")
