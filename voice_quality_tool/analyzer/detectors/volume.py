"""Volume fluctuation detection: abnormal loudness changes (AGC issues)."""
from typing import Optional
from .base import BaseDetector, DetectionEvent


class VolumeDetector(BaseDetector):
    """Detects abnormal volume fluctuations (AGC pumping, not speaker switching)."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.rms_change_threshold = self.config.get("rms_change_threshold", 0.5)
        self.min_history_frames = 3
        self.agc_pump_count = 0  # 计数"泵动"次数（用于检测AGC失效模式）
        self.prev_rms = None
    
    def detect(self, features, frame, prev_features=None, is_voice_active=True) -> Optional[DetectionEvent]:
        """Detect volume fluctuation issues (AGC pumping).
        
        区分两种情况：
        1. AGC失效 - "泵动"效应：短时间内反复忽大忽小 ✅ 检测
        2. 说话者切换 - 单向变化：音量平稳上升或下降 ❌ 不检测
        """
        self.add_to_history(features, frame)
        
        # 只在语音活跃时检测
        if not is_voice_active:
            self.prev_rms = None
            return None
        
        if len(self.history) < self.min_history_frames:
            return None
        
        rms = features.get("rms", 0)
        
        # 获取最近3帧的RMS
        recent_rms = [h["features"]["rms"] for h in self.history[-3:]]
        
        if not recent_rms or max(recent_rms) == 0:
            return None
        
        rms_ratio = max(recent_rms) / (min(recent_rms) + 1e-6)
        
        # 检查是否超过阈值
        if rms_ratio > (1.0 + self.rms_change_threshold):
            # 进一步判断：是AGC失效还是说话者切换？
            # AGC失效特征：方向反复变化（大→小→大）
            # 说话者切换特征：单向变化（小→大 或 大→小）
            
            if self.prev_rms is not None and len(recent_rms) >= 2:
                # 检查最近两帧的变化方向
                last_frame_rms = recent_rms[-2]  # 倒数第二帧
                curr_frame_rms = recent_rms[-1]  # 最后一帧（当前）
                
                # 变化方向：> 0 表示上升，< 0 表示下降
                direction_change = (curr_frame_rms - last_frame_rms) * (last_frame_rms - self.prev_rms)
                
                # 如果 direction_change < 0，说明方向改变（泵动迹象）
                if direction_change < 0:
                    # 确实是AGC泵动（方向反复变化）
                    confidence = min((rms_ratio - 1.0) / self.rms_change_threshold * 0.8, 1.0)
                    
                    result = DetectionEvent(
                        event_type="volume_fluctuation",
                        start_time=frame.start_time,
                        end_time=frame.end_time,
                        confidence=confidence,
                        details={
                            "reason": "agc_pumping",
                            "rms_ratio": rms_ratio,
                            "current_rms": rms,
                            "pattern": "direction_reversal"
                        }
                    )
                    self.prev_rms = rms
                    return result
                else:
                    # 单向变化（上升或下降）→ 可能是说话者切换，不报告
                    self.prev_rms = rms
                    return None
            
            # 无法判断方向时，保守不报告（避免误报）
            self.prev_rms = rms
            return None
        
        self.prev_rms = rms
        return None
