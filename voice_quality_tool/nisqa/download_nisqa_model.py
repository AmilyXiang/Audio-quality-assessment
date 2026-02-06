#!/usr/bin/env python3
"""下载NISQA预训练模型"""

import os
import sys
import urllib.request
import tarfile
from pathlib import Path

def download_model():
    """下载NISQA模型"""
    
    # 模型URL（从NISQA GitHub获取）
    models = {
        'nisqa': 'https://github.com/gabrielmittag/NISQA/raw/master/weights/nisqa.tar.gz',
        'nisqa_tts': 'https://github.com/gabrielmittag/NISQA/raw/master/weights/nisqa_tts.tar.gz',
    }
    
    current_dir = Path(__file__).parent
    
    for model_name, url in models.items():
        print(f"\n下载 {model_name}...")
        print(f"URL: {url}")
        
        tar_file = current_dir / f"{model_name}.tar.gz"
        model_dir = current_dir / model_name
        
        if model_dir.exists():
            print(f"✓ {model_name} 已存在")
            continue
        
        try:
            # 下载
            print(f"  下载中...")
            urllib.request.urlretrieve(url, tar_file)
            print(f"  ✓ 下载完成: {tar_file}")
            
            # 解压
            print(f"  解压中...")
            with tarfile.open(tar_file, 'r:gz') as tar:
                tar.extractall(current_dir)
            print(f"  ✓ 解压完成: {model_dir}")
            
            # 删除压缩包
            tar_file.unlink()
            print(f"  ✓ 清理完成")
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            
            # 尝试备用地址
            print(f"\n  尝试备用方案...")
            print(f"  请手动下载模型:")
            print(f"  1. 访问: https://github.com/gabrielmittag/NISQA")
            print(f"  2. 下载 weights/{model_name}.tar.gz")
            print(f"  3. 解压到: {current_dir}")
            return False
    
    return True

if __name__ == '__main__':
    success = download_model()
    if not success:
        sys.exit(1)
    print("\n✓ 所有模型已准备就绪！")
