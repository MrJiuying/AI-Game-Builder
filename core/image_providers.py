from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class ProviderOfflineError(Exception):
    """提供者离线异常"""
    pass


class BaseImageProvider(ABC):
    """图片生成提供者基类"""
    
    @abstractmethod
    async def generate_image(self, prompt: str, lora_url_or_name: Optional[str] = None) -> bytes:
        """生成图片
        
        参数:
            prompt: 提示词
            lora_url_or_name: LoRA 模型名称或URL
        
        返回:
            图片字节数据
        """
        pass
    
    async def check_health(self) -> bool:
        """健康检查
        
        返回:
            bool: 是否在线
        """
        return True


class LocalSDProvider(BaseImageProvider):
    """本地 Stable Diffusion 提供者"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7860"):
        if not base_url or not base_url.startswith("http"):
            self.base_url = "http://127.0.0.1:7860"
        else:
            self.base_url = base_url
    
    async def check_health(self) -> bool:
        """检查本地 SD WebUI 是否在线"""
        try:
            async with httpx.AsyncClient(proxy=None, trust_env=False, timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/sdapi/v1/progress")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"SD 健康检查失败详细原因: {type(e).__name__} - {str(e)}")
            raise ProviderOfflineError("本地 SD 节点未启动，请检查 WebUI。")
    
    async def generate_image(self, prompt: str, lora_url_or_name: Optional[str] = None) -> bytes:
        """调用本地 SD WebUI 生图"""
        await self.check_health()
        
        # 处理 LoRA
        if lora_url_or_name:
            prompt += f" <lora:{lora_url_or_name}:1>"
        
        payload = {
            "prompt": prompt,
            "negative_prompt": "bad quality, blurry, low resolution",
            "steps": 30,
            "width": 512,
            "height": 512,
            "seed": -1,
            "sampler_name": "DPM++ 2M Karras"
        }
        
        async with httpx.AsyncClient(proxy=None, trust_env=False, timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/sdapi/v1/txt2img", json=payload)
            response.raise_for_status()
            
            data = response.json()
            base64_image = data["images"][0]
            image_bytes = base64.b64decode(base64_image)
            
            return image_bytes


class Dalle3Provider(BaseImageProvider):
    """DALL-E 3 提供者"""
    
    def __init__(self, api_key: str, model: str = "dall-e-3"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/images/generations"
    
    async def check_health(self) -> bool:
        """检查 DALL-E 3 API 连接状态"""
        try:
            # 使用一个轻量级的 API 调用来验证凭证
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 尝试获取模型列表
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.openai.com/v1/models", headers=headers, timeout=5.0)
                if response.status_code in [401, 403]:
                    raise ProviderOfflineError("API Key 无效或无权限")
                response.raise_for_status()
                return True
        except ProviderOfflineError:
            raise
        except httpx.RequestError as e:
            raise ProviderOfflineError(f"网络错误: {str(e)}")
        except Exception as e:
            raise ProviderOfflineError(f"连接失败: {str(e)}")
    
    async def generate_image(self, prompt: str, lora_url_or_name: Optional[str] = None) -> bytes:
        """调用 DALL-E 3 生图"""
        if lora_url_or_name:
            logger.warning("DALL-E 3 不支持 LoRA，忽略 lora_url_or_name 参数")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "hd"
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            image_url = data["data"][0]["url"]
            
            # 下载图片
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            
            return image_response.content


class CloudSDProvider(BaseImageProvider):
    """云端 Stable Diffusion 提供者 (示例: Fal.ai)"""
    
    def __init__(self, api_key: str, base_url: str = "https://fal.run/fal-ai/stable-diffusion"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def check_health(self) -> bool:
        """检查云端 SD API 连接状态"""
        try:
            # 构建测试请求
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送一个轻量级的测试请求
            test_payload = {
                "prompt": "test",
                "image_size": "256x256",
                "num_images": 1,
                "steps": 1
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=test_payload, headers=headers, timeout=10.0)
                if response.status_code in [401, 403]:
                    raise ProviderOfflineError("API Key 无效或无权限")
                response.raise_for_status()
                return True
        except ProviderOfflineError:
            raise
        except httpx.RequestError as e:
            raise ProviderOfflineError(f"网络错误: {str(e)}")
        except Exception as e:
            raise ProviderOfflineError(f"连接失败: {str(e)}")
    
    async def generate_image(self, prompt: str, lora_url_or_name: Optional[str] = None) -> bytes:
        """调用云端 SD API 生图"""
        payload = {
            "prompt": prompt,
            "negative_prompt": "bad quality, blurry, low resolution",
            "image_size": "1024x1024",
            "num_images": 1,
            "guidance_scale": 7.5,
            "steps": 30
        }
        
        # 处理 LoRA
        if lora_url_or_name:
            payload["lora_weights"] = lora_url_or_name
            payload["lora_scale"] = 1.0
        
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            image_url = data["images"][0]["url"]
            
            # 下载图片
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            
            return image_response.content
