import os
import json
from typing import Optional

from openai import OpenAI

# 可通过环境变量或直接传参设置API Key
def _resolve_credentials(api_key: Optional[str] = None, base_url: Optional[str] = None) -> tuple[str, Optional[str], str]:
    """Resolve API key + base_url for OpenAI-compatible providers.

    Priority:
    - If api_key passed: use it.
    - Else prefer DEEPSEEK_API_KEY if set, otherwise OPENAI_API_KEY.
    - base_url: if passed, use it; else if DEEPSEEK_API_KEY is used, default to https://api.deepseek.com/v1.
    """
    env_deepseek = os.getenv("DEEPSEEK_API_KEY")
    env_openai = os.getenv("OPENAI_API_KEY")

    resolved_key = api_key or env_deepseek or env_openai
    if not resolved_key:
        raise RuntimeError("请设置DEEPSEEK_API_KEY或OPENAI_API_KEY环境变量，或传入api_key")

    using_deepseek = bool(api_key is None and env_deepseek) or (env_deepseek and resolved_key == env_deepseek)

    resolved_base = base_url
    if not resolved_base:
        if using_deepseek:
            resolved_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        else:
            resolved_base = os.getenv("OPENAI_API_BASE")

    provider = "deepseek" if using_deepseek or (resolved_base and "deepseek" in resolved_base) else "openai"
    return resolved_key, resolved_base, provider

def build_llm_prompt(analysis_result):
    """
    生成给LLM的prompt，输入为分析JSON结果（dict）。
    """
    meta = analysis_result.get('meta', {})
    global_block = analysis_result.get('global', {})
    audio_summary = analysis_result.get('llm_audio_summary') or analysis_result.get('audio_summary') or {}
    events_block = {
        k: v for k, v in analysis_result.items()
        if k in ("noise", "dropout", "volume_fluctuation", "voice_distortion")
    }
    prompt = f"""
你是音频质量分析专家。以下是自动检测系统的分析结果摘要和特征统计，请基于这些信息判断音频整体质量，并给出简明、专业的诊断建议：

【元信息】
{json.dumps(meta, ensure_ascii=False, indent=2)}

【全局特征】
{json.dumps(global_block, ensure_ascii=False, indent=2)}

【检测结果】
{json.dumps(events_block, ensure_ascii=False, indent=2)}

【音频摘要（路线1：从音频计算的紧凑统计）】
{json.dumps(audio_summary, ensure_ascii=False, indent=2)}

请用中文输出：
1. 总体质量结论（优/良/中/差，简要理由）
2. 主要问题归因（如有）
3. 改进建议（如有）
"""
    return prompt

def query_llm(analysis_result, api_key=None, model="deepseek-chat", base_url=None, timeout=30):
    resolved_key, resolved_base, _provider = _resolve_credentials(api_key=api_key, base_url=base_url)
    client = OpenAI(api_key=resolved_key, base_url=resolved_base)
    prompt = build_llm_prompt(analysis_result)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512,
        timeout=timeout,
    )
    return (response.choices[0].message.content or "").strip()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM智能音质诊断 (支持OpenAI/DeepSeek)")
    parser.add_argument('result_json', help='分析结果JSON文件')
    parser.add_argument('--api_key', help='API Key，可选，支持OpenAI或DeepSeek')
    parser.add_argument('--model', default='deepseek-chat', help='模型名，可选（DeepSeek示例: deepseek-chat；OpenAI示例: gpt-4o）')
    parser.add_argument('--base_url', default=None, help='API Base URL，可选，DeepSeek如https://api.deepseek.com/v1')
    args = parser.parse_args()
    with open(args.result_json, 'r', encoding='utf-8') as f:
        analysis_result = json.load(f)
    advice = query_llm(
        analysis_result,
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        timeout=30,
    )
    print("\n【LLM智能诊断建议】\n" + advice)
