from typing import Optional, Dict, Any
import logging

from core.image_providers import BaseImageProvider, LocalSDProvider, Dalle3Provider, CloudSDProvider

logger = logging.getLogger(__name__)


class ImageGeneratorCoordinator:
    """图片生成协调器"""
    
    def __init__(self):
        self._providers: Dict[str, BaseImageProvider] = {}
    
    def get_provider(self, provider_name: str, **kwargs) -> BaseImageProvider:
        """获取图片提供者
        
        参数:
            provider_name: 提供者名称
            **kwargs: 提供者初始化参数
            
        返回:
            BaseImageProvider: 图片提供者实例
        """
        if provider_name not in self._providers:
            self._providers[provider_name] = self._create_provider(provider_name, **kwargs)
        
        return self._providers[provider_name]
    
    def _create_provider(self, provider_name: str, **kwargs) -> BaseImageProvider:
        """创建图片提供者实例
        
        参数:
            provider_name: 提供者名称
            **kwargs: 初始化参数
            
        返回:
            BaseImageProvider: 图片提供者实例
        """
        match provider_name:
            case "local_sd":
                base_url = kwargs.get("base_url", "http://127.0.0.1:7860")
                return LocalSDProvider(base_url=base_url)
            
            case "dalle3":
                api_key = kwargs.get("api_key", "")
                model = kwargs.get("model", "dall-e-3")
                return Dalle3Provider(api_key=api_key, model=model)
            
            case "cloud_sd":
                api_key = kwargs.get("api_key", "")
                base_url = kwargs.get("base_url", "https://fal.run/fal-ai/stable-diffusion")
                return CloudSDProvider(api_key=api_key, base_url=base_url)
            
            case _:
                raise ValueError(f"不支持的图片提供者: {provider_name}")
    
    async def generate_image(
        self,
        provider_name: str,
        prompt: str,
        lora_model: Optional[str] = None,
        **provider_kwargs
    ) -> bytes:
        """生成图片
        
        参数:
            provider_name: 提供者名称
            prompt: 提示词
            lora_model: LoRA 模型
            **provider_kwargs: 提供者参数
            
        返回:
            bytes: 图片字节数据
        """
        provider = self.get_provider(provider_name, **provider_kwargs)
        
        try:
            image_bytes = await provider.generate_image(prompt, lora_model)
            logger.info(f"成功使用 {provider_name} 生成图片")
            return image_bytes
        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            raise
    
    async def check_provider_health(self, provider_name: str, **kwargs) -> bool:
        """检查提供者健康状态
        
        参数:
            provider_name: 提供者名称
            **kwargs: 提供者参数
            
        返回:
            bool: 是否在线
        """
        from core.image_providers import ProviderOfflineError
        
        provider = self.get_provider(provider_name, **kwargs)
        
        try:
            return await provider.check_health()
        except ProviderOfflineError:
            raise
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
