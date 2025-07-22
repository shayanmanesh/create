import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import time
import json
from datetime import datetime
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AIModelPool:
    """Connection pool for AI models with retry logic and failover"""
    
    def __init__(self, model_name: str, api_urls: List[str], api_key: str, 
                 pool_size: int = 10, timeout: int = 60):
        self.model_name = model_name
        self.api_urls = api_urls if isinstance(api_urls, list) else [api_urls]
        self.api_key = api_key
        self.pool_size = pool_size
        self.timeout = timeout
        self.sessions: List[aiohttp.ClientSession] = []
        self.current_url_index = 0
        self.latency_tracker = {}
        
    async def __aenter__(self):
        for _ in range(self.pool_size):
            connector = aiohttp.TCPConnector(limit_per_host=100)
            session = aiohttp.ClientSession(
                connector=connector,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            self.sessions.append(session)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.gather(*[session.close() for session in self.sessions])
    
    def get_fastest_endpoint(self) -> str:
        """Select endpoint with lowest latency"""
        if not self.latency_tracker:
            return self.api_urls[0]
        
        sorted_endpoints = sorted(
            self.latency_tracker.items(), 
            key=lambda x: x[1]
        )
        return sorted_endpoints[0][0] if sorted_endpoints else self.api_urls[0]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make request with retry logic and latency tracking"""
        url = self.get_fastest_endpoint()
        full_url = f"{url}/{endpoint}"
        
        start_time = time.time()
        session = self.sessions[hash(asyncio.current_task()) % len(self.sessions)]
        
        try:
            async with session.post(
                full_url, 
                json=data, 
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Track latency
                latency = time.time() - start_time
                self.latency_tracker[url] = (
                    (self.latency_tracker.get(url, 0) + latency) / 2
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Error calling {self.model_name} at {full_url}: {str(e)}")
            
            # Try next endpoint
            if len(self.api_urls) > 1:
                self.current_url_index = (self.current_url_index + 1) % len(self.api_urls)
                raise
            raise


class AIOrchestrator:
    """Main orchestrator for AI model pipeline"""
    
    def __init__(self):
        self.redis_client = None
        self.model_pools = {}
        self.initialized = False
        
    async def initialize(self):
        """Initialize model pools and Redis connection"""
        if self.initialized:
            return
            
        # Initialize Redis
        self.redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Initialize model pools
        self.model_pools = {
            "whisper": AIModelPool(
                "whisper",
                [settings.whisper_api_url],
                settings.whisper_api_key,
                timeout=settings.ai_model_timeout
            ),
            "qwq": AIModelPool(
                "qwq",
                [settings.qwq_api_url],
                settings.qwq_api_key,
                timeout=settings.ai_model_timeout
            ),
            "llama_scout": AIModelPool(
                "llama_scout",
                [settings.llama_scout_api_url],
                settings.llama_scout_api_key,
                timeout=settings.ai_model_timeout
            ),
            "flux": AIModelPool(
                "flux",
                [settings.flux_api_url],
                settings.flux_api_key,
                timeout=settings.ai_model_timeout
            ),
            "melotts": AIModelPool(
                "melotts",
                [settings.melotts_api_url],
                settings.melotts_api_key,
                timeout=settings.ai_model_timeout
            ),
            "llama_vision": AIModelPool(
                "llama_vision",
                [settings.llama_vision_api_url],
                settings.llama_vision_api_key,
                timeout=settings.ai_model_timeout
            )
        }
        
        # Enter all model pools
        for pool in self.model_pools.values():
            await pool.__aenter__()
            
        self.initialized = True
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
            
        for pool in self.model_pools.values():
            await pool.__aexit__(None, None, None)
            
    async def process_creation(
        self, 
        user_id: str,
        input_type: str,
        input_data: Union[str, bytes],
        creation_type: str = "general",
        language: str = "en"
    ) -> Dict[str, Any]:
        """Main pipeline for content creation"""
        
        start_time = time.time()
        creation_id = f"{user_id}_{int(time.time() * 1000)}"
        
        # Check cache first
        cache_key = f"creation:{creation_type}:{hash(input_data)}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        try:
            # Step 1: Process input based on type
            if input_type == "audio":
                transcription = await self._transcribe_audio(input_data)
                processed_input = transcription["text"]
            elif input_type == "image":
                image_analysis = await self._analyze_image(input_data)
                processed_input = image_analysis["description"]
            else:
                processed_input = input_data
            
            # Step 2: Content planning with QwQ
            content_plan = await self._plan_content(processed_input, creation_type)
            
            # Step 3: Parallel content generation
            generation_tasks = [
                self._generate_text_content(content_plan, creation_type),
                self._generate_images(content_plan),
                self._generate_voiceover(content_plan["script"], language)
            ]
            
            text_content, images, voiceover = await asyncio.gather(*generation_tasks)
            
            # Step 4: Quality check and optimization
            final_content = await self._quality_check({
                "text": text_content,
                "images": images,
                "voiceover": voiceover,
                "plan": content_plan
            })
            
            # Prepare result
            result = {
                "creation_id": creation_id,
                "user_id": user_id,
                "content": final_content,
                "metadata": {
                    "creation_type": creation_type,
                    "processing_time": time.time() - start_time,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            # Cache result (expire in 1 hour)
            await self.redis_client.setex(
                cache_key, 
                3600, 
                json.dumps(result)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in creation pipeline: {str(e)}")
            raise
    
    async def _transcribe_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        return await self.model_pools["whisper"].request(
            "transcribe",
            {"audio": audio_data.hex()}
        )
    
    async def _analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image using Llama Vision"""
        return await self.model_pools["llama_vision"].request(
            "analyze",
            {"image": image_data.hex()}
        )
    
    async def _plan_content(self, input_text: str, creation_type: str) -> Dict[str, Any]:
        """Plan content structure using QwQ"""
        prompt = f"""
        Create a detailed content plan for a {creation_type} based on this input: {input_text}
        
        Return a JSON with:
        - title: Catchy title
        - description: Brief description
        - script: Voiceover script (30 seconds max)
        - image_prompts: List of 3-5 image generation prompts
        - hashtags: List of viral hashtags
        - share_caption: Social media caption
        """
        
        return await self.model_pools["qwq"].request(
            "generate",
            {"prompt": prompt, "format": "json"}
        )
    
    async def _generate_text_content(
        self, 
        content_plan: Dict[str, Any], 
        creation_type: str
    ) -> Dict[str, Any]:
        """Generate text content using Llama Scout"""
        return await self.model_pools["llama_scout"].request(
            "generate",
            {
                "plan": content_plan,
                "type": creation_type,
                "max_length": 500
            }
        )
    
    async def _generate_images(self, content_plan: Dict[str, Any]) -> List[str]:
        """Generate images using FLUX"""
        image_prompts = content_plan.get("image_prompts", [])[:5]
        
        tasks = [
            self.model_pools["flux"].request(
                "generate",
                {"prompt": prompt, "size": "1024x1024"}
            )
            for prompt in image_prompts
        ]
        
        results = await asyncio.gather(*tasks)
        return [r["image_url"] for r in results]
    
    async def _generate_voiceover(self, script: str, language: str) -> Dict[str, Any]:
        """Generate voiceover using MeloTTS"""
        return await self.model_pools["melotts"].request(
            "synthesize",
            {
                "text": script,
                "language": language,
                "voice": "natural",
                "speed": 1.0
            }
        )
    
    async def _quality_check(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Quality check and optimization using Llama Vision"""
        result = await self.model_pools["llama_vision"].request(
            "quality_check",
            {"content": content}
        )
        
        # Apply optimizations if suggested
        if result.get("optimizations"):
            content.update(result["optimizations"])
            
        return content


# Singleton instance
ai_orchestrator = AIOrchestrator()